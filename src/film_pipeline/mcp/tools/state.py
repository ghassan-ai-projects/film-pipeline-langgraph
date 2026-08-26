"""Phase / state / orchestrator-summary / next-actions / blockers tools."""

from __future__ import annotations

import film_pipeline.mcp.tools as tools_pkg

from .helpers import _active_project_state, _error, _ok


async def get_current_phase(args: dict[str, object]) -> dict[str, object]:
    state = _active_project_state(args)
    if state is None:
        return _error("No active project.")
    return _ok(current_phase=state.get("current_phase", ""))


async def get_film_state(args: dict[str, object]) -> dict[str, object]:
    state = _active_project_state(args)
    if state is None:
        return _error("No active project.")
    # Return a sanitized copy (no internal keys)
    safe = {
        k: v
        for k, v in state.items()
        if not k.startswith("_") and k not in ("approved", "human_approval_required")
    }
    return _ok(state=safe)


async def get_orchestrator_summary(args: dict[str, object]) -> dict[str, object]:
    state = _active_project_state(args)
    if state is None:
        return _error("No active project.")

    from film_pipeline.graph import orchestrator_state as ostate
    from film_pipeline.graph.router import compute_actions

    ostate.ensure_orchestrator_state(state)
    router_result = compute_actions(state)
    latest_decision = ostate.get_latest_routing_decision(state)
    review_cycle = ostate.get_active_review_cycle(state, str(state.get("current_phase", "")))

    return _ok(
        project_id=state["project_id"],
        current_phase=state.get("current_phase"),
        approved=state.get("approved"),
        human_approval_required=state.get("human_approval_required"),
        issues=state.get("issues", []),
        next_action=router_result.next_action,
        route_reason=latest_decision.get("reason", "") if latest_decision else "",
        eligible_actions=router_result.eligible,
        blocked_actions=router_result.blocked,
        candidate_refs=ostate.get_candidate_refs(state),
        approved_refs=ostate.get_approved_refs(state),
        pending_revisions=ostate.get_pending_revisions(state),
        active_review_cycle=review_cycle,
        provider_blocked=ostate.get_blocked_providers(state),
        budget_snapshot=ostate.get_budget_snapshot(state),
        has_blocking_failures=ostate.has_blocking_failure(state),
    )


async def get_next_actions(args: dict[str, object]) -> dict[str, object]:
    state = _active_project_state(args)
    if state is None:
        return _error("No active project.")
    from film_pipeline.graph.router import compute_actions

    actions = compute_actions(state)
    return _ok(
        next_action=actions.next_action,
        eligible=actions.eligible,
        blocked=actions.blocked,
    )


async def get_blockers(args: dict[str, object]) -> dict[str, object]:
    state = _active_project_state(args)
    if state is None:
        return _error("No active project.")
    blockers = tools_pkg.get_runtime().get_blockers(str(state["project_id"]))
    return _ok(blockers=blockers, has_blockers=len(blockers) > 0)
