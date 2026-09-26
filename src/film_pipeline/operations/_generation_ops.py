"""Generation batch operations for the operator service.

Owns the plan → approve spend → start → poll sequencing plus the text-only
policy path. ``OperatorService`` exposes these as thin delegate methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from film_pipeline.filmspec import is_text_only_policy, text_only_generation_requests
from film_pipeline.operations.errors import BackendOperationError
from film_pipeline.operations.models import GenerationWorkspace
from film_pipeline.storage.manifest import read_manifest
from film_pipeline.storage.runtime_gateway import artifact_store_root as artifact_root

if TYPE_CHECKING:
    from film_pipeline.generation.executor import GenerationExecutor
    from film_pipeline.operations.operator import OperatorService


def get_generation_workspace(
    svc: OperatorService, project_id: str | None = None
) -> GenerationWorkspace:
    """Summarize the generation ledger for the operator."""
    state = svc._state_for_project(project_id)
    project_id_value = str(state["project_id"])
    provider, model = svc.runtime.default_video_provider()

    if is_text_only_policy(state):
        return _text_only_workspace(state, project_id_value, provider, model)

    executor = _generation_executor(svc)
    rows = executor.status_rows(project_id_value)
    counts = _count_rows_by_status(rows)
    return GenerationWorkspace(
        project_id=project_id_value,
        phase=str(state.get("current_phase", "")),
        provider=provider,
        model=model,
        rows=rows,
        planned=counts["prepared"],
        submitted=counts["submitted"],
        running=counts["running"],
        completed=counts["completed"],
        failed=counts["failed"],
        next_step=_generation_next_step(rows, counts),
    )


def plan_generation(svc: OperatorService, project_id: str | None = None) -> GenerationWorkspace:
    """Plan a generation batch for every shot in the approved shot matrix."""
    state = svc._state_for_project(project_id)
    project_id_value = str(state["project_id"])
    if is_text_only_policy(state):
        _complete_text_only_generation(svc, state, project_id_value)
        return get_generation_workspace(svc, project_id_value)
    executor = _generation_executor(svc)
    provider, model = svc.runtime.default_video_provider()
    try:
        executor.plan(project_id_value, provider=provider, model=model)
    except ValueError as exc:
        raise BackendOperationError(str(exc)) from exc
    _sync_generation_requests(svc, state, project_id_value)
    return get_generation_workspace(svc, project_id_value)


def approve_generation_spend(
    svc: OperatorService,
    project_id: str | None = None,
) -> GenerationWorkspace:
    """Approve planned generation rows by marking them SUBMITTED.

    The cost ceiling that used to live here was self-referential — it was derived
    from the planner's own estimate and compared against sums of that same
    estimate, so it could not refuse a batch the planner itself had produced.
    Removing it removes no real check; the PREPARED -> SUBMITTED transition it
    guarded is the part that matters and is unchanged.
    """
    state = svc._state_for_project(project_id)
    project_id_value = str(state["project_id"])
    if is_text_only_policy(state):
        return get_generation_workspace(svc, project_id_value)
    executor = _generation_executor(svc)
    try:
        executor.approve_spend(project_id_value)
    except ValueError as exc:
        raise BackendOperationError(str(exc)) from exc
    _sync_generation_requests(svc, state, project_id_value)
    return get_generation_workspace(svc, project_id_value)


def start_generation(svc: OperatorService, project_id: str | None = None) -> GenerationWorkspace:
    """Submit approved generation rows to their providers."""
    state = svc._state_for_project(project_id)
    project_id_value = str(state["project_id"])
    if is_text_only_policy(state):
        return get_generation_workspace(svc, project_id_value)
    executor = _generation_executor(svc)
    executor.start(project_id_value)
    _sync_generation_requests(svc, state, project_id_value)
    return get_generation_workspace(svc, project_id_value)


def poll_generation(svc: OperatorService, project_id: str | None = None) -> GenerationWorkspace:
    """Poll running generations once, delivering completed outputs."""
    state = svc._state_for_project(project_id)
    project_id_value = str(state["project_id"])
    if is_text_only_policy(state):
        return get_generation_workspace(svc, project_id_value)
    executor = _generation_executor(svc)
    executor.poll_once(project_id_value)
    _sync_generation_requests(svc, state, project_id_value)
    return get_generation_workspace(svc, project_id_value)


def preview_generation_prompts(
    svc: OperatorService, project_id: str | None = None
) -> list[dict[str, Any]]:
    """Resolve the exact prompt each shot will send to its provider.

    Available as soon as the shot matrix exists so the operator can read
    and validate prompts during gen_planning review — before any spend.
    """
    state = svc._state_for_project(project_id)
    project_id_value = str(state["project_id"])
    executor = _generation_executor(svc)
    provider, model = svc.runtime.default_video_provider()
    previews: list[dict[str, Any]] = []
    for row in executor.load_shot_rows(project_id_value):
        shot_id = _shot_row_id(row)
        if not shot_id:
            continue
        previews.append(
            {
                "shot_id": shot_id,
                "scene_id": str(row.get("scene_id", "")),
                "provider": provider,
                "model": model,
                "duration_seconds": row.get("duration_seconds", 5),
                "prompt": executor.resolve_prompt(project_id_value, shot_id, row),
            }
        )
    return previews


def _generation_executor(svc: OperatorService) -> GenerationExecutor:
    from film_pipeline.generation.executor import GenerationExecutor

    if svc.runtime.services is None:
        raise BackendOperationError("artifact store is not configured.")
    return GenerationExecutor(
        svc.runtime.services.artifact_store,
        svc.runtime.provider_adapters,
    )


def _sync_generation_requests(svc: OperatorService, state: dict[str, Any], project_id: str) -> None:
    """Mirror ledger rows into graph state so approval gates can pass."""
    executor = _generation_executor(svc)
    requests = executor.dispatchable_requests(project_id)
    if requests:
        state["generation_requests"] = requests
        _strip_stale_request_issues(state)
    _store_project_state(svc, state, project_id)


def _store_project_state(svc: OperatorService, state: dict[str, Any], project_id: str) -> None:
    """Write the updated state back into the runtime and persist it."""
    svc.runtime.projects[project_id] = state
    svc.runtime._persist_project_state(project_id)


def _strip_stale_request_issues(state: dict[str, Any]) -> None:
    from film_pipeline.filmspec import STALE_GENERATION_REQUEST_CODES
    from film_pipeline.orchestration.state_schema import remove_issues_by_code

    remove_issues_by_code(state, STALE_GENERATION_REQUEST_CODES)


def _count_rows_by_status(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"prepared": 0, "submitted": 0, "running": 0, "completed": 0, "failed": 0}
    for row in rows:
        status = str(row.get("status", ""))
        if status in counts:
            counts[status] += 1
    return counts


def _generation_next_step(rows: list[dict[str, Any]], counts: dict[str, int]) -> str:
    if not rows:
        return "plan"
    if counts["prepared"]:
        return "approve_spend"
    if counts["submitted"]:
        return "start"
    if counts["running"]:
        return "poll"
    if counts["failed"] and not counts["completed"]:
        return "review_failures"
    return "approve_phase"


def _shot_row_id(row: dict[str, Any]) -> str:
    """Identify a shot-matrix row, falling back to its scene id."""
    return str(row.get("shot_id", "") or row.get("scene_id", "")).strip()


def _complete_text_only_generation(
    svc: OperatorService, state: dict[str, Any], project_id: str
) -> None:
    """Satisfy generation gates without producing clips or frames.

    Creates completed generation_requests from the shot matrix and records
    a text-only manifest entry so the project can advance to QC/delivery.
    """
    if state.get("_text_only_generation_completed"):
        return
    executor = _generation_executor(svc)
    shot_rows = executor.load_shot_rows(project_id)
    provider, model = svc.runtime.default_video_provider()
    requests = text_only_generation_requests(project_id, shot_rows, provider, model)
    state["generation_requests"] = requests
    state["_text_only_generation_completed"] = True
    _strip_stale_request_issues(state)
    _record_text_only_manifest(svc, project_id)
    _store_project_state(svc, state, project_id)


def _text_only_workspace(
    state: dict[str, Any],
    project_id: str,
    provider: str,
    model: str,
) -> GenerationWorkspace:
    requests = state.get("generation_requests", []) or []
    completed = sum(
        1
        for req in requests
        if isinstance(req, dict) and str(req.get("status", "")).lower() == "completed"
    )
    return GenerationWorkspace(
        project_id=project_id,
        phase=str(state.get("current_phase", "")),
        provider=provider,
        model=model,
        rows=[],
        planned=0,
        submitted=0,
        running=0,
        completed=completed,
        failed=0,
        next_step="approve_phase" if completed > 0 else "plan",
    )


def _record_text_only_manifest(svc: OperatorService, project_id: str) -> None:
    from film_pipeline.storage.manifest import AssetEntry, AssetManifest, write_manifest

    root = artifact_root(svc.runtime)
    if root is None:
        return
    manifest = read_manifest(project_id, root=root)
    entries = list(manifest.entries) if manifest else []
    if not any(entry.asset_id == "text-only-delivery" for entry in entries):
        entries.append(
            AssetEntry(
                asset_id="text-only-delivery",
                kind="text_only_delivery",
                shot_id="",
                scene_id="",
                path="",
            )
        )
        write_manifest(AssetManifest(project_id=project_id, entries=entries), root=root)
