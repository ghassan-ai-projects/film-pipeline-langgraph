"""Unit tests for film_pipeline.mcp.tools.planning."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.mcp.tools import generate_plan, generate_shot_bible, initialize_budget


def _build_runtime_with_shot_bible(tmp_path: Path, project_id: str) -> StudioRuntime:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project(project_id, "Planning Test")
    rt.set_active(project_id)
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    state = rt._run_phase_node(state, "visual_dev")
    rt.projects[project_id] = state

    import film_pipeline.mcp.tools as mcp_tools

    original_get_runtime = mcp_tools.get_runtime
    mcp_tools.get_runtime = lambda: rt
    try:
        result = asyncio.run(generate_shot_bible({}))
    finally:
        mcp_tools.get_runtime = original_get_runtime
    assert result["ok"] is True, result
    return rt


def test_initialize_budget_requires_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)
    result = asyncio.run(initialize_budget({}))
    assert result["ok"] is False


def test_initialize_budget_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = _build_runtime_with_shot_bible(tmp_path, "plan-budget-1")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(initialize_budget({"cap_usd": 50.0}))
    assert result["ok"] is True
    assert result["cap_usd"] == 50.0
    assert result["remaining_usd"] == 50.0
    active = rt.get_active()
    assert active is not None
    assert active["budget_state_ref"] == result["budget_state_ref"]


def test_initialize_budget_creates_new_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = "plan-budget-version"
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project(project_id, "Budget Version Test")
    rt.set_active(project_id)
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result1 = asyncio.run(initialize_budget({"cap_usd": 10.0}))
    assert result1["ok"] is True

    result2 = asyncio.run(initialize_budget({"cap_usd": 20.0}))
    assert result2["ok"] is True

    assert rt.services is not None
    store = rt.services.artifact_store
    meta1 = store.load_metadata(project_id, "gen_planning", "budget_state", 1)
    meta2 = store.load_metadata(project_id, "gen_planning", "budget_state", 2)
    assert meta1.version == 1
    assert meta2.version == 2


def test_generate_plan_requires_shot_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("plan-no-matrix", "No Matrix")
    rt.set_active("plan-no-matrix")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(generate_plan({}))
    assert result["ok"] is False
    assert "MasterFilmMatrix not found" in cast(str, result["error"])


def test_generate_plan_raises_on_raw_dict_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``generate_plan`` reads the persisted MasterFilmMatrix as a raw dict
    via ``ArtifactStore.load`` (which always returns ``dict[str, Any]``) and
    then accesses ``matrix.rows`` as if it were a model instance. This is a
    pre-existing bug in the original (pre-split) tool implementation, carried
    over verbatim by this refactor. This test pins the current behavior;
    it is not asserting desired behavior.
    """
    rt = _build_runtime_with_shot_bible(tmp_path, "plan-success-1")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    with pytest.raises(AttributeError):
        asyncio.run(generate_plan({}))


def test_initialize_budget_save_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("plan-budget-fail", "Budget Fail")
    rt.set_active("plan-budget-fail")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    assert rt.services is not None
    store = rt.services.artifact_store

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("save boom")

    monkeypatch.setattr(store, "save", _raise)
    result = asyncio.run(initialize_budget({}))
    assert result["ok"] is False
    assert "Budget initialization failed" in cast(str, result["error"])


def test_generate_plan_requires_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)
    result = asyncio.run(generate_plan({}))
    assert result["ok"] is False
    assert "No active project" in cast(str, result["error"])


def test_generate_plan_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("plan-success-2", "Plan Success")
    rt.set_active("plan-success-2")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    from film_pipeline.schemas.matrix import MasterFilmMatrix, MasterFilmMatrixRow

    matrix = MasterFilmMatrix(
        project_id="plan-success-2",
        rows=[
            MasterFilmMatrixRow(
                shot_id="S001",
                act_id="A1",
                sequence_id="SEQ1",
                scene_id="SC1",
                scene_intent_ref="intent-1",
                duration_seconds=5,
                risk_level="low",
            )
        ],
    )

    assert rt.services is not None
    store = rt.services.artifact_store
    original_load = store.load

    def _fake_load(project_id: str, phase: Any, artifact_id: str, version: int) -> Any:
        if artifact_id == "master_film_matrix":
            return matrix
        return original_load(project_id, phase, artifact_id, version)

    monkeypatch.setattr(store, "load", _fake_load)
    result = asyncio.run(generate_plan({}))

    assert result["ok"] is True
    assert "generation_plan_ref" in result
    assert result["shot_count"] == 1
    assert result["total_estimated_cost"] == 0.1


def test_generate_plan_save_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("plan-save-fail", "Plan Save Fail")
    rt.set_active("plan-save-fail")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    from film_pipeline.schemas.matrix import MasterFilmMatrix, MasterFilmMatrixRow

    matrix = MasterFilmMatrix(
        project_id="plan-save-fail",
        rows=[
            MasterFilmMatrixRow(
                shot_id="S001",
                act_id="A1",
                sequence_id="SEQ1",
                scene_id="SC1",
                scene_intent_ref="intent-1",
                duration_seconds=5,
            )
        ],
    )

    assert rt.services is not None
    store = rt.services.artifact_store
    original_load = store.load

    def _fake_load(project_id: str, phase: Any, artifact_id: str, version: int) -> Any:
        if artifact_id == "master_film_matrix":
            return matrix
        return original_load(project_id, phase, artifact_id, version)

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("save boom")

    monkeypatch.setattr(store, "load", _fake_load)
    monkeypatch.setattr(store, "save", _raise)
    result = asyncio.run(generate_plan({}))
    assert result["ok"] is False
    assert "Plan generation failed" in cast(str, result["error"])
