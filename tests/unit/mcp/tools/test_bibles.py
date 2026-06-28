"""Unit tests for film_pipeline.mcp.tools.bibles."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.mcp.tools import (
    generate_camera_bible,
    generate_character_bible,
    generate_environment_bible,
    generate_shot_bible,
    generate_style_bible,
)
from film_pipeline.mcp.tools.bibles import _extract_script_text


def test_extract_script_text_none_returns_empty() -> None:
    assert _extract_script_text(None) == ""


def test_extract_script_text_non_dict_returns_str() -> None:
    assert _extract_script_text(cast(dict[str, object], "raw-script-text")) == "raw-script-text"


def test_extract_script_text_builds_lines_from_scenes() -> None:
    script_data: dict[str, object] = {
        "scenes": [
            {
                "heading": "INT. HOUSE - DAY",
                "action_lines": ["Leo enters."],
                "dialogue_lines": [{"character_id": "leo", "line": "Hello."}],
            }
        ]
    }
    text = _extract_script_text(script_data)
    assert "INT. HOUSE - DAY" in text
    assert "Leo enters." in text
    assert "leo: Hello." in text


def test_extract_script_text_empty_scenes_returns_empty_string() -> None:
    assert _extract_script_text({"scenes": []}) == ""


def _build_runtime_through_script(tmp_path: Path, project_id: str) -> StudioRuntime:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project(project_id, "Bible Test")
    rt.set_active(project_id)
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    rt.projects[project_id] = state
    return rt


def test_generate_character_bible_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(generate_character_bible({"character_id": "leo"}))
    assert result["ok"] is False


def test_generate_environment_bible_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(generate_environment_bible({"environment_id": "studio"}))
    assert result["ok"] is False


def test_generate_environment_bible_missing_constitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("bible-env-3", "No Constitution")
    rt.set_active("bible-env-3")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    rt.projects["bible-env-3"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    # Manually save a script artifact without going through constitution,
    # so generate_environment_bible reaches the "FilmConstitution not found"
    # branch rather than the "Script artifact not found" branch.
    from datetime import UTC, datetime

    from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata
    from film_pipeline.schemas.script import Script

    assert rt.services is not None
    store = rt.services.artifact_store
    script = Script(project_id="bible-env-3", scenes=[])
    meta = ArtifactMetadata(
        artifact_id="script",
        artifact_type=ArtifactType.SCRIPT,
        project_id="bible-env-3",
        phase=FilmPhase("script"),
        version=1,
        status=ArtifactStatus.CANDIDATE,
        parents=[],
        created_by="test",
        created_at=datetime.now(UTC),
    )
    store.save(script, meta)

    result = asyncio.run(
        generate_environment_bible({"environment_id": "studio", "environment_name": "Studio"})
    )
    assert result["ok"] is False
    assert "FilmConstitution not found" in cast(str, result["error"])


def test_generate_camera_bible_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(generate_camera_bible({}))
    assert result["ok"] is False


def test_generate_style_bible_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(generate_style_bible({}))
    assert result["ok"] is False


def test_generate_style_bible_missing_constitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("bible-style-2", "No Constitution")
    rt.set_active("bible-style-2")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(generate_style_bible({}))
    assert result["ok"] is False
    assert "FilmConstitution not found" in cast(str, result["error"])


def test_generate_shot_bible_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(generate_shot_bible({}))
    assert result["ok"] is False


def test_generate_character_bible_requires_character_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = _build_runtime_through_script(tmp_path, "bible-char-1")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(generate_character_bible({}))
    assert result["ok"] is False
    assert "character_id is required" in cast(str, result["error"])


def test_generate_character_bible_missing_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("bible-char-2", "No Script")
    rt.set_active("bible-char-2")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(generate_character_bible({"character_id": "leo"}))
    assert result["ok"] is False
    assert "Script artifact not found" in cast(str, result["error"])


def test_generate_character_bible_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = _build_runtime_through_script(tmp_path, "bible-char-3")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(generate_character_bible({"character_id": "leo", "character_name": "Leo"}))
    assert result["ok"] is True
    assert result["character_id"] == "leo"
    assert result["identity_block"]
    active = rt.get_active()
    assert active is not None
    assert active["character_bible_ref"] == result["character_bible_ref"]


def test_generate_environment_bible_requires_environment_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = _build_runtime_through_script(tmp_path, "bible-env-1")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(generate_environment_bible({}))
    assert result["ok"] is False
    assert "environment_id is required" in cast(str, result["error"])


def test_generate_environment_bible_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = _build_runtime_through_script(tmp_path, "bible-env-2")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(
        generate_environment_bible({"environment_id": "studio", "environment_name": "Studio"})
    )
    assert result["ok"] is True
    assert result["environment_id"] == "studio"
    assert result["locked_prompt_block"]


def test_generate_camera_bible_missing_constitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("bible-camera-1", "No Constitution")
    rt.set_active("bible-camera-1")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(generate_camera_bible({}))
    assert result["ok"] is False
    assert "FilmConstitution not found" in cast(str, result["error"])


def test_generate_camera_bible_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = _build_runtime_through_script(tmp_path, "bible-camera-2")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(generate_camera_bible({}))
    assert result["ok"] is True
    assert cast(int, result["profiles"]) >= 1


def test_generate_style_bible_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = _build_runtime_through_script(tmp_path, "bible-style-1")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(generate_style_bible({}))
    assert result["ok"] is True
    assert result["palette"]


def test_generate_shot_bible_missing_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("bible-shot-1", "No Refs")
    rt.set_active("bible-shot-1")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(generate_shot_bible({}))
    assert result["ok"] is False
    assert "Required artifacts not found" in cast(str, result["error"])


def test_generate_shot_bible_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("bible-shot-2", "Shot Bible")
    rt.set_active("bible-shot-2")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    state = rt._run_phase_node(state, "constitution")
    state = rt._run_phase_node(state, "development")
    state = rt._run_phase_node(state, "script")
    state = rt._run_phase_node(state, "visual_dev")
    rt.projects["bible-shot-2"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(generate_shot_bible({}))
    assert result["ok"] is True
    assert cast(int, result["shot_count"]) >= 1
    active = rt.get_active()
    assert active is not None
    assert active["shot_matrix_ref"] == result["shot_matrix_ref"]
