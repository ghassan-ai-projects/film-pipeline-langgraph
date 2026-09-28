"""Audit log and decision-explanation tools."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec

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
    project_id = str(args.get("project_id", "") or "") or (ctx.project_id or "")
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


class GetAuditLogArgs(ToolArgs):
    """Arguments for `get_audit_log`."""

    project_id: str = Field(default="", description="Project id; empty uses the active project.")
    limit: int = Field(default=100, description="Maximum events to return.")


class ExplainLastDecisionArgs(ToolArgs):
    """Arguments for `explain_last_decision` (none)."""


class ExplainAgentRoutingArgs(ToolArgs):
    """Arguments for `explain_agent_routing` (none)."""


class ExplainKbContextArgs(ToolArgs):
    """Arguments for `explain_kb_context` (none)."""


AUDIT_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="get_audit_log",
        group=ToolGroup.AUDIT,
        description="Read the audit log: who did what, when, with details.",
        args=GetAuditLogArgs,
        handler=get_audit_log,
    ),
    ToolSpec(
        name="explain_last_decision",
        group=ToolGroup.AUDIT,
        description="Explain the most recent recorded decision and its details.",
        args=ExplainLastDecisionArgs,
        handler=explain_last_decision,
    ),
    ToolSpec(
        name="explain_agent_routing",
        group=ToolGroup.AUDIT,
        description="Explain the session's agent routing decisions and why each was taken.",
        args=ExplainAgentRoutingArgs,
        handler=explain_agent_routing,
    ),
    ToolSpec(
        name="explain_kb_context",
        group=ToolGroup.AUDIT,
        description="Explain how the orchestrator selects knowledge-base context per phase.",
        args=ExplainKbContextArgs,
        handler=explain_kb_context,
    ),
)
