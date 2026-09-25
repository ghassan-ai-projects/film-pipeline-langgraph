"""Generation phase node: gate dispatch readiness and mark matrix rows generated."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from film_pipeline.graph.nodes._agent import (
    _propagate_side_effects,
    _save_artifact,
)
from film_pipeline.graph.nodes._generation_batch_planning import (
    _plan_generation_ledger,
)
from film_pipeline.graph.nodes._shared import (
    _is_new_issue,
    _is_new_ref,
    _phase_gate_updates,
)
from film_pipeline.graph.services import GraphServices, _get_services
from film_pipeline.schemas.matrix_patch import MatrixPatch, MatrixRowUpdate


def _gate_dispatch_readiness(new_state: dict[str, Any]) -> None:
    """Gate C: validate dispatch readiness over the enriched requests."""
    gen_requests = new_state.get("generation_requests")
    if gen_requests is None:
        return
    from film_pipeline.graph.orchestrator_validators import validate_dispatch_readiness

    dispatch_issues = validate_dispatch_readiness(new_state, gen_requests)
    new_state.setdefault("issues", []).extend(dispatch_issues)


def _ledger_rows_by_shot(
    services: GraphServices,
    project_id: str,
) -> dict[str, str]:
    """Map shot_id -> generation_id from the persisted generation ledger."""
    from film_pipeline.generation.ledger import GenerationLedgerManager

    mgr = GenerationLedgerManager(services.artifact_store)
    return {row.shot_id: row.generation_id for row in mgr.load(project_id).rows}


def _row_updates_marking_generated(
    gen_requests: list[Any],
    ledger_rows_by_shot: dict[str, str],
) -> list[MatrixRowUpdate]:
    """Map each dispatched request onto a row update marking its shot generated."""
    row_updates: list[MatrixRowUpdate] = []
    for req in gen_requests:
        if not isinstance(req, dict):
            continue
        sid = str(req.get("shot_id", ""))
        asset_ref = str(
            req.get("asset_ref") or req.get("output_ref") or ledger_rows_by_shot.get(sid, "")
        )
        if sid:
            row_updates.append(
                MatrixRowUpdate(
                    shot_id=sid,
                    set={"status": "generated"},
                    append={"asset_refs": [asset_ref]} if asset_ref else {},
                )
            )
    return row_updates


def _mark_matrix_rows_generated(new_state: dict[str, Any], services: GraphServices | None) -> None:
    """Emit a matrix patch marking requested shots generated with asset refs."""
    gen_requests = new_state.get("generation_requests")
    shot_matrix_ref = str(new_state.get("shot_matrix_ref", ""))
    if not gen_requests or not shot_matrix_ref:
        return

    ledger_rows_by_shot: dict[str, str] = {}
    if services is not None:
        ledger_rows_by_shot = _ledger_rows_by_shot(services, str(new_state.get("project_id", "")))

    row_updates = _row_updates_marking_generated(gen_requests, ledger_rows_by_shot)

    if row_updates:
        patch = MatrixPatch(
            patch_id=f"generation_{new_state.get('project_id', '')}",
            matrix_ref=shot_matrix_ref,
            phase="generation",
            reason="Clips generated — updating row asset references and status.",
            updates=row_updates,
            created_by_agent="generation-scheduler-agent",
        )
        patch_ref = _save_artifact(
            new_state,
            patch,
            "matrix_patch_generation",
            "generation",
            artifact_type="generation_plan",
        )
        if patch_ref:
            new_state["generation_patch_ref"] = patch_ref
            new_state.setdefault("artifact_refs", []).append(patch_ref)


def generation_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state
    gate_updates = _phase_gate_updates(new_state, phase="generation", gate="generation_batch")
    new_state.update(gate_updates)

    services = _get_services(new_state)
    _plan_generation_ledger(new_state, services)
    _gate_dispatch_readiness(new_state)
    _mark_matrix_rows_generated(new_state, services)

    updates: dict[str, Any] = dict(gate_updates)
    new_refs = [r for r in (new_state.get("artifact_refs", []) or []) if _is_new_ref(r, original)]
    if new_refs:
        updates["artifact_refs"] = new_refs
    new_issues = [i for i in (new_state.get("issues", []) or []) if _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    for key in ("generation_ledger_ref", "generation_patch_ref"):
        val = new_state.get(key)
        if val:
            updates[key] = val
    if "generation_requests" in new_state:
        # The generation_requests reducer upserts by request id, so returning
        # the enriched list updates entries in place without duplication.
        updates["generation_requests"] = new_state["generation_requests"]
    _propagate_side_effects(new_state, updates, state)
    return updates
