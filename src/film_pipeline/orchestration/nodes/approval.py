"""Approval gate and revision nodes — the human-in-the-loop control plane."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from film_pipeline.orchestration.nodes._agent import _run_agent
from film_pipeline.orchestration.nodes._repair_loop import (
    _PHASE_NODES,
    repair_phase_node,
)
from film_pipeline.orchestration.nodes._shared import _apply_external_state
from film_pipeline.orchestration.orchestrator_state import require_human_approval
from film_pipeline.orchestration.services import _get_services

# The bounded repair loop lives in ``_repair_loop``; these re-exports keep the
# historical ``graph.nodes.approval`` import paths working.
__all__ = ["_PHASE_NODES", "repair_phase_node"]


def _run_orchestrator_agent(state: dict[str, Any]) -> dict[str, Any] | None:
    """Run the orchestrator agent to decide approve/revise/escalate.

    Returns the agent's decision dict or ``None`` if the agent is unavailable
    (no services, no model — fall through to human gate).
    """
    services = _get_services(state)
    if services is None:
        return None

    result = _run_agent(
        state,
        agent_id="orchestrator-agent",
        phase=str(state.get("current_phase", "")),
        task=(
            "Review the phase output against the target runtime and constitution. "
            "Decide: approve (output is sound), revise (give one focused suggestion), "
            "or escalate (stuck or fundamentally wrong)."
        ),
    )
    if result.get("status") in ("no_services", "agent_not_found", "no_impl"):
        return None
    action = result.get("action")
    if action not in ("approve", "revise", "escalate"):
        return None
    return result


def _count_blocking_issues(state: dict[str, Any]) -> int:
    """Count blocking-severity entries in state's issues (pure read)."""
    issues = state.get("issues", []) or []
    return sum(1 for i in issues if i.get("severity") == "blocking")


def _orchestrator_working_state(state: dict[str, Any]) -> dict[str, Any]:
    """Deep-copied ``_orchestrator__*`` slice of state with defaults ensured."""
    from film_pipeline.orchestration.orchestrator_state import ensure_orchestrator_state

    working = {
        key: deepcopy(value) for key, value in state.items() if key.startswith("_orchestrator__")
    }
    ensure_orchestrator_state(working)
    return working


def _apply_headless_decision(state: dict[str, Any], stalled: bool) -> dict[str, Any] | None:
    """Apply an autonomous orchestrator decision; ``None`` falls through to the fallback."""
    if stalled:
        return None
    orch_decision = _run_orchestrator_agent(state)
    if orch_decision is None:
        return None
    action = orch_decision.get("action", "escalate")
    if action == "approve":
        return approve_phase_node(state)
    if action == "revise":
        state["_repair_feedback"] = orch_decision.get("feedback", "")
        preserve = orch_decision.get("preserve", [])
        if preserve:
            state["_repair_feedback"] += "\n\nPreserve: " + "; ".join(str(p) for p in preserve)
        return request_revision_node(state)
    # escalate: fall through to clean/buggy fallback below
    return None


def _advisory_recommendation(state: dict[str, Any], stalled: bool) -> dict[str, Any] | None:
    """Run the orchestrator agent for an advisory recommendation; the human decides."""
    if stalled:
        return None
    orch_decision = _run_orchestrator_agent(state)
    if orch_decision is None:
        return None
    return {
        "action": orch_decision.get("action", "escalate"),
        "feedback": orch_decision.get("feedback", ""),
        "preserve": orch_decision.get("preserve", []),
    }


def _build_gate_payload(
    state: dict[str, Any],
    phase: str,
    stalled: bool,
    recommendation: dict[str, Any] | None,
) -> dict[str, Any]:
    """Assemble the interrupt payload shown to the human reviewer (pre-interrupt only)."""
    gate = str(state.get("human_approval_phase", ""))
    blocking_count = _count_blocking_issues(state)

    allowed_actions: list[str] = []
    if blocking_count == 0:
        allowed_actions.append("approve_phase")
    if stalled:
        allowed_actions.append("escalate")
    else:
        allowed_actions.append("request_revision")

    return {
        "project_id": state.get("project_id", ""),
        "phase": phase,
        "gate": gate,
        "artifact_refs": state.get("artifact_refs", []),
        "blocking_issue_count": blocking_count,
        "stalled": stalled,
        "allowed_actions": allowed_actions,
        "recommendation": recommendation,
    }


def _normalize_decision(decision: Any) -> tuple[str, str, dict[str, Any]]:
    """Normalize a resume value into ``(action, note, external_state)``.

    ``external_state`` carries mutations sent via ``Command(resume=...)``;
    empty when the resume value does not bear a dict-shaped ``_external_state``.
    """
    if isinstance(decision, dict):
        external_state = decision.get("_external_state")
        return (
            str(decision.get("action", "")),
            str(decision.get("note", "")),
            external_state if isinstance(external_state, dict) else {},
        )
    if isinstance(decision, str):
        return decision, "", {}
    return "await", "", {}


