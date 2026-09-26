"""Dynamic action router — computes eligible actions and selects agents.

This module is the stable import surface; the implementation lives in two
cohesive siblings:

1. Action routing (:mod:`film_pipeline.orchestration._action_routing`): what action
   to take next, taking into account provider health, budget state, failure
   decisions, revision requests, and profile policy.
2. Agent routing (:mod:`film_pipeline.orchestration._agent_routing`): which agent
   performs the action, with KB context selection.

The orchestrator state domain (``orchestrator_state.py``) is the source
of truth for all routing-relevant state beyond the base graph fields.
"""

from __future__ import annotations

from typing import Any

from film_pipeline.filmspec import PHASE_GATES as APPROVAL_GATES
from film_pipeline.filmspec import is_blocking_issue
from film_pipeline.governance.action_routing import RouterResult
from film_pipeline.governance.action_routing import compute_actions as _compute_actions
from film_pipeline.orchestration._agent_routing import (
    AgentRouteResult,
    route_agent,
)
from film_pipeline.orchestration._gate_facts import GATE_FACTS as GATE_FACTS
from film_pipeline.orchestration.phase_sequence import PHASE_ORDER


def compute_actions(state: dict[str, Any]) -> RouterResult:
    """Compute eligible actions using the concrete orchestrator facts.

    `governance` owns the gate law but sits below `orchestration`, so the
    orchestrator facts it reads are bound here.
    """
    return _compute_actions(state, GATE_FACTS)


__all__ = [
    "APPROVAL_GATES",
    "PHASE_ORDER",
    "AgentRouteResult",
    "RouterResult",
    "compute_actions",
    "get_blockers_for_state",
    "public_blocked_actions",
    "route_agent",
]


def get_blockers_for_state(
    state: dict[str, Any], *, routing: RouterResult | None = None
) -> list[dict[str, str]]:
    """Return one canonical, deduplicated blocker list for live project state.

    ``compute_actions`` owns routing blockers. Its state-issue entries carry an
    internal origin marker; this projection replaces them with operator-facing
    code and message entries. All callers use this projection so dashboard,
    project-summary, and MCP views cannot disagree about ``has_blockers``.
    """
    # Routing initialization fills missing orchestrator keys. Use a shallow
    # state copy so a read-only dashboard query does not mutate live state.
    result = routing if routing is not None else compute_actions(dict(state))
    blockers = [
        dict(blocker) for blocker in result.blocked if blocker.get("origin") != "state_issue"
    ]
    issues = state.get("issues", [])
    blocking_issues = (
        [issue for issue in issues if is_blocking_issue(issue)] if isinstance(issues, list) else []
    )

    # Replace the router's generic issue entries with useful issue-specific
    # entries; retain independent budget, provider, failure, and gate blockers.
    blockers.extend(
        {
            "action": "resolve_blocking_issue",
            "reason": f"{issue.get('code', 'blocking_issue')!s}: {issue.get('message', '')!s}",
        }
        for issue in blocking_issues
    )

    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for blocker in blockers:
        key = (str(blocker.get("action", "")), str(blocker.get("reason", "")))
        if key not in seen:
            seen.add(key)
            unique.append({"action": key[0], "reason": key[1]})
    return unique


def public_blocked_actions(result: RouterResult) -> list[dict[str, str]]:
    """Project router blockers to the public action/reason response shape.

    Routing may attach internal provenance while evaluating state-specific
    rules. That provenance is useful inside the graph but is not part of the
    operator or MCP contract.
    """
    return [
        {
            "action": str(blocker.get("action", "")),
            "reason": str(blocker.get("reason", "")),
        }
        for blocker in result.blocked
    ]
