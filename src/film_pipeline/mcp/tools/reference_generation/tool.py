"""The generate_reference_images MCP tool."""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, cast

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.mcp.tools.reference_generation.composites import (
    _build_composites,
)
from film_pipeline.mcp.tools.reference_generation.entries import (
    _group_and_sort_entries,
    _group_key,
    _reference_aspect_ratio,
    _reference_job_id,
    _reference_output_dir,
    _reference_prompt,
)
from film_pipeline.mcp.tools.reference_generation.index_files import (
    _save_reference_index_artifact,
    _select_image_provider,
    _write_reference_index_files,
)

from ..helpers import _error, _load_latest_reference_index, _ok, _services

_logger = logging.getLogger(__name__)


class _AttemptVerdict(Enum):
    """Loop-control outcome of a single generation attempt."""

    RETRY = "retry"
    FAILED = "failed"
    STOP = "stop"


@dataclass(frozen=True)
class _GenerationBatch:
    """Shared services and accumulators for one generation batch."""

    rt: Any
    provider: Any
    project_root: Path
    identity_states: dict[str, dict[str, object]]
    char_bibles: dict[str, dict[str, object]]
    results: list[dict[str, object]]


@dataclass(frozen=True)
class _EntryContext:
    """Per-entry generation inputs shared by the retry and metadata steps."""

    reference_id: str
    shot_id: str
    output_dir: str
    prompt_text: str
    aspect_ratio: str
    tier: str
    provider_kwargs: dict[str, object]


@dataclass
class _LoopState:
    """Mutable state threaded through the bounded retry attempts."""

    best_score: float = 0.0
    best_attempt: int = 0
    frame_review_result: Any | None = None
    retry_prompt: str = ""
    target_path: Path | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class _RetryOutcome:
    """Result of the bounded per-entry generation retry loop."""

    best_score: float
    best_attempt: int
    frame_review_result: Any | None
    target_path: Path | None
    metadata: dict[str, object]
    failed: bool


def _requested_reference_ids(args: dict[str, object]) -> set[str]:
    """Normalized set of explicitly requested reference ids."""
    return {
        str(item)
        for item in cast(list[Any], args.get("reference_ids", []))
        if isinstance(item, str) and str(item).strip()
    }


def _copied_entries(grouped_entries: list[dict[str, object]]) -> list[dict[str, object]]:
    """Shallow-copy every entry so persisted state keeps the pre-run values."""
    return [dict(r) for r in grouped_entries]  # use modified copies


def _maybe_cache_character_bible(
    store: Any,
    project_id: str,
    raw: dict[str, object],
    char_bibles: dict[str, dict[str, object]],
) -> None:
    """Cache the CharacterBible for a character entry when one exists."""
    subject_type = str(raw.get("subject_type", ""))
    subject_id = str(raw.get("subject_id", "")).strip()
    if subject_type != "character" or not subject_id or subject_id in char_bibles:
        return
    try:
        from film_pipeline.schemas._base import FilmPhase

        bible = store.load(project_id, FilmPhase("visual_dev"), "character_bible", 1)
        if isinstance(bible, dict) and bible.get("character_id") == subject_id:
            char_bibles[subject_id] = bible
    except (FileNotFoundError, ValueError):
        pass  # CharacterBible not yet generated — fall back to prompt_text


