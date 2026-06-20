"""Dynamic action router — computes eligible actions and selects agents.

Two layers:
1. Action routing (phase-based): what action to take next
2. Agent routing (capability-based): which agent performs the action

Agent routing is state-aware — it selects different agents for create,
review, repair, and QC based on capability, blocked providers, and
validation outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PHASE_ORDER = [
    "intake",
    "constitution",
    "development",
    "script",
    "visual_dev",
    "shot_bible",
    "gen_planning",
    "generation",
    "qc",
    "post",
    "delivery",
]

APPROVAL_GATES = {
    "intake": "config",
    "constitution": "constitution",
    "development": "treatment",
    "script": "script",
    "visual_dev": "visual_bible",
    "shot_bible": "shot_bible",
    "gen_planning": "generation_spend",
    "generation": "generation_batch",
    "qc": "qc",
    "post": "assembly",
    "delivery": "final_delivery",
}


@dataclass
class RouterResult:
    eligible: list[str] = field(default_factory=list)
    blocked: list[dict[str, str]] = field(default_factory=list)
    next_action: str = ""
    human_gate: str = ""


@dataclass
class AgentRouteResult:
    """Result of routing a task to an agent."""

    agent_id: str
    routing_reason: str
    fallback: bool = False


# Capability → role mapping for routing
_CREATE_CAPABILITIES = {"writing", "analysis", "planning", "composition"}
_REVIEW_CAPABILITIES = {"review", "validation", "qc", "inspecting"}
_REPAIR_CAPABILITIES = {"repair", "revision", "replan", "correcting"}


def compute_actions(state: dict[str, Any]) -> RouterResult:
    phase = state.get("current_phase", "intake")
    approved = state.get("approved", False)
    human_required = state.get("human_approval_required", False)
    issues: list[dict[str, Any]] = state.get("issues", [])

    result = RouterResult()

    if human_required:
        result.eligible = ["approve_phase", "request_revision"]
        result.next_action = "wait_for_human"
        result.human_gate = APPROVAL_GATES.get(phase, phase)
        return result

    blocking = [i for i in issues if i.get("severity") == "blocking"]
    if blocking:
        result.blocked = [
            {"action": "advance_phase", "reason": f"blocking issue: {b.get('code', '')}"}
            for b in blocking
        ]
        result.eligible = ["repair", "request_human_review"]
        result.next_action = "handle_blockers"
        return result

    if not approved and phase in APPROVAL_GATES:
        result.eligible = ["present_review_package", "approve_phase"]
        result.next_action = "present_review_package"
        result.human_gate = APPROVAL_GATES[phase]
        return result

    idx = PHASE_ORDER.index(phase) if phase in PHASE_ORDER else -1
    if idx >= 0 and idx + 1 < len(PHASE_ORDER):
        next_phase = PHASE_ORDER[idx + 1]
        result.eligible = [f"advance_to_{next_phase}"]
        result.next_action = f"advance_to_{next_phase}"
    else:
        result.eligible = ["wrap"]
        result.next_action = "wrap"

    return result


def route_agent(
    state: dict[str, Any],
    phase: str,
    task_type: str = "create",
    *,
    registry: Any | None = None,
    preferred_capability: str | None = None,
) -> AgentRouteResult:
    """Select an agent based on task type, phase state, and capabilities.

    ``task_type`` is one of: ``"create"``, ``"review"``, ``"repair"``.
    ``preferred_capability`` overrides task-type-based selection.

    When ``registry`` is provided, the selection is validated against
    registered agents. When None, returns a best-effort result using
    the default phase agent.
    """
    from film_pipeline.schemas._base import AgentRole

    # Default agent per phase (for backward compatibility)
    _PHASE_DEFAULT_AGENTS: dict[str, str] = {
        "intake": "intake-classifier-agent",
        "constitution": "film-constitution-agent",
        "development": "treatment-agent",
        "script": "screenwriter-agent",
        "visual_dev": "reference-strategy-planner",
        "shot_bible": "shot-design-agent",
        "gen_planning": "provider-planning-agent",
        "qc": "clip-validator",
        "post": "failure-handling-agent",
    }

    default_agent = _PHASE_DEFAULT_AGENTS.get(phase, "orchestrator-agent")

    # Map preferred_capability to task_type when registry is absent
    if preferred_capability:
        if preferred_capability in _REPAIR_CAPABILITIES:
            task_type = "repair"
        elif preferred_capability in _REVIEW_CAPABILITIES:
            task_type = "review"

    # Route by task type when registry is available
    if registry is not None:
        if task_type == "repair" or preferred_capability in _REPAIR_CAPABILITIES:
            candidates = registry.lookup_by_role(AgentRole.OPERATOR)
            if candidates:
                return AgentRouteResult(
                    agent_id=candidates[0].agent_id,
                    routing_reason=f"repair path for phase '{phase}' after validation failure",
                )
            # Fall through to creator if no repair agents (explicit)
            return AgentRouteResult(
                agent_id=default_agent,
                routing_reason=f"repair requested but no repair agents available for phase '{phase}' — using creator",
                fallback=True,
            )

        if task_type == "review" or preferred_capability in _REVIEW_CAPABILITIES:
            candidates = registry.lookup_by_role(AgentRole.REVIEWER)
            if not candidates:
                candidates = registry.lookup_by_role(AgentRole.VALIDATOR)
            if candidates:
                return AgentRouteResult(
                    agent_id=candidates[0].agent_id,
                    routing_reason=f"review path for phase '{phase}'",
                )
            return AgentRouteResult(
                agent_id=default_agent,
                routing_reason=f"review requested but no validator agents for phase '{phase}' — using creator",
                fallback=True,
            )

        if preferred_capability:
            candidates = registry.lookup_by_capability(preferred_capability)
            if candidates:
                return AgentRouteResult(
                    agent_id=candidates[0].agent_id,
                    routing_reason=f"selected by capability '{preferred_capability}' for phase '{phase}'",
                )

    # Default: create path
    return AgentRouteResult(
        agent_id=default_agent,
        routing_reason=f"create path for phase '{phase}' — using default agent",
    )
