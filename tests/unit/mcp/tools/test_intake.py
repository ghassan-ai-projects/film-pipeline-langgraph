"""Unit tests for film_pipeline.mcp.tools.intake."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from film_pipeline.mcp.tools import (
    approve_intake,
    create_film_project,
    get_intake_analysis,
    set_active_project,
    submit_idea,
)
from film_pipeline.studio.runtime import get_runtime as gr

CallTool = Callable[..., Any]


def _make_active_project(project_id: str, call_tool: CallTool) -> None:
    call_tool(create_film_project, {"project_id": project_id})
    call_tool(set_active_project, {"project_ref": project_id})


def test_submit_idea_requires_idea_text(call_tool: CallTool) -> None:
    _make_active_project("intake-empty-1", call_tool)
    result = call_tool(submit_idea, {})
    assert result["ok"] is False
    assert "idea is required" in cast(str, result["error"])


def test_submit_idea_success(call_tool: CallTool) -> None:
    _make_active_project("intake-submit-1", call_tool)
    result = call_tool(submit_idea, {"idea": "A clockmaker who can stop time."})
    assert result["ok"] is True
    assert result["project_id"] == "intake-submit-1"
    assert result["current_phase"] == "intake"


def test_submit_idea_propagates_target_scene_count(call_tool: CallTool) -> None:
    _make_active_project("intake-scene-count-1", call_tool)
    call_tool(submit_idea, {"idea": "A 12-scene mystery.", "target_scene_count": 12})
    rt = gr()
    active = rt.get_active()
    assert active is not None
    assert active.get("target_scene_count") == 12


def test_get_intake_analysis_falls_back_to_raw_idea_or_errors(call_tool: CallTool) -> None:
    _make_active_project("intake-analysis-1", call_tool)
    # Before submitting, no idea and no artifact -> error.
    result = call_tool(get_intake_analysis, {})
    assert result["ok"] is False

    call_tool(submit_idea, {"idea": "A whisper in an empty theater."})
    result2 = call_tool(get_intake_analysis, {})
    assert result2["ok"] is True
    assert "analysis" in result2


def test_approve_intake_rejects_wrong_phase(call_tool: CallTool) -> None:
    _make_active_project("intake-approve-wrong-1", call_tool)
    call_tool(submit_idea, {"idea": "A train that only stops at midnight."})
    rt = gr()
    active = rt.get_active()
    assert active is not None
    active["current_phase"] = "script"
    rt.projects["intake-approve-wrong-1"] = active

    result = call_tool(approve_intake, {"confirmed": True})
    assert result["ok"] is False
    assert "not intake" in cast(str, result["error"])


def test_approve_intake_success(call_tool: CallTool) -> None:
    _make_active_project("intake-approve-ok-1", call_tool)
    call_tool(submit_idea, {"idea": "A garden that grows memories instead of flowers."})

    result = call_tool(approve_intake, {"confirmed": True})
    assert result["ok"] is True
    assert result["project_id"] == "intake-approve-ok-1"
