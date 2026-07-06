"""Reference-image generation pipeline tools and supporting helpers."""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any, cast

import film_pipeline.mcp.tools as tools_pkg

from .helpers import (
    _error,
    _latest_artifact_version,
    _load_latest_reference_index,
    _ok,
    _services,
)


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


def _group_key(entry: dict[str, object]) -> str:
    """Deterministic group key for identity/geometry consistency."""
    subject_type = str(entry.get("subject_type", "")).strip().lower()
    subject_id = str(entry.get("subject_id", "")).strip().lower()
    return f"{subject_type}:{subject_id}"


def _group_and_sort_entries(
    entries: list[object],
    requested_ids: set[str],
    force: bool,
    project_root: Path,
) -> list[dict[str, object]]:
    """Filter, group, and sort entries — anchor frame first per group.

    Character anchors: 'front-face'. Environment anchors: 'wide-establishing'.
    Entries already generated (asset_path present, not force) are tagged _skip.
    """
    ANCHOR_PRIORITY = {"front-face": 0, "wide-establishing": 0}

    filtered: list[dict[str, object]] = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        ref_id = str(raw.get("reference_id", "")).strip()
        if not ref_id:
            continue
        if requested_ids and ref_id not in requested_ids:
            continue
        r = dict(raw)
        r["_reference_id"] = ref_id
        if r.get("asset_path") and not force:
            existing_path = project_root / str(r.get("asset_path", ""))
            if existing_path.exists():
                r["_skip"] = True
        filtered.append(r)

    # Sort: group by key, anchor first within each group
    def sort_key(r: dict[str, object]) -> tuple[str, int, str]:
        gk = _group_key(r)
        role = str(r.get("frame_role", "")).strip().lower()
        anchor_prio = ANCHOR_PRIORITY.get(role, 50)
        return (gk, anchor_prio, str(r.get("reference_id", "")))

    filtered.sort(key=sort_key)
    return filtered


def _reference_output_dir(entry: dict[str, object], project_root: Path) -> Path:
    """Compute organized output directory for a reference entry.

    Produces paths like:
        references/characters/leo/master-frames/
        references/environments/studio/master-frames/
        references/props/paintbrush/
        references/style/
        references/scale/
    """
    subject_type = str(entry.get("subject_type", "misc")).strip().lower()
    subject_id = str(entry.get("subject_id", "unknown")).strip().lower()

    if subject_type in ("character", "environment", "prop"):
        return project_root / "references" / f"{subject_type}s" / subject_id / "master-frames"
    return project_root / "references" / subject_type


def _reference_prompt(
    entry: dict[str, object],
    *,
    character_bible: dict[str, object] | None = None,
    constitution: dict[str, object] | None = None,
    identity_state: dict[str, object] | None = None,
) -> str:
    """Build a structured generation prompt from domain data blocks.

    Delegates to ``build_structured_prompt()`` which assembles character or
    environment prompts from locked blocks (CharacterBible, FilmConstitution).
    Falls back to the entry's ``prompt_text`` when no structured sources exist.
    """
    from film_pipeline.generation.prompt_builder import build_structured_prompt

    return build_structured_prompt(
        dict(entry),
        character_bible=dict(character_bible) if character_bible else None,
        constitution=dict(constitution) if constitution else None,
        identity_state=dict(identity_state) if identity_state else None,
    )


def _reference_aspect_ratio(entry: dict[str, object]) -> str:
    asset_type = str(entry.get("asset_type", ""))
    subject_type = str(entry.get("subject_type", ""))
    if "environment" in asset_type or subject_type == "environment":
        return "16:9"
    if "style" in asset_type or "camera" in asset_type or "scale" in asset_type:
        return "16:9"
    return "3:4"


def _reference_job_id(reference_id: str) -> str:
    return reference_id.replace(":", "-").replace("/", "-")