def _merge_external_fixes(
    state: dict[str, Any],
    state_updates: dict[str, Any],
) -> dict[str, Any]:
    """Merge externally resolved issues into state before the approval guard runs.

    Ordering matters: stale blockers (already fixed outside the graph) would
    otherwise wedge the gate.
    """
    if not state_updates.get("issues"):
        return state
    from film_pipeline.orchestration.state_schema import merge_issues

    return {
        **state,
        "issues": merge_issues(
            cast("list[dict[str, object]]", state.get("issues", [])),
            cast("list[dict[str, object]]", state_updates["issues"]),
        ),
    }


def _route_decision(
    state: dict[str, Any],
    action: str,
    note: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch a normalized gate decision; unrecognized actions yield bare updates."""
    if action in ("approve", "approve_phase"):
        result = approve_phase_node(state)
        result.update(updates)
        return result
    if action in ("revise", "request_revision"):
        if note:
            state["_revision_note"] = note
        result = request_revision_node(state)
        result.update(updates)
        return result
    return updates


def await_approval_node(state: dict[str, Any]) -> dict[str, Any]:
    """Pause the graph for human review. Resumes via Command(resume=decision).

    When ``require_human_approval`` is enabled (the default), the node always
    calls LangGraph's ``interrupt()`` so the human gate cannot be silently
    bypassed. The orchestrator agent may produce a recommendation, but it is
    only advisory and is surfaced inside the interrupt payload.

    In headless / auto-approve mode the orchestrator agent may act
    autonomously; when it is unavailable or escalates, clean phases are
    approved and phases with blocking issues are routed to the bounded repair
    loop.

    Short-circuits when ``approved`` is already ``True`` — the phase node
    auto-approved (e.g. headless/auto-approve profile). The downstream
    ``after_approval`` routing will advance to the next phase.
    """
    if state.get("approved"):
        return {}

    from film_pipeline.orchestration.orchestrator_state import is_stalled

    phase = str(state.get("current_phase", ""))
    stalled = is_stalled(state, phase)
    require_human = require_human_approval(state)

    # ── Headless / auto-approve mode ───────────────────────────────────
    if not require_human:
        return _apply_headless_decision(state, stalled) or (
            approve_phase_node(state)
            if _count_blocking_issues(state) == 0
            else {"approved": False, "human_approval_required": False}
        )

    # ── Human gate (default) ───────────────────────────────────────────
    # The orchestrator may prepare a recommendation, but the human decides.
    recommendation = _advisory_recommendation(state, stalled)

    from langgraph.types import interrupt

    payload = _build_gate_payload(state, phase, stalled, recommendation)

    decision = interrupt(payload)
    action, note, external_state = _normalize_decision(decision)
    state_updates = _apply_external_state(state, external_state) if external_state else {}
    state = _merge_external_fixes(state, state_updates)
    return _route_decision(state, action, note, state_updates)


def approve_phase_node(state: dict[str, Any]) -> dict[str, Any]:
    """Approve the current phase. Returns a partial state update.

    Returning the full state would re-append every entry of the
    append-only reducer channels (``issues``, ``artifact_refs``, ...), so
    only the keys this node actually changes are returned.
    """
    # ── Guard: reject approval when structural issues exist ──────────
    if _count_blocking_issues(state):
        return {"approved": False, "_approval_blocked_by_issues": True}

    # Promote all candidate refs to approved
    from film_pipeline.orchestration.orchestrator_state import (
        get_approved_refs,
        get_candidate_refs,
        set_approved_ref,
    )

    working = _orchestrator_working_state(state)
    for family, ref in get_candidate_refs(state).items():
        set_approved_ref(working, family, ref)

    return {
        "approved": True,
        "human_approval_required": False,
        "_approval_blocked_by_issues": False,
        "_orchestrator__approved_refs": get_approved_refs(working),
    }


def request_revision_node(state: dict[str, Any]) -> dict[str, Any]:
    """Route the current phase to revision. Returns a partial state update."""
    revision_note = str(state.get("_revision_note", ""))
    # Record durable revision request via orchestrator state helpers
    from film_pipeline.orchestration.orchestrator_state import (
        add_revision_request,
        get_all_revisions,
    )

    working = _orchestrator_working_state(state)
    artifact_refs = list(state.get("artifact_refs", []) or [])
    add_revision_request(working, artifact_refs, note="Human requested revision.")

    return {
        "approved": False,
        "human_approval_required": False,
        "_revision_note": "",
        "issues": [
            {
                "issue_id": "rev",
                "severity": "warning",
                "code": "REVISION_REQUESTED",
                "message": revision_note or "Human requested revision.",
            }
        ],
        "_orchestrator__pending_revisions": get_all_revisions(working),
    }
