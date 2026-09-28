"""Integration test: full MCP flow through intake → approval → constitution."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import pytest

from film_pipeline.mcp.tools import (
    approve_phase,
    create_film_project,
    get_active_project,
    get_current_phase,
    list_projects,
    request_revision,
    set_active_project,
    submit_idea,
)

CallTool = Callable[..., Any]


@pytest.mark.integration
class TestMCPFlow:
    """End-to-end MCP tool flow: create project, submit idea, approve, advance."""

    @classmethod
    def setup_class(cls) -> None:
        """Reset runtime between test runs."""
        from film_pipeline.studio.runtime import get_runtime, reset_runtime

        reset_runtime("mock")
        rt = get_runtime()
        rt.projects.clear()
        rt.active_project_id = ""

    def setup_method(self) -> None:
        """Reset runtime before each test."""
        from film_pipeline.studio.runtime import get_runtime, reset_runtime

        reset_runtime("mock")
        rt = get_runtime()
        rt.projects.clear()
        rt.active_project_id = ""

    def test_create_and_list_projects(self, call_tool: CallTool) -> None:
        loop = asyncio.new_event_loop()
        try:
            result = call_tool(
                create_film_project,
                {"project_id": "mini-film-01", "title": "Mini Film", "slug": "mini"},
            )
            assert result["ok"] is True
            assert result["project_id"] == "mini-film-01"

            result2 = call_tool(list_projects, {})
            assert "mini-film-01" in result2["projects"]
        finally:
            loop.close()

    def test_set_and_get_active_project(self, call_tool: CallTool) -> None:
        loop = asyncio.new_event_loop()
        try:
            call_tool(create_film_project, {"project_id": "mini-film-02", "title": "Test"})
            call_tool(set_active_project, {"project_ref": "mini-film-02"})
            result = call_tool(get_active_project, {})
            assert result["project_id"] == "mini-film-02"
        finally:
            loop.close()

    def test_submit_idea_triggers_intake(self, call_tool: CallTool) -> None:
        loop = asyncio.new_event_loop()
        try:
            call_tool(create_film_project, {"project_id": "mini-film-03", "title": "Idea Test"})
            call_tool(set_active_project, {"project_ref": "mini-film-03"})
            result = call_tool(
                submit_idea,
                {
                    "idea": "A lonely watchmaker hears the rain stop. "
                    "He discovers time itself is freezing."
                },
            )
            assert result["ok"] is True
            # Intake node sets current_phase to "intake"
            assert result["current_phase"] == "intake"
            assert result["human_approval_required"] is True
        finally:
            loop.close()

    def test_approve_phase_after_submit(self, call_tool: CallTool) -> None:
        loop = asyncio.new_event_loop()
        try:
            call_tool(create_film_project, {"project_id": "mini-film-04", "title": "Approve Test"})
            call_tool(set_active_project, {"project_ref": "mini-film-04"})
            call_tool(submit_idea, {"idea": "Test idea."})

            # Approve the intaken idea
            result = call_tool(approve_phase, {"confirmed": True})
            assert result["ok"] is True
            assert result["current_phase"] == "constitution"
        finally:
            loop.close()

    def test_request_revision_adds_issue(self, call_tool: CallTool) -> None:
        loop = asyncio.new_event_loop()
        try:
            call_tool(create_film_project, {"project_id": "mini-film-05", "title": "Revision Test"})
            call_tool(set_active_project, {"project_ref": "mini-film-05"})
            call_tool(submit_idea, {"idea": "Test."})

            result = call_tool(
                request_revision, {"note": "Needs more character detail", "confirmed": True}
            )
            assert result["ok"] is True
            assert len(result["issues"]) >= 1
        finally:
            loop.close()

    def test_get_current_phase(self, call_tool: CallTool) -> None:
        loop = asyncio.new_event_loop()
        try:
            call_tool(create_film_project, {"project_id": "mini-film-06", "title": "Phase Test"})
            call_tool(set_active_project, {"project_ref": "mini-film-06"})
            call_tool(submit_idea, {"idea": "Test."})

            result = call_tool(get_current_phase, {})
            assert result["current_phase"] == "intake"
        finally:
            loop.close()

    def test_full_intake_approval_flow(self, call_tool: CallTool) -> None:
        """Complete flow: create → submit idea → approve → verify."""
        loop = asyncio.new_event_loop()
        try:
            # 1. Create project
            r = call_tool(create_film_project, {"project_id": "flow-01", "title": "Full Flow"})
            assert r["ok"] is True

            # 2. Set active
            r = call_tool(set_active_project, {"project_ref": "flow-01"})
            assert r["ok"] is True

            # 3. Submit idea
            r = call_tool(submit_idea, {"idea": "A time traveler tries to prevent a mistake."})
            assert r["ok"] is True
            assert r["current_phase"] == "intake"
            assert r["human_approval_required"] is True

            # 4. Request revision
            r = call_tool(request_revision, {"note": "More sci-fi tone", "confirmed": True})
            assert r["ok"] is True
            assert len(r["issues"]) >= 1

            # 5. Approve after revision
            r = call_tool(approve_phase, {"confirmed": True})
            assert r["ok"] is True
            assert r["current_phase"] == "constitution"

            # 6. Verify project exists and is active
            r = call_tool(get_active_project, {})
            assert r["project_id"] == "flow-01"
            assert r["current_phase"] == "constitution"
        finally:
            loop.close()

    def test_unknown_project_ref_errors(self, call_tool: CallTool) -> None:
        loop = asyncio.new_event_loop()
        try:
            r = call_tool(set_active_project, {"project_ref": "nonexistent"})
            assert r.get("ok") is False
        finally:
            loop.close()

    def test_submit_idea_without_an_active_project_raises(self, call_tool: CallTool) -> None:
        """Called directly, the handler asserts the dispatch precondition.

        `MCPServer.call` refuses the request with `no_active_project` before the
        handler runs (see `test_active_project_precondition`). A direct caller
        bypasses that gate, so the handler raises rather than returning a
        wrong answer.
        """
        from film_pipeline.operations.errors import ProjectNotFoundError

        with pytest.raises(ProjectNotFoundError):
            call_tool(submit_idea, {"idea": "x"})

    def test_create_duplicate_project(self, call_tool: CallTool) -> None:
        loop = asyncio.new_event_loop()
        try:
            r1 = call_tool(create_film_project, {"project_id": "dup-test", "title": "Original"})
            assert r1["ok"] is True

            r2 = call_tool(create_film_project, {"project_id": "dup-test", "title": "Duplicate"})
            assert r2.get("ok") is False
        finally:
            loop.close()
