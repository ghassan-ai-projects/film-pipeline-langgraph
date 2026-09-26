"""The generate_reference_images MCP tool."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.mcp.tools.reference_generation.composites import (
    _build_composites,
)
from film_pipeline.mcp.tools.reference_generation.context import (
    _copied_entries,
    _GenerationBatch,
    _load_character_bibles,
    _prepare_entry_context,
    _requested_reference_ids,
)
from film_pipeline.mcp.tools.reference_generation.entries import (
    _group_and_sort_entries,
)
from film_pipeline.mcp.tools.reference_generation.index_files import (
    _save_reference_index_artifact,
    _select_image_provider,
    _write_reference_index_files,
)
from film_pipeline.mcp.tools.reference_generation.outcomes import (
    _register_generated_entry,
    _stamp_retry_stats,
    _update_identity_group,
)
from film_pipeline.mcp.tools.reference_generation.retry_loop import (
    _run_retry_attempts,
)

from ..helpers import (
    _error,
    _load_latest_reference_index,
    _ok,
    _services,
    require_project_state,
)


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
    active = require_project_state(args)
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
    _stamp_retry_stats(raw, outcome)
    # Phase 4 — track anchor + detect identity/geometry drift
    _update_identity_group(batch.identity_states, raw, outcome)

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
