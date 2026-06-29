"""Audit log and decision-explanation tools."""

from __future__ import annotations

import film_pipeline.mcp.tools as tools_pkg

from .helpers import _active_project_id, _ok


async def get_audit_log(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    project_id = str(args.get("project_id", "") or "")
    limit_raw = args.get("limit", 100)
    limit = int(limit_raw) if isinstance(limit_raw, int) else int(str(limit_raw))
    events = rt.get_audit_log(project_id if project_id else None, limit=limit)
    return _ok(events=events, total=len(events))


async def explain_last_decision(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    events = rt.audit_events
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


async def explain_agent_routing(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    state = rt.get_project(project_id) if project_id is not None else rt.get_active()

    if state is None:
        return _ok(decisions=[], message="No active project. Routing data is session-scoped.")

    routing_decisions = state.get("_routing_decisions", [])

    if not routing_decisions:
        return _ok(
            decisions=[],
            message="No routing decisions recorded yet. Run a phase to populate routing history.",
        )

    summary_lines: list[str] = []
    for rd in routing_decisions:
        agent = rd.get("agent_id", "unknown")
        reason = rd.get("routing_reason", "")
        was_fallback = rd.get("fallback", False)
        label = " [FALLBACK]" if was_fallback else ""
        summary_lines.append(f"{agent}{label}: {reason}")

    return _ok(
        decisions=routing_decisions,
        summary="\n".join(summary_lines),
        message=f"{len(routing_decisions)} routing decision(s) recorded.",
    )


async def explain_kb_context(args: dict[str, object]) -> dict[str, object]:
    return _ok(
        message="KB context: the orchestrator selects KB slices by phase and agent. "
        "Canonical rules take priority over playbooks and case studies.",
    )
