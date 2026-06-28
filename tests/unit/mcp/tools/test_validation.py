"""Unit tests for film_pipeline.mcp.tools.validation."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.mcp.tools import (
    create_film_project,
    get_validation_report,
    list_validation_issues,
    run_validation,
    set_active_project,
)


def test_run_validation_requires_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)
    result = asyncio.run(run_validation({}))
    assert result["ok"] is False


def test_run_validation_unknown_phase(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("val-bad-phase", "Bad Phase")
    rt.set_active("val-bad-phase")
    active = rt.get_active()
    assert active is not None
    active["current_phase"] = "not-a-real-phase"
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(run_validation({}))
    assert result["ok"] is False
    assert "Unknown phase" in cast(str, result["error"])


def test_run_validation_no_validators_for_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("val-no-validators", "No Validators")
    rt.set_active("val-no-validators")
    active = rt.get_active()
    assert active is not None
    active["current_phase"] = "intake"
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(run_validation({}))
    assert result["ok"] is True
    assert result["message"] == "No validators found for this phase."


def test_run_validation_script_phase_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("val-script-1", "Script Phase")
    rt.set_active("val-script-1")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    state["current_phase"] = "script"
    rt.projects["val-script-1"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(run_validation({}))
    assert result["ok"] is True
    assert result["phase"] == "script"
    assert len(cast(list[object], result["reports"])) >= 1


def test_run_validation_visual_dev_phase_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("val-visdev-1", "Visual Dev Phase")
    rt.set_active("val-visdev-1")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    state = rt._run_phase_node(state, "visual_dev")
    state["current_phase"] = "visual_dev"
    rt.projects["val-visdev-1"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(run_validation({}))
    assert result["ok"] is True
    assert result["phase"] == "visual_dev"
    assert len(cast(list[object], result["reports"])) >= 1


def test_get_validation_report_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(get_validation_report({}))
    assert result["ok"] is False


def test_get_validation_report_uses_qc_stored_reports() -> None:
    asyncio.run(create_film_project({"project_id": "val-stored-1"}))
    asyncio.run(set_active_project({"project_ref": "val-stored-1"}))
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    active = rt.get_active()
    assert active is not None
    active["_validation_reports"] = [{"validator_id": "fake", "score": 1.0}]
    rt.projects["val-stored-1"] = active

    result = asyncio.run(get_validation_report({}))
    assert result["ok"] is True
    assert result["source"] == "qc_node"
    assert len(cast(list[object], result["reports"])) == 1


def test_get_validation_report_no_phase_and_no_stored_reports() -> None:
    asyncio.run(create_film_project({"project_id": "val-no-phase-1"}))
    asyncio.run(set_active_project({"project_ref": "val-no-phase-1"}))
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    active = rt.get_active()
    assert active is not None
    active["current_phase"] = ""
    active.pop("_validation_reports", None)
    rt.projects["val-no-phase-1"] = active

    result = asyncio.run(get_validation_report({}))
    assert result["ok"] is False


def test_get_validation_report_live_dispatch_script_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("val-live-script-1", "Live Script")
    rt.set_active("val-live-script-1")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    state["current_phase"] = "script"
    state.pop("_validation_reports", None)
    rt.projects["val-live-script-1"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(get_validation_report({}))
    assert result["ok"] is True
    assert result["source"] == "live"
    assert result["phase"] == "script"


def test_get_validation_report_live_dispatch_visual_dev_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("val-live-visdev-1", "Live VisDev")
    rt.set_active("val-live-visdev-1")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    state = rt._run_phase_node(state, "visual_dev")
    state["current_phase"] = "visual_dev"
    state.pop("_validation_reports", None)
    rt.projects["val-live-visdev-1"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(get_validation_report({}))
    assert result["ok"] is True
    assert result["source"] == "live"
    assert result["phase"] == "visual_dev"


def test_list_validation_issues_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(list_validation_issues({}))
    assert result["ok"] is False


def test_list_validation_issues_with_stored_issues() -> None:
    asyncio.run(create_film_project({"project_id": "val-issues-1"}))
    asyncio.run(set_active_project({"project_ref": "val-issues-1"}))
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    active = rt.get_active()
    assert active is not None
    active["issues"] = [
        {
            "validator_id": "fake_validator",
            "code": "X",
            "message": "bad",
            "severity": "warning",
        }
    ]
    rt.projects["val-issues-1"] = active

    result = asyncio.run(list_validation_issues({}))
    assert result["ok"] is True
    assert len(cast(list[object], result["issues"])) == 1


def test_list_validation_issues_empty() -> None:
    asyncio.run(create_film_project({"project_id": "val-issues-2"}))
    asyncio.run(set_active_project({"project_ref": "val-issues-2"}))
    result = asyncio.run(list_validation_issues({}))
    assert result["ok"] is True
    assert result["issues"] == []
