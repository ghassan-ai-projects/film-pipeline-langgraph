"""Phase / state / orchestrator-summary / next-actions / blockers tools."""

from __future__ import annotations

from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec
from film_pipeline.orchestration import orchestrator_state as ostate
from film_pipeline.orchestration.router import (
    compute_actions,
    get_blockers_for_state,
    public_blocked_actions,
)

from .helpers import (
    _ok,
)


async def get_current_phase(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    _ = args
    state = ctx.project_state()
    return _ok(current_phase=state.get("current_phase", ""))


async def get_film_state(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    _ = args
    state = ctx.project_state()
    # Return a sanitized copy (no internal keys)
    safe = {
        k: v
        for k, v in state.items()
        if not k.startswith("_") and k not in ("approved", "human_approval_required")
    }
    return _ok(state=safe)


async def get_orchestrator_summary(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    _ = args
    state = ctx.project_state()

    routing_state = dict(state)
    ostate.ensure_orchestrator_state(routing_state)
    router_result = compute_actions(routing_state)
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
        blocked_actions=public_blocked_actions(router_result),
        candidate_refs=ostate.get_candidate_refs(state),
        approved_refs=ostate.get_approved_refs(state),
        pending_revisions=ostate.get_pending_revisions(state),
        active_review_cycle=review_cycle,
        provider_blocked=ostate.get_blocked_providers(state),
        has_blocking_failures=ostate.has_blocking_failure(state),
    )


async def get_next_actions(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    _ = args
    state = ctx.project_state()

    actions = compute_actions(dict(state))
    return _ok(
        next_action=actions.next_action,
        eligible=actions.eligible,
        blocked=public_blocked_actions(actions),
    )


async def get_blockers(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Report what currently blocks the project, derived from live state.

    Mirrors ``get_next_actions``: the router computes blocked transitions from
    real project state, and blocking issues join the same list so operators
    see one truthful picture. Response shape is stable:
    ``{blockers: [{action, reason}], has_blockers: bool}``.
    """
    _ = args
    state = ctx.project_state()

    blockers = get_blockers_for_state(state)
    return _ok(blockers=blockers, has_blockers=len(blockers) > 0)


# ── Tool declarations ────────────────────────────────────────────────────────
# Declared next to the handlers they describe (doc 04 slice 1). None of these
# take arguments: they all report on the project the context resolved.


class NoArgs(ToolArgs):
    """Arguments for the state read tools (none)."""


STATE_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="get_current_phase",
        group=ToolGroup.STATE,
        description="Report the phase the active project is currently in.",
        args=NoArgs,
        handler=get_current_phase,
        active_project=True,
    ),
    ToolSpec(
        name="get_film_state",
        group=ToolGroup.STATE,
        description="Return the active project's state with internal keys stripped.",
        args=NoArgs,
        handler=get_film_state,
        active_project=True,
    ),
    ToolSpec(
        name="get_orchestrator_summary",
        group=ToolGroup.STATE,
        description="Summarise what the orchestrator is tracking for the active project.",
        args=NoArgs,
        handler=get_orchestrator_summary,
        active_project=True,
    ),
    ToolSpec(
        name="get_next_actions",
        group=ToolGroup.STATE,
        description="List the actions the active project can take next.",
        args=NoArgs,
        handler=get_next_actions,
        active_project=True,
    ),
    ToolSpec(
        name="get_blockers",
        group=ToolGroup.STATE,
        description="List what is blocking the active project from advancing.",
        args=NoArgs,
        handler=get_blockers,
        active_project=True,
    ),
)
