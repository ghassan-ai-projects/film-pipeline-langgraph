"""Unit tests for film_pipeline.mcp.tools.projects."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from film_pipeline.mcp.tools import (
    create_film_project,
    find_project,
    get_active_project,
    get_project_summary,
    list_projects,
    set_active_project,
)
from film_pipeline.studio.runtime import get_runtime as gr

CallTool = Callable[..., Any]


def test_create_film_project_requires_project_id(call_tool: CallTool) -> None:
    result = call_tool(create_film_project, {})
    assert result["ok"] is False
    assert "project_id is required" in cast(str, result["error"])


def test_create_film_project_success_defaults_to_server_mode(call_tool: CallTool) -> None:
    rt = gr()
    result = call_tool(
        create_film_project, {"project_id": "proj-create-1", "title": "T", "slug": "s"}
    )
    assert result["ok"] is True
    assert result["project_id"] == "proj-create-1"
    assert rt.get_project("proj-create-1") is not None


def test_create_film_project_rejects_bad_runtime_mode(call_tool: CallTool) -> None:
    result = call_tool(
        create_film_project, {"project_id": "proj-create-2", "runtime_mode": "bogus"}
    )
    assert result["ok"] is False
    assert "runtime_mode must be" in cast(str, result["error"])


def test_list_and_find_project(call_tool: CallTool) -> None:
    call_tool(create_film_project, {"project_id": "proj-find-1", "slug": "find-slug-1"})
    listed = call_tool(list_projects, {})
    assert listed["ok"] is True
    assert "proj-find-1" in cast(list[str], listed["projects"])

    by_id = call_tool(find_project, {"ref": "proj-find-1"})
    assert by_id["ok"] is True
    assert by_id["project_id"] == "proj-find-1"

    by_slug = call_tool(find_project, {"ref": "find-slug-1"})
    assert by_slug["ok"] is True
    assert by_slug["project_id"] == "proj-find-1"


def test_find_project_not_found(call_tool: CallTool) -> None:
    result = call_tool(find_project, {"ref": "does-not-exist-xyz"})
    assert result["ok"] is False


def test_set_and_get_active_project(call_tool: CallTool) -> None:
    call_tool(create_film_project, {"project_id": "proj-active-1"})
    set_result = call_tool(set_active_project, {"project_ref": "proj-active-1"})
    assert set_result["ok"] is True
    assert set_result["active_project_id"] == "proj-active-1"

    active_result = call_tool(get_active_project, {})
    assert active_result["ok"] is True
    assert active_result["project_id"] == "proj-active-1"


def test_set_active_project_unknown_returns_error(call_tool: CallTool) -> None:
    result = call_tool(set_active_project, {"project_ref": "totally-unknown-project"})
    assert result["ok"] is False


def test_get_project_summary_success(call_tool: CallTool) -> None:
    call_tool(create_film_project, {"project_id": "proj-summary-1"})
    call_tool(set_active_project, {"project_ref": "proj-summary-1"})
    result = call_tool(get_project_summary, {})
    assert result["ok"] is True
    assert result["project_id"] == "proj-summary-1"
    assert "artifact_count" in result
