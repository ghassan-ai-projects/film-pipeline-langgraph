"""Wrap-up phase nodes: post, delivery, and the consistency check.

Nodes take the graph state contract (``StudioGraphState``) and return a partial
update. The return stays ``dict[str, Any]`` rather than the TypedDict because
``_propagate_side_effects`` writes the accumulator under *computed* channel keys
(from ``ORCH_CHANNELS``), and a TypedDict cannot be indexed by a computed key
(``TypedDict key must be a string literal [literal-required]``). Declaring the
TypedDict return would require a ``cast``, which this migration forbids.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from film_pipeline.orchestration.nodes._agent import (
    _propagate_side_effects,
    _run_agent,
    _save_artifact,
    produced_artifact,
)
from film_pipeline.orchestration.nodes._shared import (
    _phase_gate_updates,
)
from film_pipeline.orchestration.services import _get_services
from film_pipeline.orchestration.state_schema import StudioGraphState


def post_node(state: StudioGraphState) -> dict[str, Any]:
    new_state: StudioGraphState = deepcopy(state)
    updates: dict[str, Any] = dict(_phase_gate_updates(new_state, phase="post", gate="assembly"))
    new_refs: list[str] = []

    result = _run_agent(
        new_state,
        agent_id="failure-handling-agent",
        phase="post",
        task="Create the assembly manifest from generated media and the shot matrix.",
    )
    manifest = produced_artifact(new_state, "failure-handling-agent", result)
    if manifest is not None:
        ref = _save_artifact(new_state, manifest, "assembly_manifest", "post")
        if ref:
            updates["assembly_manifest_ref"] = ref
            new_refs.append(ref)

    if new_refs:
        updates["artifact_refs"] = new_refs
    _propagate_side_effects(new_state, updates, dict(state))
    return updates


def delivery_node(state: StudioGraphState) -> StudioGraphState:
    return _phase_gate_updates(state, phase="delivery", gate="final_delivery")


def consistency_check_node(state: StudioGraphState) -> dict[str, Any]:
    """Post-phase consistency check: are our outputs still valid?

    Runs staleness detection on all artifacts created in the current phase.
    Warnings are informational (non-blocking) in Phase 3.
    """
    services = _get_services(state)
    if services is None:
        return {}

    from film_pipeline.governance.consistency import check_phase_consistency
    from film_pipeline.orchestration.orchestrator_state import get_approved_refs

    # `governance` sits below `orchestration` and must not read orchestrator
    # state itself, so the approved-ref registry is supplied from here. Its
    # helpers still take `dict[str, Any]` (naming StudioGraphState there would
    # be the forbidden back-edge), hence the plain copy at this boundary.
    mutable_state: dict[str, Any] = dict(state)
    warnings = check_phase_consistency(mutable_state, services, get_approved_refs(mutable_state))
    return {"consistency_warnings": warnings} if warnings else {}
