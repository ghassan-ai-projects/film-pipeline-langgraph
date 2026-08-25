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

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from film_pipeline.graph import orchestrator_state as ostate
from film_pipeline.schemas._base import AgentRole, ValidationStatus

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

# Severity ordering for the four-status validation contract
_STATUS_SEVERITY = {
    ValidationStatus.PASS: 0,
    ValidationStatus.PASS_WITH_NOTES: 1,
    ValidationStatus.NEEDS_REVISION: 2,
    ValidationStatus.BLOCKED: 3,
    ValidationStatus.ERROR: 4,
}

# Default agent per phase (for backward compatibility)
_PHASE_DEFAULT_AGENTS: Mapping[str, str] = MappingProxyType(
    {
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
)


def _status_from_value(value: str) -> ValidationStatus:
    """Parse a validation status string, defaulting to ERROR."""
    try:
        return ValidationStatus(value)
    except ValueError:
        return ValidationStatus.ERROR


def _latest_validation_status(state: dict[str, Any]) -> ValidationStatus | None:
    """Return the most severe validation/consensus status stored in state."""
    # Prefer an explicit consensus report when available.
    consensus = state.get("consensus_report")
    if isinstance(consensus, dict):
        raw = consensus.get("consensus_status") or consensus.get("status")
        if raw:
            return _status_from_value(str(raw))

    reports: list[dict[str, Any]] = state.get("_validation_reports", [])
    if not reports:
        return None

    worst: ValidationStatus | None = None
    worst_rank = -1
    for report in reports:
        raw = report.get("status")
        if not raw:
            continue
        status = _status_from_value(str(raw))
        rank = _STATUS_SEVERITY.get(status, -1)
        if rank > worst_rank:
            worst_rank = rank
            worst = status
    return worst


def _human_approval_result(
    state: dict[str, Any],
    phase: str,
    issues: list[dict[str, Any]],
) -> RouterResult | None:
    """Rule 1: human approval required → wait for human."""
    if not bool(state.get("human_approval_required", False)):
        return None
    blocking_count = sum(
        1 for issue in issues if isinstance(issue, dict) and issue.get("severity") == "blocking"
    )
    result = RouterResult()
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


def _failure_continue_result(
    latest_failure: dict[str, Any] | None,
    phase: str,
) -> RouterResult | None:
    """Generation may be blocked, but planning/writing can proceed."""
    if not (
        latest_failure
        and latest_failure.get("safe_to_continue_other_work")
        and phase in _PHASE_AGNOSTIC_PHASES
    ):
        return None
    return RouterResult(
        eligible=["continue_unrelated_work", "escalate_to_human"],
        next_action="continue_unrelated_work",
        blocked=[
            {
                "action": "advance_to_generation",
                "reason": f"provider failure: {latest_failure.get('human_message', '')}",
            }
        ],
    )


def _blocking_failure_result(state: dict[str, Any], phase: str) -> RouterResult | None:
    """Rule 2: blocking failure decision → escalate or continue unrelated work."""
    if not ostate.has_blocking_failure(state):
        return None
    latest_failure = ostate.get_latest_failure_decision(state)
    continued = _failure_continue_result(latest_failure, phase)
    if continued is not None:
        return continued
    return RouterResult(
        eligible=["escalate_to_failure_handler", "escalate_to_human"],
        next_action="escalate_to_failure_handler",
        blocked=[
            {
                "action": a,
                "reason": f"blocking failure: {latest_failure.get('human_message', '')}"
                if latest_failure
                else "blocking failure",
            }
            for a in ["advance_phase", "continue_unrelated_work"]
        ],
    )


def _blocked_providers_result(state: dict[str, Any], phase: str) -> RouterResult | None:
    """Rule 3: provider-blocked generation → continue unrelated work."""
    blocked_providers = ostate.get_blocked_providers(state)
    if not (blocked_providers and phase in _GENERATION_DEPENDENT_PHASES):
        return None
    return RouterResult(
        eligible=["continue_unrelated_work", "escalate_to_human"],
        next_action="continue_unrelated_work",
        blocked=[
            {
                "action": "advance_to_generation",
                "reason": f"provider(s) blocked: {', '.join(blocked_providers)}",
            }
        ],
    )


def _budget_blocked_result(state: dict[str, Any]) -> RouterResult | None:
    """Rule 4: budget threshold exceeded → escalate to human."""
    if not ostate.is_budget_blocked(state):
        return None
    return RouterResult(
        eligible=["escalate_to_human"],
        next_action="escalate_to_human",
        blocked=[
            {
                "action": "advance_phase",
                "reason": "budget threshold exceeded",
            }
        ],
    )


def _blocking_issues_result(issues: list[dict[str, Any]]) -> RouterResult | None:
    """Rule 5: blocking issues → repair or escalate."""
    blocking = [i for i in issues if i.get("severity") == "blocking"]
    if not blocking:
        return None
    return RouterResult(
        eligible=["repair", "escalate_to_human"],
        next_action="handle_blockers",
        blocked=[
            {"action": "advance_phase", "reason": f"blocking issue: {b.get('code', '')}"}
            for b in blocking
        ],
    )


def _validation_status_result(state: dict[str, Any], result: RouterResult) -> RouterResult | None:
    """Rule 6: validation consensus drives repair/revision routing.

    BLOCKED/NEEDS_REVISION annotate and return the shared ``result``;
    PASS_WITH_NOTES only annotates it and returns ``None`` so later rules
    keep mutating the same object. Preserve this mutate-vs-replace split
    when inserting rules between 6 and 7.
    """
    val_status = _latest_validation_status(state)
    if val_status == ValidationStatus.BLOCKED:
        result.blocked = [{"action": "advance_phase", "reason": "validation consensus is blocked"}]
        result.eligible = ["repair", "escalate_to_human"]
        result.next_action = "handle_blockers"
        return result
    if val_status == ValidationStatus.NEEDS_REVISION:
        result.eligible = ["revise", "escalate_to_human"]
        result.next_action = "revise"
        result.blocked = [
            {"action": "approve_phase", "reason": "validation consensus requires revision"}
        ]
        return result
    if val_status == ValidationStatus.PASS_WITH_NOTES:
        result.blocked.append(
            {"action": "approve_phase", "reason": "validation passed with notes — review warnings"}
        )
    return None


def _pending_revision_result(state: dict[str, Any]) -> RouterResult | None:
    """Rule 7: pending revision → revise before anything else."""
    if not ostate.has_pending_revision(state):
        return None
    return RouterResult(
        eligible=["revise", "escalate_to_human"],
        next_action="revise",
        blocked=[{"action": "approve_phase", "reason": "pending revision must be resolved first"}],
    )


def _review_package_result(result: RouterResult, approved: bool, phase: str) -> RouterResult | None:
    """Rule 8: unapproved at an approval gate → present review package."""
    if approved or phase not in APPROVAL_GATES:
        return None
    result.eligible = ["present_review_package", "approve_phase"]
    result.next_action = "present_review_package"
    result.human_gate = APPROVAL_GATES[phase]
    return result


def _advance_result(state: dict[str, Any], phase: str, result: RouterResult) -> RouterResult:
    """Approved phases advance to the next phase in PHASE_ORDER, or wrap."""
    idx = PHASE_ORDER.index(phase) if phase in PHASE_ORDER else -1
    if idx < 0 or idx + 1 >= len(PHASE_ORDER):
        result.eligible = ["wrap"]
        result.next_action = "wrap"
        return result

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
    return result


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
    issues: list[dict[str, Any]] = state.get("issues", [])
    result = RouterResult()

    routed = _human_approval_result(state, phase, issues)
    if routed is not None:
        return routed
    routed = _blocking_failure_result(state, phase)
    if routed is not None:
        return routed
    routed = _blocked_providers_result(state, phase)
    if routed is not None:
        return routed
    routed = _budget_blocked_result(state)
    if routed is not None:
        return routed
    routed = _blocking_issues_result(issues)
    if routed is not None:
        return routed
    routed = _validation_status_result(state, result)
    if routed is not None:
        return routed
    routed = _pending_revision_result(state)
    if routed is not None:
        return routed
    routed = _review_package_result(result, approved, phase)
    if routed is not None:
        return routed

    return _advance_result(state, phase, result)


def _default_agent_for(phase: str) -> str:
    """Backward-compatible default agent for a phase."""
    return _PHASE_DEFAULT_AGENTS.get(phase, "orchestrator-agent")


def _normalized_task_type(task_type: str, preferred_capability: str | None) -> str:
    """Map preferred_capability to task_type when registry is absent."""
    if preferred_capability in _REPAIR_CAPABILITIES:
        return "repair"
    if preferred_capability in _REVIEW_CAPABILITIES:
        return "review"
    return task_type


def _first_registered(
    candidates: list[Any],
    routing_reason: str,
    review_strategy: str = "single",
) -> AgentRouteResult:
    """Route to the first registered candidate with its KB context ref."""
    agent = candidates[0]
    return AgentRouteResult(
        agent_id=agent.agent_id,
        routing_reason=routing_reason,
        review_strategy=review_strategy,
        kb_context_ref=_build_kb_context_ref(agent),
    )


def _failure_handler_route(registry: Any, phase: str) -> AgentRouteResult:
    """Failure-handling path: first operator agent, else orchestrator fallback."""
    candidates = registry.lookup_by_role(AgentRole.OPERATOR)
    if candidates:
        return _first_registered(candidates, f"failure-handling path for phase '{phase}'")
    return AgentRouteResult(
        agent_id="orchestrator-agent",
        routing_reason="failure handler requested but no operator agents available",
        fallback=True,
    )


def _repair_route(registry: Any, phase: str) -> AgentRouteResult:
    """Repair path: first operator agent, else explicit fall-through to creator."""
    candidates = registry.lookup_by_role(AgentRole.OPERATOR)
    if candidates:
        return _first_registered(
            candidates, f"repair path for phase '{phase}' after validation failure"
        )
    # Fall through to creator if no repair agents (explicit)
    return AgentRouteResult(
        agent_id=_default_agent_for(phase),
        routing_reason=(
            f"repair requested but no repair agents available for phase '{phase}' — using creator"
        ),
        fallback=True,
    )


def _review_route(state: dict[str, Any], registry: Any, phase: str) -> AgentRouteResult:
    """Review path: reviewer/validator agents with profile-driven strategy."""
    # Apply profile-driven review strategy
    review_strategy = _resolve_review_strategy(state, phase)
    candidates = registry.lookup_by_role(AgentRole.REVIEWER)
    if not candidates:
        candidates = registry.lookup_by_role(AgentRole.VALIDATOR)
    if candidates:
        return _first_registered(
            candidates, f"review path for phase '{phase}'", review_strategy=review_strategy
        )
    return AgentRouteResult(
        agent_id=_default_agent_for(phase),
        routing_reason=(
            f"review requested but no validator agents for phase '{phase}' — using creator"
        ),
        fallback=True,
    )


def _capability_route(registry: Any, phase: str, capability: str) -> AgentRouteResult | None:
    """Select by an explicit capability; None falls through to the create path."""
    candidates = registry.lookup_by_capability(capability)
    if not candidates:
        return None
    return _first_registered(
        candidates, f"selected by capability '{capability}' for phase '{phase}'"
    )


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
    task_type = _normalized_task_type(task_type, preferred_capability)

    if registry is not None:
        if task_type == "failure_handler":
            return _failure_handler_route(registry, phase)
        if task_type == "repair" or preferred_capability in _REPAIR_CAPABILITIES:
            return _repair_route(registry, phase)
        if task_type == "review" or preferred_capability in _REVIEW_CAPABILITIES:
            return _review_route(state, registry, phase)
        if preferred_capability:
            routed = _capability_route(registry, phase, preferred_capability)
            if routed is not None:
                return routed

    # Default: create path
    return AgentRouteResult(
        agent_id=_default_agent_for(phase),
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
