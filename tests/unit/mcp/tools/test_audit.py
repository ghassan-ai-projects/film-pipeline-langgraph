"""Unit tests for film_pipeline.mcp.tools.audit."""

from __future__ import annotations

import asyncio
from typing import cast

from film_pipeline.app.runtime import get_runtime as gr
from film_pipeline.mcp.tools import (
    create_film_project,
    explain_agent_routing,
    explain_kb_context,
    explain_last_decision,
    get_audit_log,
    set_active_project,
)


def test_get_audit_log_returns_events() -> None:
    asyncio.run(create_film_project({"project_id": "proj-audit-1"}))
    result = asyncio.run(get_audit_log({"project_id": "proj-audit-1"}))
    assert result["ok"] is True
    assert cast(int, result["total"]) >= 1


def test_get_audit_log_with_limit() -> None:
    asyncio.run(create_film_project({"project_id": "proj-audit-2"}))
    result = asyncio.run(get_audit_log({"project_id": "proj-audit-2", "limit": 1}))
    assert result["ok"] is True
    assert len(cast(list[object], result["events"])) <= 1


def test_explain_last_decision_with_events() -> None:
    asyncio.run(create_film_project({"project_id": "proj-audit-3"}))
    result = asyncio.run(explain_last_decision({}))
    assert result["ok"] is True
    assert "action" in result


def test_explain_last_decision_empty() -> None:
    rt = gr()
    rt.audit_events.clear()
    result = asyncio.run(explain_last_decision({}))
    assert result["ok"] is True
    assert result["message"] == "No decisions recorded yet."


def test_explain_agent_routing_no_active_project() -> None:
    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(explain_agent_routing({}))
    assert result["ok"] is True
    assert result["decisions"] == []


def test_explain_agent_routing_no_decisions_yet() -> None:
    asyncio.run(create_film_project({"project_id": "proj-audit-4"}))
    asyncio.run(set_active_project({"project_ref": "proj-audit-4"}))
    result = asyncio.run(explain_agent_routing({}))
    assert result["ok"] is True
    assert result["decisions"] == []


def test_explain_kb_context() -> None:
    result = asyncio.run(explain_kb_context({}))
    assert result["ok"] is True
    assert "message" in result
