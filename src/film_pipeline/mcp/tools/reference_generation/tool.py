"""The generate_reference_images MCP tool."""

from __future__ import annotations

import contextlib
import json
import logging
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


async def generate_reference_images(args: dict[str, object]) -> dict[str, object]:
    """Generate persisted reference images from the visual-dev reference index."""
    rt = tools_pkg.get_runtime()
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

    requested_ids = {
        str(item)
        for item in cast(list[Any], args.get("reference_ids", []))
        if isinstance(item, str) and str(item).strip()
    }
    force = bool(args.get("force", False))
    provider = _select_image_provider(rt)
    if provider is None:
        return _error("No image provider is registered for the active project.")

    project_root = rt.project_roots.get(project_id)
    if project_root is None:
        return _error(f"Project root for '{project_id}' not found.")

    results: list[dict[str, object]] = []
    generated = 0
    skipped = 0
    failed = 0

    # Phase 4 — Identity/geometry consistency: group entries by subject,
    # generate anchor frame first, propagate seed + identity state.
    grouped_entries = _group_and_sort_entries(entries, requested_ids, force, project_root)
    identity_states: dict[str, dict[str, object]] = {}  # keyed by group_key

    # Pre-load CharacterBibles from artifact store for structured prompts
    char_bibles: dict[str, dict[str, object]] = {}
    store = _services(rt).artifact_store
    for raw in grouped_entries:
        if raw.get("_skip"):
            continue
        subject_type = str(raw.get("subject_type", ""))
        subject_id = str(raw.get("subject_id", "")).strip()
        if subject_type == "character" and subject_id and subject_id not in char_bibles:
            try:
                from film_pipeline.schemas._base import FilmPhase

                bible = store.load(project_id, FilmPhase("visual_dev"), "character_bible", 1)
                if isinstance(bible, dict) and bible.get("character_id") == subject_id:
                    char_bibles[subject_id] = bible
            except (FileNotFoundError, ValueError):
                pass  # CharacterBible not yet generated — fall back to prompt_text

    for raw in grouped_entries:
        reference_id = str(raw.get("reference_id", "")).strip()
        if not reference_id:
            continue
        if raw.get("_skip"):
            skipped += 1
            results.append({"reference_id": reference_id, "status": "skipped"})
            continue

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
        provider_kwargs: dict[str, object] = {
            "duration": 0.0,
            "aspect_ratio": aspect_ratio,
        }
        if tier in ("standard", "ultra"):
            group_key = _group_key(raw)
            identity_state = identity_states.get(group_key, {})
            anchor_seed = identity_state.get("anchor_seed")
            if anchor_seed is not None:
                provider_kwargs["seed"] = anchor_seed
            else:
                provider_kwargs["seed"] = hash(shot_id) % (2**31)
                identity_states.setdefault(group_key, {})["anchor_seed"] = provider_kwargs["seed"]
        # Identity consistency is enforced via the ID_REINFORCE prompt block
        # (the Imagen API does not support reference-image conditioning).
        # anchor_frame_path and i2i_active in identity_states are consumed by
        # _reference_prompt() → build_structured_prompt() to strengthen the
        # ID_REINFORCE instruction when Gemini detects subject drift.

        # Phase 5 — Retry loop: max 3 attempts (initial + 2 retries)
        best_score = 0.0
        best_attempt = 0
        retry_prompt = prompt_text
        frame_review_result = None

        for attempt in range(3):
            if attempt > 0:
                # Inject actionable feedback into prompt for retry
                feedback = frame_review_result.actionable_feedback if frame_review_result else ""
                if feedback:
                    retry_prompt = f"{prompt_text} Fix the following: {feedback}"

            try:
                payload = provider.build_payload(retry_prompt, **provider_kwargs)
                job = provider.submit(payload, shot_id)
                job = provider.poll(job)
                downloaded_path = provider.download(job, output_dir)
                metadata = provider.extract_metadata(downloaded_path)
            except Exception as exc:
                if attempt < 2:
                    continue
                raw["generation_status"] = "failed"
                raw["issues"] = [
                    {"code": "generation_failed", "message": str(exc)[:300], "severity": "blocking"}
                ]
                raw["validation"] = {"status": "needs_regeneration", "score": 0.0, "reports": []}
                failed += 1
                results.append(
                    {"reference_id": reference_id, "status": "failed", "error": str(exc)[:200]}
                )
                break

            # Rename
            ext = Path(downloaded_path).suffix or ".png"
            target_name = f"{_reference_job_id(reference_id)}{ext}"
            target_path = Path(output_dir) / target_name
            Path(downloaded_path).rename(target_path)

            # Heuristics
            from film_pipeline.generation.frame_heuristics import run_heuristic_checks

            heuristic_result = run_heuristic_checks(
                target_path, subject_type=str(raw.get("subject_type", "character"))
            )
            if not heuristic_result.passed:
                if attempt < 2:
                    continue
                raw["generation_status"] = "failed"
                raw["issues"] = [
                    {
                        "code": "heuristic_check_failed",
                        "message": f"Heuristics failed: {', '.join(heuristic_result.failures)}",
                        "severity": "blocking",
                    }
                ]
                raw["validation"] = {"status": "needs_regeneration", "score": 0.0, "reports": []}
                failed += 1
                results.append(
                    {
                        "reference_id": reference_id,
                        "status": "failed",
                        "error": f"Heuristics: {', '.join(heuristic_result.failures)}",
                    }
                )
                break

            # Gemini review
            from film_pipeline.generation.frame_reviewer import review_frame, should_review_frame

            frame_review_result = None
            if should_review_frame(raw):
                with contextlib.suppress(Exception):
                    frame_review_result = review_frame(
                        target_path,
                        retry_prompt,
                        model=_services(rt).prompt_runner.model_router.resolve_or_raise(
                            "visual_reasoner"
                        ),
                        subject_type=str(raw.get("subject_type", "character")),
                        frame_id=reference_id,
                    )

            if frame_review_result is not None and frame_review_result.passed:
                best_score = frame_review_result.total
                best_attempt = attempt + 1
                break
            if frame_review_result is not None:
                if frame_review_result.total > best_score:
                    best_score = frame_review_result.total
                    best_attempt = attempt + 1
                if attempt < 2:
                    continue
            # Review skipped or unavailable — accept on first attempt
            if frame_review_result is None:
                best_attempt = attempt + 1
                break

        # --- Post-retry: update metadata ---
        raw["retry_count"] = best_attempt  # 0 if all attempts failed
        raw["best_score"] = best_score

        # Phase 4 — track anchor + detect identity/geometry drift
        gk = _group_key(raw)
        ist = identity_states.setdefault(gk, {})
        is_anchor = str(raw.get("frame_role", "")).strip().lower() in (
            "front-face",
            "wide-establishing",
        )
        if is_anchor and "anchor_seed" in ist and "target_path" in dir():
            ist["anchor_frame_path"] = target_path
        if frame_review_result is not None and not frame_review_result.passed:
            subject_score = float(
                cast(float, frame_review_result.scores.get("subject", {}).get("score", 10))
            )
            if subject_score < 7 and not is_anchor:
                if not ist.get("i2i_active"):
                    ist["i2i_active"] = True
                    ist["i2i_strength"] = 0.5
                elif float(cast(float, ist.get("i2i_strength", 0.5))) > 0.3:
                    ist["i2i_strength"] = 0.3

        if best_attempt == 0:
            # All attempts failed — error already recorded in retry loop
            generated += 0  # counted as failed above
            continue

        rel_path = target_path.resolve().relative_to(project_root.resolve())
        provider_entry = getattr(provider, "entry", None)
        provider_id = str(getattr(provider_entry, "provider_id", ""))
        raw["asset_path"] = rel_path.as_posix()
        raw["provider"] = provider_id
        raw["tier"] = tier
        raw["prompt_text"] = prompt_text
        raw["source_frames"] = [rel_path.as_posix()]
        raw["original_mime_type"] = str(metadata.get("mime_type", "image/png"))
        raw["normalized_mime_type"] = str(metadata.get("mime_type", "image/png"))

        if frame_review_result is not None and frame_review_result.passed:
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
        elif frame_review_result is not None and not frame_review_result.passed:
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
                    "message": frame_review_result.actionable_feedback
                    or "Gemini review below threshold.",
                    "severity": "warning",
                }
            ]
        # else: review was skipped (selective validation) or failed — keep defaults
        else:
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
        generated += 1

        # Phase 03 — Write frame metadata sidecar alongside the PNG
        try:
            from film_pipeline.generation.frame_sidecar import write_frame_sidecar
            from film_pipeline.schemas.reference import ReferenceFrame

            frame = ReferenceFrame(
                frame_path=rel_path.as_posix(),
                reference_id=reference_id,
                subject_type=str(raw.get("subject_type", "")),
                subject_id=str(raw.get("subject_id", "")),
                provider_id=str(raw.get("provider", "")),
                model_id="",
                tier=tier,
                seed=cast(int | None, provider_kwargs.get("seed")),
                prompt_text=prompt_text,
                frame_role=str(raw.get("frame_role", "")),
                expression=str(raw.get("expression", "")) or None,
                lighting=str(raw.get("lighting", "")) or None,
                aspect_ratio=aspect_ratio,
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

        results.append(
            {
                "reference_id": reference_id,
                "status": "generated",
                "asset_path": rel_path.as_posix(),
                "provider": provider_id,
            }
        )

    if generated == 0 and failed == 0:
        return _ok(
            generated=0,
            skipped=skipped,
            failed=0,
            results=results,
            message="No reference images needed generation.",
        )

    updated = {
        "project_id": project_id,
        "entries": [dict(r) for r in grouped_entries],  # use modified copies
    }
    ref = _save_reference_index_artifact(rt, active, cast(dict[str, object], updated))
    if ref:
        active["visual_refs"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)
    rt._record_audit(
        "system",
        "generate_reference_images",
        project_id=project_id,
        generated=str(generated),
        skipped=str(skipped),
        failed=str(failed),
    )

    # Phase 7 — Build composite sheets for characters with generated frames
    _build_composites(project_root, project_id, grouped_entries, _services(rt).artifact_store)

    # Phase 11 — Write human-readable index files
    _write_reference_index_files(project_root, cast(list[dict[str, object]], updated["entries"]))

    return _ok(
        generated=generated,
        skipped=skipped,
        failed=failed,
        results=results,
        reference_index_ref=ref,
    )