def _load_character_bibles(
    store: Any,
    project_id: str,
    grouped_entries: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Pre-load CharacterBibles from the artifact store for structured prompts."""
    char_bibles: dict[str, dict[str, object]] = {}
    for raw in grouped_entries:
        if raw.get("_skip"):
            continue
        _maybe_cache_character_bible(store, project_id, raw, char_bibles)
    return char_bibles


# Identity consistency is enforced via the ID_REINFORCE prompt block
# (the Imagen API does not support reference-image conditioning).
# anchor_frame_path and i2i_active in identity_states are consumed by
# _reference_prompt() → build_structured_prompt() to strengthen the
# ID_REINFORCE instruction when Gemini detects subject drift.


def _seed_from_identity_state(
    identity_states: dict[str, dict[str, object]],
    group_key: str,
    shot_id: str,
    provider_kwargs: dict[str, object],
) -> None:
    """Reuse the group's anchor seed, or mint one on the anchor entry."""
    identity_state = identity_states.get(group_key, {})
    anchor_seed = identity_state.get("anchor_seed")
    if anchor_seed is not None:
        provider_kwargs["seed"] = anchor_seed
    else:
        provider_kwargs["seed"] = hash(shot_id) % (2**31)
        identity_states.setdefault(group_key, {})["anchor_seed"] = provider_kwargs["seed"]


def _prepare_entry_context(
    raw: dict[str, object],
    reference_id: str,
    char_bibles: dict[str, dict[str, object]],
    identity_states: dict[str, dict[str, object]],
    project_root: Path,
) -> _EntryContext:
    """Build prompt, output, and provider-routing context for one entry."""
    prompt_text = _reference_prompt(
        raw,
        character_bible=char_bibles.get(str(raw.get("subject_id", "")).strip()),
        identity_state=identity_states.get(_group_key(raw)),
    )
    aspect_ratio = _reference_aspect_ratio(raw)
    shot_id = _reference_job_id(reference_id)
    output_dir = str(_reference_output_dir(raw, project_root).resolve())
    # Ensure the directory tree exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Provider tier routing (Phase 6) + Identity consistency (Phase 4)
    tier = str(raw.get("tier", "fast"))
    provider_kwargs: dict[str, object] = {"duration": 0.0, "aspect_ratio": aspect_ratio}
    if tier in ("standard", "ultra"):
        _seed_from_identity_state(identity_states, _group_key(raw), shot_id, provider_kwargs)

    return _EntryContext(
        reference_id=reference_id,
        shot_id=shot_id,
        output_dir=output_dir,
        prompt_text=prompt_text,
        aspect_ratio=aspect_ratio,
        tier=tier,
        provider_kwargs=provider_kwargs,
    )


def _record_failed_entry(
    raw: dict[str, object],
    reference_id: str,
    results: list[dict[str, object]],
    *,
    code: str,
    issue_message: str,
    result_error: str,
) -> None:
    """Record a terminal generation failure on the entry and in results."""
    raw["generation_status"] = "failed"
    raw["issues"] = [{"code": code, "message": issue_message, "severity": "blocking"}]
    raw["validation"] = {"status": "needs_regeneration", "score": 0.0, "reports": []}
    results.append({"reference_id": reference_id, "status": "failed", "error": result_error})


def _feedback_retry_prompt(prompt_text: str, frame_review_result: Any | None) -> str | None:
    """Compose the retry prompt with actionable feedback, when present."""
    feedback = frame_review_result.actionable_feedback if frame_review_result else ""
    if feedback:
        return f"{prompt_text} Fix the following: {feedback}"
    return None


def _execute_provider_attempt(
    provider: Any,
    retry_prompt: str,
    ctx: _EntryContext,
) -> tuple[Path, dict[str, object], Exception | None]:
    """Submit one provider job and rename its download into place.

    Returns the renamed target path plus metadata on success, or the raised
    exception. Rename errors intentionally propagate to the caller's caller.
    """
    try:
        payload = provider.build_payload(retry_prompt, **ctx.provider_kwargs)
        job = provider.submit(payload, ctx.shot_id)
        job = provider.poll(job)
        downloaded_path = provider.download(job, ctx.output_dir)
        metadata = provider.extract_metadata(downloaded_path)
    except Exception as exc:  # retried/recorded by the loop
        return Path(), {}, exc

    ext = Path(downloaded_path).suffix or ".png"
    target_name = f"{_reference_job_id(ctx.reference_id)}{ext}"
    target_path = Path(ctx.output_dir) / target_name
    Path(downloaded_path).rename(target_path)
    return target_path, metadata, None


def _grade_generated_frame(
    batch: _GenerationBatch,
    raw: dict[str, object],
    ctx: _EntryContext,
    state: _LoopState,
    attempt: int,
) -> _AttemptVerdict:
    """Run heuristics and Gemini review for a freshly generated frame."""
    from film_pipeline.generation.frame_heuristics import run_heuristic_checks

    heuristic_result = run_heuristic_checks(
        cast(Path, state.target_path), subject_type=str(raw.get("subject_type", "character"))
    )
    if not heuristic_result.passed:
        if attempt < 2:
            return _AttemptVerdict.RETRY
        _record_failed_entry(
            raw,
            ctx.reference_id,
            batch.results,
            code="heuristic_check_failed",
            issue_message=f"Heuristics failed: {', '.join(heuristic_result.failures)}",
            result_error=f"Heuristics: {', '.join(heuristic_result.failures)}",
        )
        return _AttemptVerdict.FAILED
    from film_pipeline.generation.frame_reviewer import review_frame, should_review_frame

    state.frame_review_result = None
    if should_review_frame(raw):
        with contextlib.suppress(Exception):
            state.frame_review_result = review_frame(
                cast(Path, state.target_path),
                state.retry_prompt,
                model=_services(batch.rt).prompt_runner.model_router.resolve_or_raise(
                    "visual_reasoner"
                ),
                subject_type=str(raw.get("subject_type", "character")),
                frame_id=ctx.reference_id,
            )

    review_result = state.frame_review_result
    if review_result is not None and review_result.passed:
        state.best_score = review_result.total
        state.best_attempt = attempt + 1
        return _AttemptVerdict.STOP
    if review_result is not None:
        if review_result.total > state.best_score:
            state.best_score = review_result.total
            state.best_attempt = attempt + 1
        if attempt < 2:
            return _AttemptVerdict.RETRY
    # Review skipped or unavailable — accept on first attempt
    if review_result is None:
        state.best_attempt = attempt + 1
    return _AttemptVerdict.STOP


def _attempt_reference_once(
    batch: _GenerationBatch,
    raw: dict[str, object],
    ctx: _EntryContext,
    state: _LoopState,
    attempt: int,
) -> _AttemptVerdict:
    """Execute one generation attempt; classify the loop-control outcome."""
    if attempt > 0:
        # Inject actionable feedback into prompt for retry
        updated = _feedback_retry_prompt(ctx.prompt_text, state.frame_review_result)
        if updated is not None:
            state.retry_prompt = updated

    target_path, metadata, exc = _execute_provider_attempt(batch.provider, state.retry_prompt, ctx)
    if exc is None:
        state.target_path = target_path
        state.metadata = metadata
        return _grade_generated_frame(batch, raw, ctx, state, attempt)

    if attempt < 2:
        return _AttemptVerdict.RETRY
    _record_failed_entry(
        raw,
        ctx.reference_id,
        batch.results,
        code="generation_failed",
        issue_message=str(exc)[:300],
        result_error=str(exc)[:200],
    )
    return _AttemptVerdict.FAILED


def _run_retry_attempts(
    batch: _GenerationBatch,
    raw: dict[str, object],
    ctx: _EntryContext,
) -> _RetryOutcome:
    """Run up to three generation attempts, keeping the best reviewed frame."""
    state = _LoopState(retry_prompt=ctx.prompt_text)
    verdict = _AttemptVerdict.RETRY
    for attempt in range(3):
        verdict = _attempt_reference_once(batch, raw, ctx, state, attempt)
        if verdict is _AttemptVerdict.RETRY:
            continue
        break
    return _RetryOutcome(
        best_score=state.best_score,
        best_attempt=state.best_attempt,
        frame_review_result=state.frame_review_result,
        target_path=state.target_path,
        metadata=state.metadata,
        failed=verdict is _AttemptVerdict.FAILED,
    )


def _apply_identity_drift_policy(
    identity_states: dict[str, dict[str, object]],
    raw: dict[str, object],
    frame_review_result: Any | None,
    is_anchor: bool,
) -> None:
    """Escalate to image-to-image strength when Gemini reports subject drift."""
    if frame_review_result is None or frame_review_result.passed:
        return
    subject_score = float(
        cast(float, frame_review_result.scores.get("subject", {}).get("score", 10))
    )
    if subject_score < 7 and not is_anchor:
        ist = identity_states.setdefault(_group_key(raw), {})
        if not ist.get("i2i_active"):
            ist["i2i_active"] = True
            ist["i2i_strength"] = 0.5
        elif float(cast(float, ist.get("i2i_strength", 0.5))) > 0.3:
            ist["i2i_strength"] = 0.3


def _apply_validated_metadata(raw: dict[str, object], frame_review_result: Any) -> None:
    """Stamp approved-review quality fields onto a generated entry."""
    raw["generation_status"] = "validated"
    raw["quality_score"] = frame_review_result.total / 40.0 * 100.0
    raw["locked"] = True
    raw["validation"] = {
        "status": "approved",
        "score": frame_review_result.total,
        "reports": [json.dumps(frame_review_result.scores, default=str)],
    }
    raw["ai_usability"] = {
        "score": frame_review_result.total / 40.0 * 100.0,
        "risks": [],
        "notes": "Gemini per-frame review passed.",
    }
    raw["issues"] = []


def _apply_regeneration_metadata(raw: dict[str, object], frame_review_result: Any) -> None:
    """Stamp needs-regeneration quality fields onto a generated entry."""
    raw["generation_status"] = "needs_regeneration"
    raw["quality_score"] = frame_review_result.total / 40.0 * 100.0
    raw["locked"] = False
    raw["validation"] = {
        "status": "needs_regeneration",
        "score": frame_review_result.total,
        "reports": [json.dumps(frame_review_result.scores, default=str)],
    }
    raw["ai_usability"] = {
        "score": frame_review_result.total / 40.0 * 100.0,
        "risks": [],
        "notes": frame_review_result.actionable_feedback or "Gemini review failed.",
    }
    raw["issues"] = [
        {
            "code": "gemini_review_failed",
            "message": frame_review_result.actionable_feedback or "Gemini review below threshold.",
            "severity": "warning",
        }
    ]


def _apply_unreviewed_metadata(raw: dict[str, object]) -> None:
    """Stamp default quality fields when Gemini review did not run."""
    raw["generation_status"] = "generated"
    raw["quality_score"] = 80.0
    raw["locked"] = False
    raw["validation"] = {
        "status": "pending",
        "score": 0.0,
        "reports": [],
    }
    raw["ai_usability"] = {
        "score": 0.0,
        "risks": [],
        "notes": "Gemini review skipped (selective validation or API unavailable).",
    }
    raw["issues"] = []


def _write_frame_sidecar_safely(
    target_path: Path, raw: dict[str, object], asset_posix: str, ctx: _EntryContext
) -> None:
    """Write the frame metadata sidecar alongside the PNG; non-blocking."""
    try:
        from film_pipeline.generation.frame_sidecar import write_frame_sidecar
        from film_pipeline.schemas.reference import ReferenceFrame

        frame = ReferenceFrame(
            frame_path=asset_posix,
            reference_id=ctx.reference_id,
            subject_type=str(raw.get("subject_type", "")),
            subject_id=str(raw.get("subject_id", "")),
            provider_id=str(raw.get("provider", "")),
            model_id="",
            tier=ctx.tier,
            seed=cast(int | None, ctx.provider_kwargs.get("seed")),
            prompt_text=ctx.prompt_text,
            frame_role=str(raw.get("frame_role", "")),
            expression=str(raw.get("expression", "")) or None,
            lighting=str(raw.get("lighting", "")) or None,
            aspect_ratio=ctx.aspect_ratio,
            generation_status=str(raw.get("generation_status", "generated")),
            quality_score=float(cast(float, raw.get("quality_score", 0))),
            retry_count=int(cast(int, raw.get("retry_count", 0))),
            best_score=float(cast(float, raw.get("best_score", 0))),
            heuristic_checks_passed=True,
            mime_type=str(raw.get("normalized_mime_type", "image/png")),
            created_at="",
        )
        write_frame_sidecar(target_path, frame)
    except Exception:
        pass  # sidecar failure is non-blocking


def _stamp_asset_fields(
    batch: _GenerationBatch,
    raw: dict[str, object],
    ctx: _EntryContext,
    outcome: _RetryOutcome,
) -> None:
    """Stamp asset location, provider, and prompt provenance onto the entry."""
    rel_path = cast(Path, outcome.target_path).resolve().relative_to(batch.project_root.resolve())
    provider_entry = getattr(batch.provider, "entry", None)
    provider_id = str(getattr(provider_entry, "provider_id", ""))
    raw["asset_path"] = rel_path.as_posix()
    raw["provider"] = provider_id
    raw["tier"] = ctx.tier
    raw["prompt_text"] = ctx.prompt_text
    raw["source_frames"] = [rel_path.as_posix()]
    raw["original_mime_type"] = str(outcome.metadata.get("mime_type", "image/png"))
    raw["normalized_mime_type"] = str(outcome.metadata.get("mime_type", "image/png"))


def _register_generated_entry(
    batch: _GenerationBatch,
    raw: dict[str, object],
    ctx: _EntryContext,
    outcome: _RetryOutcome,
) -> str:
    """Apply success metadata, write the sidecar, and record the result row."""
    _stamp_asset_fields(batch, raw, ctx, outcome)
    asset_posix = str(raw["asset_path"])

    frame_review_result = outcome.frame_review_result
    if frame_review_result is not None and frame_review_result.passed:
        _apply_validated_metadata(raw, frame_review_result)
    elif frame_review_result is not None:
        _apply_regeneration_metadata(raw, frame_review_result)
    # else: review was skipped (selective validation) or failed — keep defaults
    else:
        _apply_unreviewed_metadata(raw)

    # Phase 03 — Write frame metadata sidecar alongside the PNG
    _write_frame_sidecar_safely(cast(Path, outcome.target_path), raw, asset_posix, ctx)

    batch.results.append(
        {
            "reference_id": ctx.reference_id,
            "status": "generated",
            "asset_path": asset_posix,
            "provider": str(raw["provider"]),
        }
    )
    return "generated"


def _generate_single_reference(batch: _GenerationBatch, raw: dict[str, object]) -> str:
    """Generate one reference entry; classify the outcome for batch counters."""
    reference_id = str(raw.get("reference_id", "")).strip()
    if not reference_id:
        return ""
    if raw.get("_skip"):
        batch.results.append({"reference_id": reference_id, "status": "skipped"})
        return "skipped"

    ctx = _prepare_entry_context(
        raw, reference_id, batch.char_bibles, batch.identity_states, batch.project_root
    )
    outcome = _run_retry_attempts(batch, raw, ctx)
    if outcome.target_path is not None:
        target_path = outcome.target_path

    # --- Post-retry: update metadata ---
    raw["retry_count"] = outcome.best_attempt  # 0 if all attempts failed
    raw["best_score"] = outcome.best_score

    # Phase 4 — track anchor + detect identity/geometry drift
    ist = batch.identity_states.setdefault(_group_key(raw), {})
    is_anchor = str(raw.get("frame_role", "")).strip().lower() in (
        "front-face",
        "wide-establishing",
    )
    if is_anchor and "anchor_seed" in ist and "target_path" in dir():
        ist["anchor_frame_path"] = target_path
    _apply_identity_drift_policy(batch.identity_states, raw, outcome.frame_review_result, is_anchor)

    if outcome.best_attempt == 0:
        # All attempts failed or were exhausted without a reviewed frame — any
        # terminal failure already recorded its result row in the retry loop.
        return ""

    return _register_generated_entry(batch, raw, ctx, outcome)


def _generate_all_references(
    batch: _GenerationBatch,
    grouped_entries: list[dict[str, object]],
) -> tuple[int, int, int]:
    """Generate every selected entry, accumulating per-outcome counters."""
    counts = {"generated": 0, "skipped": 0}
    for raw in grouped_entries:
        status = _generate_single_reference(batch, raw)
        if status in counts:
            counts[status] += 1
    # Terminal failures tally from their result rows: an entry whose earlier
    # attempt was reviewed-but-not-passed flows through BOTH the terminal path
    # and the generated path, so `failed` is independent of the per-entry
    # classification.
    failed = sum(1 for row in batch.results if row.get("status") == "failed")
    return counts["generated"], counts["skipped"], failed


def _persist_updated_index(
    rt: Any,
    active: dict[str, Any],
    project_id: str,
    grouped_entries: list[dict[str, object]],
) -> Any:
    """Save the regenerated reference index and link it into project state."""
    updated = {
        "project_id": project_id,
        "entries": _copied_entries(grouped_entries),
    }
    ref = _save_reference_index_artifact(rt, active, cast(dict[str, object], updated))
    if ref:
        active["visual_refs"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)
    return ref


def _record_generation_audit(rt: Any, project_id: str, counts: tuple[int, int, int]) -> None:
    """Append the generation outcome to the runtime audit trail."""
    generated, skipped, failed = counts
    rt._record_audit(
        "system",
        "generate_reference_images",
        project_id=project_id,
        generated=str(generated),
        skipped=str(skipped),
        failed=str(failed),
    )


@dataclass(frozen=True)
class _GenerationInputs:
    """Validated request-level inputs for reference generation."""

    active: dict[str, Any]
    project_id: str
    entries: list[object]
    requested_ids: set[str]
    force: bool
    provider: Any
    project_root: Path


def _resolve_generation_inputs(
    rt: Any,
    args: dict[str, object],
) -> _GenerationInputs | dict[str, object]:
    """Validate request-level inputs; return an error payload or the inputs."""
    active = rt.get_active()
    if not active:
        return _error("No active project.")

    project_id = str(active["project_id"])
    data = _load_latest_reference_index(rt, project_id, active)
    if data is None:
        return _error("Reference index not yet generated. Run visual_dev first.")

    entries = data.get("entries", [])
    if not isinstance(entries, list) or not entries:
        return _error("Reference index has no entries to generate.")

    provider = _select_image_provider(rt)
    if provider is None:
        return _error("No image provider is registered for the active project.")

    project_root = rt.project_roots.get(project_id)
    if project_root is None:
        return _error(f"Project root for '{project_id}' not found.")

    return _GenerationInputs(
        active=active,
        project_id=project_id,
        entries=entries,
        requested_ids=_requested_reference_ids(args),
        force=bool(args.get("force", False)),
        provider=provider,
        project_root=project_root,
    )


async def generate_reference_images(args: dict[str, object]) -> dict[str, object]:
    """Generate persisted reference images from the visual-dev reference index."""
    rt = tools_pkg.get_runtime()
    resolved = _resolve_generation_inputs(rt, args)
    if isinstance(resolved, dict):
        return resolved

    # Phase 4 — Identity/geometry consistency: group entries by subject,
    # generate anchor frame first, propagate seed + identity state.
    grouped_entries = _group_and_sort_entries(
        resolved.entries, resolved.requested_ids, resolved.force, resolved.project_root
    )
    store = _services(rt).artifact_store
    batch = _GenerationBatch(
        rt=rt,
        provider=resolved.provider,
        project_root=resolved.project_root,
        identity_states={},  # keyed by group_key
        char_bibles=_load_character_bibles(store, resolved.project_id, grouped_entries),
        results=[],
    )

    generated, skipped, failed = _generate_all_references(batch, grouped_entries)
    if generated == 0 and failed == 0:
        return _ok(
            generated=0,
            skipped=skipped,
            failed=0,
            results=batch.results,
            message="No reference images needed generation.",
        )

    ref = _persist_updated_index(rt, resolved.active, resolved.project_id, grouped_entries)
    _record_generation_audit(rt, resolved.project_id, (generated, skipped, failed))

    # Phase 7 — Build composite sheets for characters with generated frames
    _build_composites(resolved.project_root, resolved.project_id, grouped_entries, store)

    # Phase 11 — Write human-readable index files
    _write_reference_index_files(resolved.project_root, _copied_entries(grouped_entries))

    return _ok(
        generated=generated,
        skipped=skipped,
        failed=failed,
        results=batch.results,
        reference_index_ref=ref,
    )
