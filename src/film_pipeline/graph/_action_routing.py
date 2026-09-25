"""Action routing — rule-priority computation of eligible orchestrator actions.

Each ``_*_result`` helper implements exactly one numbered rule of the
priority order documented on ``compute_actions()``; the first rule that
matches decides the outcome. Rules 6 and 8 annotate a shared
``RouterResult`` in place instead of constructing one — see the note on
``_validation_status_result`` before inserting rules between 6 and 7.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from film_pipeline.filmspec import (
    GENERATION_DEPENDENT_PHASES as _GENERATION_DEPENDENT_PHASES,
)
from film_pipeline.filmspec import PHASE_AGNOSTIC_PHASES as _PHASE_AGNOSTIC_PHASES
from film_pipeline.filmspec import PHASE_GATES as APPROVAL_GATES
from film_pipeline.filmspec import next_phase
from film_pipeline.graph import orchestrator_state as ostate
from film_pipeline.schemas.base import ValidationStatus


@dataclass
class RouterResult:
    eligible: list[str] = field(default_factory=list)
    blocked: list[dict[str, str]] = field(default_factory=list)
    next_action: str = ""
    human_gate: str = ""


# Severity ordering for the four-status validation contract
_STATUS_SEVERITY = {
    ValidationStatus.PASS: 0,
    ValidationStatus.PASS_WITH_NOTES: 1,
    ValidationStatus.NEEDS_REVISION: 2,
    ValidationStatus.BLOCKED: 3,
    ValidationStatus.ERROR: 4,
}


def _status_from_value(value: str) -> ValidationStatus:
    """Parse a validation status string, defaulting to ERROR."""
    try:
        return ValidationStatus(value)
    except ValueError:
        return ValidationStatus.ERROR


def _is_blocking_issue(issue: Any) -> bool:
    """True when an issue's severity blocks phase approval."""
    return isinstance(issue, dict) and issue.get("severity") == "blocking"


def _blocking_issue_count(issues: list[dict[str, Any]]) -> int:
    """Number of issues whose severity blocks approval."""
    return sum(1 for issue in issues if _is_blocking_issue(issue))


def _advance_to_generation_blocker(blocked_providers: list[str]) -> dict[str, str]:
    """Blocker entry explaining why generation cannot start."""
    return {
        "action": "advance_to_generation",
        "reason": f"provider(s) blocked: {', '.join(blocked_providers)}",
    }


def _consensus_status(state: dict[str, Any]) -> ValidationStatus | None:
    """Validation status from an explicit consensus report, when present."""
    consensus = state.get("consensus_report")
    if isinstance(consensus, dict):
        raw = consensus.get("consensus_status") or consensus.get("status")
        if raw:
            return _status_from_value(str(raw))
    return None


def _most_severe_report(reports: list[dict[str, Any]]) -> ValidationStatus | None:
    """Highest-severity status across validation reports."""
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


def _latest_validation_status(state: dict[str, Any]) -> ValidationStatus | None:
    """Most severe validation signal: explicit consensus wins over reports."""
    consensus = _consensus_status(state)
    if consensus is not None:
        return consensus
    reports: list[dict[str, Any]] = state.get("_validation_reports", [])
    return _most_severe_report(reports)


def _human_approval_result(
    state: dict[str, Any],
    phase: str,
    issues: list[dict[str, Any]],
) -> RouterResult | None:
    """Rule 1: human approval required → wait for human."""
    if not bool(state.get("human_approval_required", False)):
        return None
    blocking_count = _blocking_issue_count(issues)
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
                "origin": "state_issue",
            }
        ]
    return result


def _safe_to_continue_result(
    latest_failure: dict[str, Any] | None,
    phase: str,
) -> RouterResult | None:
    """Failure allows unrelated work even though generation cannot proceed."""
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


def _blocking_failure_blockers(
    latest_failure: dict[str, Any] | None,
) -> list[dict[str, str]]:
    """Blocker entries raised while a blocking failure stands."""
    return [
        {
            "action": action,
            "reason": f"blocking failure: {latest_failure.get('human_message', '')}"
            if latest_failure
            else "blocking failure",
        }
        for action in ["advance_phase", "continue_unrelated_work"]
    ]


def _blocking_failure_result(state: dict[str, Any], phase: str) -> RouterResult | None:
    """Rule 2: blocking failure decision → escalate or continue unrelated work."""
    if not ostate.has_blocking_failure(state):
        return None
    latest_failure = ostate.get_latest_failure_decision(state)
    continued = _safe_to_continue_result(latest_failure, phase)
    if continued is not None:
        return continued
    return RouterResult(
        eligible=["escalate_to_failure_handler", "escalate_to_human"],
        next_action="escalate_to_failure_handler",
        blocked=_blocking_failure_blockers(latest_failure),
    )


def _blocked_providers_result(state: dict[str, Any], phase: str) -> RouterResult | None:
    """Rule 3: provider-blocked generation → continue unrelated work."""
    blocked_providers = ostate.get_blocked_providers(state)
    if not (blocked_providers and phase in _GENERATION_DEPENDENT_PHASES):
        return None
    return RouterResult(
        eligible=["continue_unrelated_work", "escalate_to_human"],
        next_action="continue_unrelated_work",
        blocked=[_advance_to_generation_blocker(blocked_providers)],
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
    blocking = [issue for issue in issues if _is_blocking_issue(issue)]
    if not blocking:
        return None
    return RouterResult(
        eligible=["repair", "escalate_to_human"],
        next_action="handle_blockers",
        blocked=[
            {
                "action": "advance_phase",
                "reason": f"blocking issue: {b.get('code', '')}",
                "origin": "state_issue",
            }
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
            {
                "action": "approve_phase",
                "reason": "validation passed with notes — review warnings",
            }
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
    """Advance approved phases to their sequence successor, or wrap."""
    successor = next_phase(phase)
    if successor is None:
        result.eligible = ["wrap"]
        result.next_action = "wrap"
        return result

    blocked_providers = ostate.get_blocked_providers(state)

    # Generation cannot start while its providers are blocked.
    if successor == "generation" and blocked_providers:
        result.eligible = ["continue_unrelated_work", "escalate_to_human"]
        result.next_action = "continue_unrelated_work"
        result.blocked = [_advance_to_generation_blocker(blocked_providers)]
        return result

    result.eligible = [f"advance_to_{successor}"]
    result.next_action = f"advance_to_{successor}"
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
