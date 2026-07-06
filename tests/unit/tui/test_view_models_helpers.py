"""Tests for the scene/artifact rendering helper utilities."""

from __future__ import annotations

from film_pipeline.app.services.models import OperatorComment, ValidationWorkspace
from film_pipeline.tui.view_models.helpers import (
    all_issues,
    artifact_outline,
    artifact_scenes,
    comments_for_target,
    compact_dict,
    find_scene,
    issue_target,
    render_artifact_body,
    render_scene,
    scene_outline,
    validation_for_target,
)


def _validation() -> ValidationWorkspace:
    return ValidationWorkspace(
        project_id="p1",
        phase="script",
        source="test",
        reports=[],
        blocking_issues=[{"message": "blocking", "scene_id": "SC_001"}],
        non_blocking_issues=[{"message": "warning", "artifact_id": "script"}],
    )


def test_all_issues_merges_blocking_and_non_blocking() -> None:
    issues = all_issues(_validation())
    assert len(issues) == 2


def test_all_issues_empty_without_validation() -> None:
    assert all_issues(None) == []


def test_issue_target_prefers_artifact_id() -> None:
    assert issue_target({"artifact_id": "script", "scene_id": "SC_001"}) == "script"


def test_issue_target_falls_back_to_scene_id() -> None:
    assert issue_target({"scene_id": "SC_001"}) == "SC_001"


def test_issue_target_empty_when_unknown() -> None:
    assert issue_target({"message": "no target"}) == ""


def test_artifact_scenes_collects_all_containers() -> None:
    body = {
        "scenes": [{"scene_id": "SC_001"}],
        "scene_list": {"scenes": [{"scene_id": "SC_002"}]},
        "rows": [{"scene_id": "SC_003", "shot_id": "shot_1"}],
    }
    ids = [scene.get("scene_id") for scene in artifact_scenes(body)]
    assert ids == ["SC_001", "SC_002", "SC_003"]


def test_find_scene_locates_by_id() -> None:
    body = {"scenes": [{"scene_id": "SC_001"}, {"scene_id": "SC_002", "conflict": "storm"}]}
    scene = find_scene(body, "SC_002")
    assert scene is not None and scene["conflict"] == "storm"
    assert find_scene(body, "SC_404") is None


def test_render_scene_formats_screenplay_text() -> None:
    scene = {
        "scene_id": "SC_001",
        "scene_heading": "INT. STATION - DAWN",
        "action_lines": ["Mara waits by the platform."],
        "dialogue": [{"character_id": "mara", "direction": "softly", "line": "It's here."}],
        "characters": ["mara"],
    }
    text = render_scene(scene)
    assert "INT. STATION - DAWN" in text
    assert "Mara waits by the platform." in text
    assert "MARA" in text
    assert "(softly)" in text
    assert "It's here." in text
    assert "characters: mara" in text
    # Dialogue blocks are separated by a blank line for readability.
    assert "\n\nMARA" in text


def test_render_scene_falls_back_to_compact_dict() -> None:
    assert render_scene({"custom": "value"}) == "custom: value"


def test_render_artifact_body_prefers_text() -> None:
    assert render_artifact_body({"text": "A logline."}) == "A logline."


def test_render_artifact_body_renders_treatment_and_scenes() -> None:
    assert render_artifact_body({"treatment": {"text": "Act one."}}) == "Act one."
    body = {"scenes": [{"scene_id": "SC_001", "scene_heading": "EXT. RIDGE - DAY"}]}
    assert "EXT. RIDGE - DAY" in render_artifact_body(body)


def test_artifact_outline_lists_scenes_and_rows() -> None:
    assert artifact_outline({"scenes": [{"scene_id": "SC_001", "scene_heading": "INT."}]}) == [
        "SC_001: INT."
    ]
    assert artifact_outline({"scene_list": {"scenes": [{"scene_id": "SC_002"}]}}) == ["SC_002: "]
    assert artifact_outline({"rows": [{"scene_id": "SC_003", "shot_id": "shot_1"}]}) == [
        "SC_003: shot_1"
    ]
    assert artifact_outline({"title": "x"}) == ["title"]


def test_scene_outline_includes_key_facts() -> None:
    outline = scene_outline({"scene_id": "SC_001", "conflict": "storm"})
    assert outline == ["SC_001", "conflict: storm"]


def test_comments_for_target_matches_scene_and_artifact() -> None:
    comment = OperatorComment(
        comment_id="c1",
        project_id="p1",
        target_type="scene",
        target_id="SC_001",
        phase="script",
        body="Colder.",
        created_at="2026-06-24T10:00:00",
        resolved=False,
        source="test",
    )
    assert comments_for_target([comment], "SC_001", "script") == [comment]
    assert comments_for_target([comment], "SC_002", "other") == []


def test_validation_for_target_matches_scene_and_artifact() -> None:
    validation = _validation()
    assert validation_for_target(validation, "SC_001", "script") == all_issues(validation)
    assert validation_for_target(validation, "SC_404", "unknown") == []


def test_compact_dict_summarizes_containers() -> None:
    assert compact_dict({"a": 1, "b": [1, 2], "c": {"k": "v"}, "d": None}).splitlines() == [
        "a: 1",
        "b: 2 item(s)",
        "c: 1 field(s)",
        "d: None",
    ]
