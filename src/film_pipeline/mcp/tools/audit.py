"""Audit log and decision-explanation tools."""

from __future__ import annotations

from typing import Any

from film_pipeline.mcp.tools.context import ToolContext

from .helpers import _ok


def _routing_summary(routing_decisions: list[dict[str, Any]]) -> str:
    """Render routing decisions as ``agent [FALLBACK]: reason`` lines."""
    summary_lines: list[str] = []
    for rd in routing_decisions:
        agent = rd.get("agent_id", "unknown")
        reason = rd.get("routing_reason", "")
        was_fallback = rd.get("fallback", False)
        label = " [FALLBACK]" if was_fallback else ""
        summary_lines.append(f"{agent}{label}: {reason}")
    return "\n".join(summary_lines)


async def get_audit_log(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    project_id = str(args.get("project_id", "") or "")
    limit_raw = args.get("limit", 100)
    limit = int(limit_raw) if isinstance(limit_raw, int) else int(str(limit_raw))
    events = ctx.runtime.get_audit_log(project_id if project_id else None, limit=limit)
    return _ok(events=events, total=len(events))


async def explain_last_decision(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    _ = args
    events = ctx.runtime.audit_events
    if not events:
        return _ok(message="No decisions recorded yet.")
    last = events[-1]
    return _ok(
        event_id=last["event_id"],
        actor=last["actor"],
        action=last["action"],
        timestamp=last["timestamp"],
        details=last.get("details", {}),
    )


async def explain_agent_routing(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    _ = args
    # The context's project is what dispatch resolved; this tool also reads the
    # runtime's *active* project, because routing history is session-scoped and
    # the tool declares `requires_active_project=False`.
    state = (
        ctx.runtime.get_project(ctx.project_id)
        if ctx.project_id is not None
        else ctx.runtime.get_active()
    )

    if state is None:
        return _ok(decisions=[], message="No active project. Routing data is session-scoped.")

    routing_decisions = state.get("_routing_decisions", [])

    if not routing_decisions:
        return _ok(
            decisions=[],
            message="No routing decisions recorded yet. Run a phase to populate routing history.",
        )

    return _ok(
        decisions=routing_decisions,
        summary=_routing_summary(routing_decisions),
        message=f"{len(routing_decisions)} routing decision(s) recorded.",
    )


async def explain_kb_context(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    _ = ctx, args
    return _ok(
        message="KB context: the orchestrator selects KB slices by phase and agent. "
        "Canonical rules take priority over playbooks and case studies.",
    )