def _build_composites(
    project_root: Path,
    project_id: str,
    entries: list[dict[str, object]],
    artifact_store: Any,
) -> None:
    """Build composite sheets from generated frames (Phase 7)."""
    from film_pipeline.generation.compositor import (
        build_character_identity_sheet,
        build_environment_board,
    )
    from film_pipeline.schemas._base import FilmPhase

    # Resolve color palettes from EnvironmentBible artifacts
    env_palettes: dict[str, list[str]] = {}
    for entry in entries:
        if str(entry.get("subject_type", "")) != "environment":
            continue
        subject_id = str(entry.get("subject_id", "")).strip()
        if not subject_id or subject_id in env_palettes:
            continue
        try:
            bible = artifact_store.load(project_id, FilmPhase("visual_dev"), "environment_bible", 1)
            if isinstance(bible, dict):
                palette = bible.get("color_palette", [])
                if isinstance(palette, list) and palette:
                    env_palettes[subject_id] = [str(c) for c in palette]
        except (FileNotFoundError, ValueError):
            pass

    # Group entries by character subject
    char_frames: dict[str, dict[str, Path]] = {}
    for entry in entries:
        if str(entry.get("subject_type", "")) != "character":
            continue
        if entry.get("generation_status") not in ("validated", "generated"):
            continue
        subject_id = str(entry.get("subject_id", "")).strip()
        if not subject_id:
            continue
        role = str(entry.get("frame_role", "")).strip()
        asset = str(entry.get("asset_path", "")).strip()
        if not role or not asset:
            continue
        frame_path = project_root / asset
        if frame_path.exists():
            char_frames.setdefault(subject_id, {})[role] = frame_path

    for subject_id, frames in char_frames.items():
        sheet_path = project_root / "references" / "characters" / subject_id / "identity-sheet.png"
        try:
            build_character_identity_sheet(subject_id, subject_id, frames, sheet_path)
            # Phase 8 — Composite validation
            _validate_composite(sheet_path, "character_identity_sheet", subject_id)
        except Exception:
            pass

    # Group entries by environment subject
    env_frames: dict[str, dict[str, Path]] = {}
    for entry in entries:
        if str(entry.get("subject_type", "")) != "environment":
            continue
        if entry.get("generation_status") not in ("validated", "generated"):
            continue
        subject_id = str(entry.get("subject_id", "")).strip()
        if not subject_id:
            continue
        role = str(entry.get("frame_role", "")).strip()
        asset = str(entry.get("asset_path", "")).strip()
        if not role or not asset:
            continue
        frame_path = project_root / asset
        if frame_path.exists():
            env_frames.setdefault(subject_id, {})[role] = frame_path

    for subject_id, frames in env_frames.items():
        sheet_path = (
            project_root / "references" / "environments" / subject_id / "environment-board.png"
        )
        try:
            build_environment_board(
                subject_id,
                subject_id,
                frames,
                sheet_path,
                palette_colors=env_palettes.get(subject_id),
            )
            # Phase 8 — Composite validation
            _validate_composite(sheet_path, "environment_board", subject_id)
        except Exception:
            pass

    # Phase 05 — Additional composite templates
    _build_optional_sheets(project_root, project_id, char_frames, env_palettes)


def _build_optional_sheets(
    project_root: Path,
    project_id: str,
    char_frames: dict[str, dict[str, Path]],
    env_palettes: dict[str, list[str]],
) -> None:
    """Build expression sheets, scale sheet, and style board (non-blocking)."""
    from film_pipeline.generation.compositor import (
        build_expression_sheet,
        build_scale_sheet,
        build_style_board,
    )

    # Expression sheet per character
    for subject_id, frames in char_frames.items():
        try:
            sheet_path = (
                project_root / "references" / "characters" / subject_id / "expression-sheet.png"
            )
            build_expression_sheet(subject_id, subject_id, frames, sheet_path)
        except Exception:
            pass

    # Scale sheet — all characters' full-body frames
    full_body_frames: dict[str, Path] = {}
    for subject_id, frames in char_frames.items():
        fb = frames.get("full-body")
        if fb and fb.exists():
            full_body_frames[subject_id] = fb
    if full_body_frames:
        try:
            sheet_path = project_root / "references" / "scale" / "scale-sheet.png"
            build_scale_sheet(project_id, full_body_frames, sheet_path)
        except Exception:
            pass

    # Style board — use first environment's palette or defaults
    palette: list[str] = []
    for p in env_palettes.values():
        palette = p
        break
    try:
        sheet_path = project_root / "references" / "style" / "style-board.png"
        build_style_board(project_id, palette, "", "", "", sheet_path)
    except Exception:
        pass


