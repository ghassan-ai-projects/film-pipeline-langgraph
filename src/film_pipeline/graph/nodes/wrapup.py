"""Wrap-up phase nodes: post, delivery, and the consistency check."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from film_pipeline.graph.nodes._agent import (
    _propagate_side_effects,
    _run_agent,
    _save_artifact,
)
from film_pipeline.graph.nodes._shared import (
    _phase_gate_updates,
)
from film_pipeline.graph.services import _get_services


def post_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    updates: dict[str, Any] = _phase_gate_updates(new_state, phase="post", gate="assembly")
    new_refs: list[str] = []

    result = _run_agent(
        new_state,
        agent_id="failure-handling-agent",
        phase="post",
        task="Create the assembly manifest from generated media and the shot matrix.",
    )
    manifest = result.get("assembly_manifest")
    if manifest is not None:
        ref = _save_artifact(new_state, manifest, "assembly_manifest", "post")
        if ref:
            updates["assembly_manifest_ref"] = ref
            new_refs.append(ref)

    if new_refs:
        updates["artifact_refs"] = new_refs
    _propagate_side_effects(new_state, updates, state)
    return updates


def delivery_node(state: dict[str, Any]) -> dict[str, Any]:
    return _phase_gate_updates(state, phase="delivery", gate="final_delivery")


def consistency_check_node(state: dict[str, Any]) -> dict[str, Any]:
    """Post-phase consistency check: are our outputs still valid?

    Runs staleness detection on all artifacts created in the current phase.
    Warnings are informational (non-blocking) in Phase 3.
    """
    services = _get_services(state)
    if services is None:
        return {}

    from film_pipeline.governance.consistency import check_phase_consistency
    from film_pipeline.graph.orchestrator_state import get_approved_refs

    # `governance` sits below `orchestration` and must not read orchestrator
    # state itself, so the approved-ref registry is supplied from here.
    warnings = check_phase_consistency(state, services, get_approved_refs(state))
    return {"consistency_warnings": warnings} if warnings else {}
