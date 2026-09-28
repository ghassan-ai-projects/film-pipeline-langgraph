"""Unit tests for film_pipeline.mcp.tools.audit.

These call handlers through the `call_tool` fixture, which builds the
`ToolContext` dispatch would build. They used to call `handler(args)` directly
and reach the runtime through the process-global singleton — the shape doc 01
removes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from film_pipeline.mcp.tools import (
    create_film_project,
    explain_agent_routing,
    explain_kb_context,
    explain_last_decision,
    get_audit_log,
    set_active_project,
)
from film_pipeline.studio.runtime import get_runtime as gr

CallTool = Callable[..., Any]


def test_get_audit_log_returns_events(call_tool: CallTool) -> None:
    call_tool(create_film_project, {"project_id": "proj-audit-1"})
    result = call_tool(get_audit_log, {"project_id": "proj-audit-1"})
    assert result["ok"] is True
    assert cast(int, result["total"]) >= 1


def test_get_audit_log_with_limit(call_tool: CallTool) -> None:
    call_tool(create_film_project, {"project_id": "proj-audit-2"})
    result = call_tool(get_audit_log, {"project_id": "proj-audit-2", "limit": 1})
    assert result["ok"] is True
    assert len(cast(list[object], result["events"])) <= 1


def test_explain_last_decision_with_events(call_tool: CallTool) -> None:
    call_tool(create_film_project, {"project_id": "proj-audit-3"})
    result = call_tool(explain_last_decision, {})
    assert result["ok"] is True
    assert "action" in result


def test_explain_last_decision_empty(call_tool: CallTool) -> None:
    gr().audit_events.clear()
    result = call_tool(explain_last_decision, {})
    assert result["ok"] is True
    assert result["message"] == "No decisions recorded yet."


def test_explain_agent_routing_no_decisions_yet(call_tool: CallTool) -> None:
    call_tool(create_film_project, {"project_id": "proj-audit-4"})
    call_tool(set_active_project, {"project_ref": "proj-audit-4"})
    result = call_tool(explain_agent_routing, {}, project_id="proj-audit-4")
    assert result["ok"] is True
    assert result["decisions"] == []


def test_explain_kb_context(call_tool: CallTool) -> None:
    result = call_tool(explain_kb_context, {})
    assert result["ok"] is True
    assert "message" in result
