"""Unit tests for film_pipeline.mcp.tools.review."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from film_pipeline.mcp.tools import (
    approve_phase,
    create_film_project,
    request_revision,
    review_phase_artifacts,
    set_active_project,
    submit_idea,
)
from film_pipeline.studio.runtime import StudioRuntime

CallTool = Callable[..., Any]


def test_review_phase_artifacts_requires_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, call_tool: CallTool
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("review-no-phase", "Review")
    rt.set_active("review-no-phase")
    active = rt.get_active()
    assert active is not None
    active["current_phase"] = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = call_tool(review_phase_artifacts, {})
    assert result["ok"] is False
    assert "No phase specified" in cast(str, result["error"])


def test_review_phase_artifacts_unknown_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, call_tool: CallTool
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("review-bad-phase", "Review")
    rt.set_active("review-bad-phase")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = call_tool(review_phase_artifacts, {"phase": "not-a-real-phase"})
    assert result["ok"] is False
    assert "Unknown phase" in cast(str, result["error"])


def test_review_phase_artifacts_success(call_tool: CallTool) -> None:
    call_tool(create_film_project, {"project_id": "review-success"})
    call_tool(set_active_project, {"project_ref": "review-success"})
    call_tool(submit_idea, {"idea": "A quiet harbor town at dawn."})

    result = call_tool(review_phase_artifacts, {"phase": "intake"})
    assert result["ok"] is True
    assert result["phase"] == "intake"
    # Either the full review package or the artifact-list fallback is present.
    assert "review_package" in result or "artifacts" in result


def test_approve_phase_no_active_project_errors(call_tool: CallTool) -> None:
    from film_pipeline.studio.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = call_tool(approve_phase, {"confirmed": True})
    assert result["ok"] is False


def test_approve_phase_success(call_tool: CallTool) -> None:
    call_tool(create_film_project, {"project_id": "review-approve-1"})
    call_tool(set_active_project, {"project_ref": "review-approve-1"})
    call_tool(submit_idea, {"idea": "A clockmaker who freezes time."})

    result = call_tool(approve_phase, {"confirmed": True})
    assert result["ok"] is True
    assert result["project_id"] == "review-approve-1"


def test_request_revision_no_active_project_errors(call_tool: CallTool) -> None:
    from film_pipeline.studio.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = call_tool(request_revision, {"note": "fix it", "confirmed": True})
    assert result["ok"] is False


def test_request_revision_success(call_tool: CallTool) -> None:
    call_tool(create_film_project, {"project_id": "review-revise-1"})
    call_tool(set_active_project, {"project_ref": "review-revise-1"})
    call_tool(submit_idea, {"idea": "A lighthouse keeper hears a ship that isn't there."})

    result = call_tool(request_revision, {"note": "needs more detail", "confirmed": True})
    assert result["ok"] is True
    assert result["project_id"] == "review-revise-1"
    assert len(cast(list[object], result["issues"])) >= 1


def test_review_phase_artifacts_generator_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, call_tool: CallTool
) -> None:
    """When ReviewPackageGenerator raises, review_phase_artifacts falls back
    to the plain artifact list response.
    """
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("review-fallback", "Review Fallback")
    rt.set_active("review-fallback")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    from film_pipeline.governance.generator import ReviewPackageGenerator

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(ReviewPackageGenerator, "build", _raise)
    result = call_tool(review_phase_artifacts, {"phase": "intake"})
    assert result["ok"] is True
    assert "artifacts" in result
    assert result["phase"] == "intake"


@pytest.mark.parametrize(
    ("action", "expected_text"),
    [
        ("wait_for_human", "Review the human_gate package"),
        ("handle_blockers", "Blocking issues detected"),
        ("escalate_to_human", "human decision"),
        ("escalate_to_failure_handler", "triage by failure-handling agent"),
        ("continue_unrelated_work", "Generation is blocked"),
        ("present_review_package", "candidate artifacts"),
        ("revise", "Pending revision"),
        ("advance_to_script", "Ready to advance to script"),
        ("unknown_action", "Current action: unknown_action"),
    ],
)
def test_build_orchestrator_recommendation_branches(action: str, expected_text: str) -> None:
    from film_pipeline.mcp.tools.review import _build_orchestrator_recommendation

    class FakeRouter:
        next_action = action
        human_gate = "human_gate"

    rec = _build_orchestrator_recommendation({}, FakeRouter())
    assert expected_text in rec
