"""Dynamic action router — computes eligible actions and selects agents.

Two layers:
1. Action routing (state-driven): what action to take next, taking into
   account provider health, budget state, failure decisions, revision
   requests, and profile policy.
2. Agent routing (capability-based): which agent performs the action,
   with KB context selection.

The orchestrator state domain (``orchestrator_state.py``) is the source
of truth for all routing-relevant state beyond the base graph fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from film_pipeline.graph import orchestrator_state as ostate

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

# Actions that can operate in any phase regardless of provider health
_PHASE_AGNOSTIC_PHASES = {
    "intake",
    "constitution",
    "development",
    "script",
    "visual_dev",
    "shot_bible",
    "gen_planning",
    "qc",
    "post",
    "delivery",
}

# Actions that require a healthy generation-capable provider
_GENERATION_DEPENDENT_PHASES = {"generation"}

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
    kb_context_ref: str = ""
    review_strategy: str = "single"


# Capability → role mapping for routing
_CREATE_CAPABILITIES = {"writing", "analysis", "planning", "composition"}
_REVIEW_CAPABILITIES = {"review", "validation", "qc", "inspecting"}
_REPAIR_CAPABILITIES = {"repair", "revision", "replan", "correcting"}


def compute_actions(state: dict[str, Any]) -> RouterResult:
    """Compute eligible actions from current state including provider health,
    budget, failure decisions, and revision state.

    Priority order:
    1. Human approval required → wait for human
    2. Blocking failure decision → escalate_to_failure_handler or continue_unrelated_work
    3. Provider-blocked generation → continue_unrelated_work (if non-gen phase possible)
    4. Budget blocked → escalate_to_human
    5. Blocking issues → repair or escalate
    6. Pending revision → revise
    7. Not approved → present review package
    8. Approved → advance to next phase
    """
    ostate.ensure_orchestrator_state(state)

    phase = str(state.get("current_phase", "intake"))
    approved = bool(state.get("approved", False))
    human_required = bool(state.get("human_approval_required", False))
    issues: list[dict[str, Any]] = state.get("issues", [])
    result = RouterResult()

    # --- 1. Human approval required ------------------------------------------
    if human_required:
        blocking_count = sum(
            1 for issue in issues if isinstance(issue, dict) and issue.get("severity") == "blocking"
        )
        result.eligible = []
        if blocking_count == 0:
            result.eligible.append("approve_phase")
        if state.get("_stalled_phase"):
            result.eligible.append("escalate_to_human")
        else:
            result.eligible.append("request_revision")
        result.next_action = "wait_for_human"
        result.human_gate = APPROVAL_GATES.get(phase, phase)
        if blocking_count:
            result.blocked = [
                {
                    "action": "approve_phase",
                    "reason": f"{blocking_count} blocking issue(s) must be resolved first.",
                }
            ]
        return result

    # --- 2. Failure decisions ------------------------------------------------
    if ostate.has_blocking_failure(state):
        latest_failure = ostate.get_latest_failure_decision(state)
        if (
            latest_failure
            and latest_failure.get("safe_to_continue_other_work")
            and phase in _PHASE_AGNOSTIC_PHASES
        ):
            # Generation may be blocked, but planning/writing can proceed
            result.eligible = ["continue_unrelated_work", "escalate_to_human"]
            result.next_action = "continue_unrelated_work"
            result.blocked = [
                {
                    "action": "advance_to_generation",
                    "reason": f"provider failure: {latest_failure.get('human_message', '')}",
                }
            ]
            return result

        result.eligible = ["escalate_to_failure_handler", "escalate_to_human"]
        result.next_action = "escalate_to_failure_handler"
        result.blocked = [
            {
                "action": a,
                "reason": f"blocking failure: {latest_failure.get('human_message', '')}"
                if latest_failure
                else "blocking failure",
            }
            for a in ["advance_phase", "continue_unrelated_work"]
        ]
        return result

    # --- 3. Provider health check --------------------------------------------
    blocked_providers = ostate.get_blocked_providers(state)
    if blocked_providers and phase in _GENERATION_DEPENDENT_PHASES:
        result.eligible = ["continue_unrelated_work", "escalate_to_human"]
        result.next_action = "continue_unrelated_work"
        result.blocked = [
            {
                "action": "advance_to_generation",
                "reason": f"provider(s) blocked: {', '.join(blocked_providers)}",
            }
        ]
        return result

    # --- 4. Budget check -----------------------------------------------------
    if ostate.is_budget_blocked(state):
        result.eligible = ["escalate_to_human"]
        result.next_action = "escalate_to_human"
        result.blocked = [
            {
                "action": "advance_phase",
                "reason": "budget threshold exceeded",
            }
        ]
        return result

    # --- 5. Blocking issues --------------------------------------------------
    blocking = [i for i in issues if i.get("severity") == "blocking"]
    if blocking:
        result.blocked = [
            {"action": "advance_phase", "reason": f"blocking issue: {b.get('code', '')}"}
            for b in blocking
        ]
        result.eligible = ["repair", "escalate_to_human"]
        result.next_action = "handle_blockers"
        return result

    # --- 6. Pending revision -------------------------------------------------
    if ostate.has_pending_revision(state):
        result.eligible = ["revise", "escalate_to_human"]
        result.next_action = "revise"
        result.blocked = [
            {"action": "approve_phase", "reason": "pending revision must be resolved first"}
        ]
        return result

    # --- 7. Not approved → review package ------------------------------------
    if not approved and phase in APPROVAL_GATES:
        result.eligible = ["present_review_package", "approve_phase"]
        result.next_action = "present_review_package"
        result.human_gate = APPROVAL_GATES[phase]
        return result

    # --- 8. Approved → advance to next phase ---------------------------------
    idx = PHASE_ORDER.index(phase) if phase in PHASE_ORDER else -1
    if idx >= 0 and idx + 1 < len(PHASE_ORDER):
        next_phase = PHASE_ORDER[idx + 1]

        # Check if next phase is generation and providers are blocked
        if next_phase == "generation" and ostate.get_blocked_providers(state):
            result.eligible = ["continue_unrelated_work", "escalate_to_human"]
            result.next_action = "continue_unrelated_work"
            result.blocked = [
                {
                    "action": "advance_to_generation",
                    "reason": f"provider(s) blocked: {', '.join(ostate.get_blocked_providers(state))}",
                }
            ]
            return result

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

    ``task_type`` is one of: ``"create"``, ``"review"``, ``"repair"``,
    ``"failure_handler"``.

    When ``preferred_capability`` is provided, it overrides task-type-based
    selection.

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
        if task_type == "failure_handler":
            candidates = registry.lookup_by_role(AgentRole.OPERATOR)
            if candidates:
                agent = candidates[0]
                return AgentRouteResult(
                    agent_id=agent.agent_id,
                    routing_reason=f"failure-handling path for phase '{phase}'",
                    kb_context_ref=_build_kb_context_ref(agent),
                )
            return AgentRouteResult(
                agent_id="orchestrator-agent",
                routing_reason="failure handler requested but no operator agents available",
                fallback=True,
            )

        if task_type == "repair" or preferred_capability in _REPAIR_CAPABILITIES:
            candidates = registry.lookup_by_role(AgentRole.OPERATOR)
            if candidates:
                agent = candidates[0]
                return AgentRouteResult(
                    agent_id=agent.agent_id,
                    routing_reason=f"repair path for phase '{phase}' after validation failure",
                    kb_context_ref=_build_kb_context_ref(agent),
                )
            # Fall through to creator if no repair agents (explicit)
            return AgentRouteResult(
                agent_id=default_agent,
                routing_reason=(
                    f"repair requested but no repair agents available "
                    f"for phase '{phase}' — using creator"
                ),
                fallback=True,
            )

        if task_type == "review" or preferred_capability in _REVIEW_CAPABILITIES:
            # Apply profile-driven review strategy
            review_strategy = _resolve_review_strategy(state, phase)
            candidates = registry.lookup_by_role(AgentRole.REVIEWER)
            if not candidates:
                candidates = registry.lookup_by_role(AgentRole.VALIDATOR)
            if candidates:
                agent = candidates[0]
                return AgentRouteResult(
                    agent_id=agent.agent_id,
                    routing_reason=f"review path for phase '{phase}'",
                    review_strategy=review_strategy,
                    kb_context_ref=_build_kb_context_ref(agent),
                )
            return AgentRouteResult(
                agent_id=default_agent,
                routing_reason=(
                    f"review requested but no validator agents for phase '{phase}' — using creator"
                ),
                fallback=True,
            )

        if preferred_capability:
            candidates = registry.lookup_by_capability(preferred_capability)
            if candidates:
                agent = candidates[0]
                return AgentRouteResult(
                    agent_id=agent.agent_id,
                    routing_reason=(
                        f"selected by capability '{preferred_capability}' for phase '{phase}'"
                    ),
                    kb_context_ref=_build_kb_context_ref(agent),
                )

    # Default: create path
    return AgentRouteResult(
        agent_id=default_agent,
        routing_reason=f"create path for phase '{phase}' — using default agent",
    )


def _build_kb_context_ref(agent: Any) -> str:
    """Build a KB context ref string from the agent's allowed KB domains."""
    allowed = getattr(agent, "allowed_kb_domains", [])
    if not allowed:
        return ""
    return f"kbctx:{agent.agent_id}:{'+'.join(sorted(allowed))}"


def _resolve_review_strategy(state: dict[str, Any], phase: str) -> str:
    """Resolve the review strategy from the active profile's resolved config."""
    resolved_config = state.get("resolved_config", {})
    if isinstance(resolved_config, dict):
        strategy = resolved_config.get("resolved_review_strategy", "")
        if strategy:
            return str(strategy)
    return "single"
