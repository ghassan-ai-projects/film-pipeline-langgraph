"""Unit tests for film_pipeline.mcp.tools.bibles."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from film_pipeline.mcp.tools import (
    generate_camera_bible,
    generate_character_bible,
    generate_environment_bible,
    generate_shot_bible,
    generate_style_bible,
)
from film_pipeline.mcp.tools.bibles import _extract_script_text
from film_pipeline.studio.mock_responses import default_mock_responses
from film_pipeline.studio.runtime import StudioRuntime


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

    from film_pipeline.schemas.artifact import ArtifactMetadata
    from film_pipeline.schemas.base import ArtifactStatus, ArtifactType, FilmPhase
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


def test_saved_character_bible_is_about_the_requested_character(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The persisted artifact's identity must be the request, not the mock's.

    A registered mock is static and cannot interpolate the requested character,
    so nothing stopped a mock-mode run from persisting a bible identified as the
    mock's subject while the response echoed the request. The response asserted
    the right id; the artifact on disk did not. Two different characters
    previously both persisted ``character_id: "lead"``.
    """
    import json

    project_id = "bible-char-identity"
    rt = _build_runtime_through_script(tmp_path, project_id)
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    saved: list[str] = []
    for character_id in ("hero", "villain"):
        result = asyncio.run(
            generate_character_bible({"character_id": character_id, "character_name": character_id})
        )
        assert result["ok"] is True
        assert result["character_id"] == character_id

        versions = sorted(
            (
                tmp_path
                / "runtime"
                / project_id
                / "artifacts"
                / "04-visual-dev"
                / "character_bible"
                / "versions"
            ).glob("v*.json")
        )
        envelope = json.loads(versions[-1].read_text())
        body = envelope.get("payload", envelope)
        saved.append(str(body.get("character_id")))

    assert saved == ["hero", "villain"], (
        f"each character's saved bible must be identified as that character; found {saved}"
    )


def test_saved_environment_bible_is_about_the_requested_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same rule for the environment bible, whose id the response also echoes."""
    import json

    project_id = "bible-env-identity"
    rt = _build_runtime_through_script(tmp_path, project_id)
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(
        generate_environment_bible({"environment_id": "neon_market", "environment_name": "Neon"})
    )
    assert result["ok"] is True

    versions = sorted(
        (
            tmp_path
            / "runtime"
            / project_id
            / "artifacts"
            / "04-visual-dev"
            / "environment_bible"
            / "versions"
        ).glob("v*.json")
    )
    envelope = json.loads(versions[-1].read_text())
    body = envelope.get("payload", envelope)
    assert body.get("environment_id") == "neon_market", (
        "the saved environment bible must be identified as the requested "
        f"environment; found {body.get('environment_id')!r}"
    )


def test_generate_character_bible_creates_new_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = "bible-char-version"
    rt = _build_runtime_through_script(tmp_path, project_id)
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result1 = asyncio.run(
        generate_character_bible({"character_id": "leo", "character_name": "Leo"})
    )
    assert result1["ok"] is True

    result2 = asyncio.run(
        generate_character_bible({"character_id": "leo", "character_name": "Leo"})
    )
    assert result2["ok"] is True

    assert rt.services is not None
    store = rt.services.artifact_store
    meta1 = store.load_metadata(project_id, "visual_dev", "character_bible", 1)
    meta2 = store.load_metadata(project_id, "visual_dev", "character_bible", 2)
    assert meta1.version == 1
    assert meta2.version == 2


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
    # Pinned rather than `>= 1`: this tool used to fall back to a hand-written
    # single-row matrix, and now takes the same registered mock the graph path
    # uses. That swap is a real change in mock output, so the count is asserted
    # and cannot drift silently in either direction.
    mock_rows = default_mock_responses()["shot-design-agent"]["shot_matrix"]["rows"]
    assert cast(int, result["shot_count"]) == len(mock_rows)
    assert len(mock_rows) > 1
    active = rt.get_active()
    assert active is not None
    assert active["shot_matrix_ref"] == result["shot_matrix_ref"]


def test_shot_bible_reports_success_with_a_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The happy path still returns both promised artifacts, unwarned."""
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("bible-shot-ok", "Shot Bible")
    rt.set_active("bible-shot-ok")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    for phase in ("constitution", "development", "script", "visual_dev"):
        state = rt._run_phase_node(state, phase)
    rt.projects["bible-shot-ok"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(generate_shot_bible({}))

    assert result["ok"] is True
    assert result["continuity_ledger_ref"], "the ledger ref must be present"
    assert "warnings" not in result


def test_shot_bible_flags_a_ledger_that_failed_to_persist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing ledger must not look like an unqualified success.

    `_generate_continuity_ledger` caught every exception and returned None, so a
    ledger that failed to persist was indistinguishable from one that was never
    needed: the tool still answered `ok: True` with a null ref, while its own
    docstring promises "MasterFilmMatrix + ContinuityLedger". The matrix is still
    the deliverable, so the call stays non-fatal — but it now logs the failure and
    names it in the response.
    """
    from film_pipeline.mcp.tools.bibles import shot as shot_module

    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("bible-shot-fail", "Shot Bible")
    rt.set_active("bible-shot-fail")
    state = rt._run_phase_node(rt.get_active() or {}, "intake")
    for phase in ("constitution", "development", "script", "visual_dev"):
        state = rt._run_phase_node(state, phase)
    rt.projects["bible-shot-fail"] = state
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    def _explode(*args: object, **kwargs: object) -> str:
        raise RuntimeError("simulated storage failure")

    monkeypatch.setattr(shot_module, "_persist_continuity_ledger", _explode)

    result = asyncio.run(generate_shot_bible({}))

    assert result["ok"] is True, "the matrix is still the deliverable"
    assert result["shot_matrix_ref"], "the matrix must still be persisted"
    assert result["continuity_ledger_ref"] is None
    assert result["warnings"] == ["continuity_ledger_not_persisted"], (
        "the response must name the missing artifact rather than reporting an unqualified success"
    )
