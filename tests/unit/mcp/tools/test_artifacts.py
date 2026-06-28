"""Unit tests for film_pipeline.mcp.tools.artifacts."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.app.runtime import get_runtime as gr
from film_pipeline.mcp.tools import (
    create_film_project,
    inspect_artifact,
    inspect_reference,
    inspect_scene,
    inspect_shot,
    list_artifacts,
    list_shots,
    set_active_project,
)


def _build_runtime_through_shot_bible(tmp_path: Path, project_id: str) -> StudioRuntime:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project(project_id, "Artifacts Test")
    rt.set_active(project_id)
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    state = rt._run_phase_node(state, "visual_dev")
    state = rt._run_phase_node(state, "shot_bible")
    rt.projects[project_id] = state
    return rt


def _make_active_project(project_id: str) -> None:
    asyncio.run(create_film_project({"project_id": project_id}))
    asyncio.run(set_active_project({"project_ref": project_id}))


def test_list_artifacts_requires_active_project() -> None:
    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(list_artifacts({}))
    assert result["ok"] is False


def test_list_artifacts_empty_for_new_project() -> None:
    _make_active_project("proj-artifacts-1")
    result = asyncio.run(list_artifacts({}))
    assert result["ok"] is True
    assert result["artifacts"] == []


def test_list_artifacts_unknown_phase_errors() -> None:
    _make_active_project("proj-artifacts-2")
    result = asyncio.run(list_artifacts({"phase": "not-a-real-phase"}))
    assert result["ok"] is False


def test_inspect_artifact_requires_artifact_id() -> None:
    _make_active_project("proj-artifacts-3")
    result = asyncio.run(inspect_artifact({}))
    assert result["ok"] is False
    assert "artifact_id is required" in cast(str, result["error"])


def test_inspect_artifact_not_found() -> None:
    _make_active_project("proj-artifacts-4")
    result = asyncio.run(inspect_artifact({"artifact_id": "nope", "phase": "script", "version": 1}))
    assert result["ok"] is False


def test_list_shots_when_no_shot_bible() -> None:
    _make_active_project("proj-artifacts-5")
    result = asyncio.run(list_shots({}))
    assert result["ok"] is True
    assert result["shots"] == []


def test_inspect_shot_requires_shot_id() -> None:
    _make_active_project("proj-artifacts-6")
    result = asyncio.run(inspect_shot({}))
    assert result["ok"] is False


def test_inspect_shot_no_bible_errors() -> None:
    _make_active_project("proj-artifacts-7")
    result = asyncio.run(inspect_shot({"shot_id": "S001"}))
    assert result["ok"] is False


def test_inspect_scene_requires_scene_id() -> None:
    _make_active_project("proj-artifacts-8")
    result = asyncio.run(inspect_scene({}))
    assert result["ok"] is False


def test_inspect_scene_no_script_errors() -> None:
    _make_active_project("proj-artifacts-9")
    result = asyncio.run(inspect_scene({"scene_id": "scene_01"}))
    assert result["ok"] is False


def test_inspect_reference_requires_reference_id() -> None:
    _make_active_project("proj-artifacts-10")
    result = asyncio.run(inspect_reference({}))
    assert result["ok"] is False


def test_inspect_reference_no_index_errors() -> None:
    _make_active_project("proj-artifacts-11")
    result = asyncio.run(inspect_reference({"reference_id": "ref-001"}))
    assert result["ok"] is False


def test_inspect_artifact_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("proj-artifacts-17", "Inspect Success")
    rt.set_active("proj-artifacts-17")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    rt.projects["proj-artifacts-17"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(inspect_artifact({"artifact_id": "script", "phase": "script"}))
    assert result["ok"] is True
    assert result["content"]


def test_list_artifacts_with_phase_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("proj-artifacts-18", "List Filter")
    rt.set_active("proj-artifacts-18")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    rt.projects["proj-artifacts-18"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(list_artifacts({"phase": "script"}))
    assert result["ok"] is True
    assert len(cast(list[object], result["artifacts"])) >= 1


def test_inspect_scene_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("proj-artifacts-19", "Inspect Scene")
    rt.set_active("proj-artifacts-19")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    rt.projects["proj-artifacts-19"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    from film_pipeline.schemas._base import FilmPhase

    assert rt.services is not None
    script_data = rt.services.artifact_store.load(
        "proj-artifacts-19", FilmPhase("script"), "script", 1
    )
    scenes = cast(list[dict[str, object]], script_data.get("scenes", []))
    assert scenes, "expected at least one scene from mock script generation"
    scene_id = str(scenes[0].get("scene_id", ""))

    result = asyncio.run(inspect_scene({"scene_id": scene_id}))
    assert result["ok"] is True
    assert result["scene"]


def test_inspect_scene_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("proj-artifacts-20", "Inspect Scene Missing")
    rt.set_active("proj-artifacts-20")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    rt.projects["proj-artifacts-20"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(inspect_scene({"scene_id": "totally-bogus-scene-id"}))
    assert result["ok"] is False


def test_list_shots_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = _build_runtime_through_shot_bible(tmp_path, "proj-artifacts-12")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(list_shots({}))
    assert result["ok"] is True
    shots = cast(list[dict[str, object]], result["shots"])
    assert len(shots) >= 1
    assert shots[0]["shot_id"] == "shot_0001"


def test_inspect_shot_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = _build_runtime_through_shot_bible(tmp_path, "proj-artifacts-13")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(inspect_shot({"shot_id": "shot_0001"}))
    assert result["ok"] is True
    shot = cast(dict[str, object], result["shot"])
    assert shot["shot_id"] == "shot_0001"


def test_inspect_shot_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = _build_runtime_through_shot_bible(tmp_path, "proj-artifacts-14")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(inspect_shot({"shot_id": "no-such-shot"}))
    assert result["ok"] is False


def test_inspect_reference_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("proj-artifacts-15", "Reference Test")
    rt.set_active("proj-artifacts-15")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    state = rt._run_phase_node(state, "visual_dev")
    rt.projects["proj-artifacts-15"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    from film_pipeline.schemas._base import FilmPhase

    assert rt.services is not None
    data = rt.services.artifact_store.load(
        "proj-artifacts-15", FilmPhase("visual_dev"), "reference_index", 1
    )
    entries = cast(list[dict[str, object]], data.get("entries", []))
    assert entries, "expected at least one reference entry from mock visual_dev"
    reference_id = str(entries[0].get("reference_id", entries[0].get("id", "")))

    result = asyncio.run(inspect_reference({"reference_id": reference_id}))
    assert result["ok"] is True
    assert result["reference"]


def test_inspect_reference_not_found_with_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("proj-artifacts-16", "Reference Missing")
    rt.set_active("proj-artifacts-16")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    state = rt._run_phase_node(state, "visual_dev")
    rt.projects["proj-artifacts-16"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(inspect_reference({"reference_id": "totally-bogus-ref-id"}))
    assert result["ok"] is False