def _validate_composite(sheet_path: Path, sheet_type: str, subject_id: str) -> None:
    """Run Gemini composite validation on a sheet (Phase 8). Non-blocking."""
    try:
        from film_pipeline.agents.model_routing import ModelRouter
        from film_pipeline.generation.sheet_reviewer import review_composite_sheet

        router = ModelRouter()
        review_composite_sheet(
            sheet_path,
            sheet_type,
            subject_id,
            model=router.resolve_or_raise("visual_reasoner"),
        )
    except Exception:
        pass  # validation failure doesn't block


def _write_reference_index_files(project_root: Path, entries: list[dict[str, object]]) -> None:
    """Write human-readable reference index files (Phase 11)."""
    idx_dir = project_root / "references" / "index"
    idx_dir.mkdir(parents=True, exist_ok=True)

    # reference-index.json
    index_data = {
        "project_id": "",
        "generated_at": "",
        "entries": [
            {
                "reference_id": str(e.get("reference_id", "")),
                "asset_type": str(e.get("asset_type", "")),
                "subject_id": str(e.get("subject_id", "")),
                "asset_path": str(e.get("asset_path", "")),
                "provider": str(e.get("provider", "")),
                "validation": e.get("validation", {}),
                "locked": bool(e.get("locked", False)),
            }
            for e in entries
        ],
    }
    (idx_dir / "reference-index.json").write_text(json.dumps(index_data, indent=2, default=str))

    # reference-validation-summary.json
    scores = [
        float(cast(float, e.get("quality_score", 0))) for e in entries if e.get("quality_score")
    ]
    validated = sum(1 for e in entries if e.get("generation_status") == "validated")
    summary = {
        "project_id": "",
        "total_entries": len(entries),
        "validated": validated,
        "failed": sum(1 for e in entries if e.get("generation_status") == "failed"),
        "average_score": sum(scores) / len(scores) if scores else 0.0,
    }
    (idx_dir / "reference-validation-summary.json").write_text(json.dumps(summary, indent=2))


def _select_image_provider(rt: Any) -> Any | None:
    for provider_id in rt.list_providers():
        adapter = rt.get_provider(provider_id)
        entry = getattr(adapter, "entry", None)
        if entry is not None and getattr(entry, "provider_type", "") == "image":
            return adapter
    return None


def _save_reference_index_artifact(
    rt: Any,
    state: dict[str, object],
    artifact: dict[str, object],
) -> str | None:
    from datetime import UTC, datetime

    from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata

    project_id = str(state.get("project_id", ""))
    store = _services(rt).artifact_store
    version = (
        _latest_artifact_version(store, project_id, FilmPhase("visual_dev"), "reference_index") + 1
    )
    meta = ArtifactMetadata(
        artifact_id="reference_index",
        artifact_type=ArtifactType.REFERENCE_INDEX,
        project_id=project_id,
        phase=FilmPhase("visual_dev"),
        version=version,
        status=ArtifactStatus.CANDIDATE,
        parents=[],
        created_by="mcp.generate_reference_images",
        created_at=datetime.now(UTC),
    )
    from film_pipeline.schemas.reference import ReferenceIndex

    entries = _reference_entries_from_grouped(artifact)
    reference_index = ReferenceIndex(project_id=project_id, entries=entries)
    store.save(reference_index, meta)
    return f"artifact:reference_index:v{version}"


def _reference_entries_from_grouped(
    artifact: dict[str, object],
) -> list[Any]:
    """Build typed ``ReferenceIndexEntry`` objects from grouped raw entries."""
    from film_pipeline.schemas.reference import ReferenceIndexEntry

    raw_entries = cast(list[Any], artifact.get("entries", []))
    entries: list[ReferenceIndexEntry] = []
    for raw in raw_entries or []:
        if not isinstance(raw, dict):
            continue
        data = dict(raw)
        data.setdefault("asset_path", "")
        data.setdefault("asset_type", "")
        data.setdefault("subject_type", "")
        data.setdefault("subject_id", "")
        data.setdefault("quality_score", 0.0)
        entries.append(ReferenceIndexEntry.model_validate(data))
    return entries
