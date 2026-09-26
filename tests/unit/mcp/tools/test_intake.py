"""Unit tests for film_pipeline.mcp.tools.intake."""

from __future__ import annotations

import asyncio
from typing import cast

from film_pipeline.mcp.tools import (
    approve_intake,
    create_film_project,
    get_intake_analysis,
    set_active_project,
    submit_idea,
)
from film_pipeline.studio.runtime import get_runtime as gr


def _make_active_project(project_id: str) -> None:
    asyncio.run(create_film_project({"project_id": project_id}))
    asyncio.run(set_active_project({"project_ref": project_id}))


def test_submit_idea_requires_idea_text() -> None:
    _make_active_project("intake-empty-1")
    result = asyncio.run(submit_idea({}))
    assert result["ok"] is False
    assert "idea is required" in cast(str, result["error"])


def test_submit_idea_success() -> None:
    _make_active_project("intake-submit-1")
    result = asyncio.run(submit_idea({"idea": "A clockmaker who can stop time."}))
    assert result["ok"] is True
    assert result["project_id"] == "intake-submit-1"
    assert result["current_phase"] == "intake"


def test_submit_idea_propagates_target_scene_count() -> None:
    _make_active_project("intake-scene-count-1")
    asyncio.run(submit_idea({"idea": "A 12-scene mystery.", "target_scene_count": 12}))
    rt = gr()
    active = rt.get_active()
    assert active is not None
    assert active.get("target_scene_count") == 12


def test_get_intake_analysis_falls_back_to_raw_idea_or_errors() -> None:
    _make_active_project("intake-analysis-1")
    # Before submitting, no idea and no artifact -> error.
    result = asyncio.run(get_intake_analysis({}))
    assert result["ok"] is False

    asyncio.run(submit_idea({"idea": "A whisper in an empty theater."}))
    result2 = asyncio.run(get_intake_analysis({}))
    assert result2["ok"] is True
    assert "analysis" in result2


def test_approve_intake_rejects_wrong_phase() -> None:
    _make_active_project("intake-approve-wrong-1")
    asyncio.run(submit_idea({"idea": "A train that only stops at midnight."}))
    rt = gr()
    active = rt.get_active()
    assert active is not None
    active["current_phase"] = "script"
    rt.projects["intake-approve-wrong-1"] = active

    result = asyncio.run(approve_intake({"confirmed": True}))
    assert result["ok"] is False
    assert "not intake" in cast(str, result["error"])


def test_approve_intake_success() -> None:
    _make_active_project("intake-approve-ok-1")
    asyncio.run(submit_idea({"idea": "A garden that grows memories instead of flowers."}))

    result = asyncio.run(approve_intake({"confirmed": True}))
    assert result["ok"] is True
    assert result["project_id"] == "intake-approve-ok-1"
