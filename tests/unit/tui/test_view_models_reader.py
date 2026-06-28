"""Tests for artifact reader, selection, and review/validation view model builders."""

from __future__ import annotations

from film_pipeline.app.services.models import ArtifactDetail, OperatorCommentRequest
from film_pipeline.tui.view_models import (
    build_artifact_reader,
    build_asset_action_rows,
    build_comment_thread_rows,
    build_reader_index_rows,
    build_reader_link_rows,
    build_review_checklist_rows,
    build_review_issue_rows,
    build_validation_fix_suggestions,
    build_validation_groups,
    format_fix_draft,
    format_selection_detail,
    format_targeted_revision_note,
    selection_from_row,
    validation_issue_rows,
)
from tests.unit.tui.conftest import RecordingGateway


def test_selection_and_targeted_revision_note_preserve_context() -> None:
    selection = selection_from_row(
        "scene_table",
        {
            "scene": "SC_007",
            "phase": "script",
            "status": "warning",
            "validation": "Payoff is unclear.",
        },
    )

    note = format_targeted_revision_note(selection, "Make the payoff emotionally clearer.")

    assert selection.target_type == "scene"
    assert selection.target_id == "SC_007"
    assert note == (
        "[target_type=scene target_id=SC_007 phase=script] Make the payoff emotionally clearer."
    )


def test_artifact_reader_builds_outline_body_and_links() -> None:
    gateway = RecordingGateway()
    comment = gateway.add_operator_comment(
        OperatorCommentRequest(
            target_type="scene",
            target_id="SC_004",
            phase="script",
            body="Make the station feel colder.",
        ),
        "field-message",
    )
    artifact = gateway.inspect_artifact("script", "script", 4, "field-message")

    reader = build_artifact_reader(
        artifact,
        comments=[comment],
        validation=gateway.get_validation_workspace("field-message"),
        scene_id="SC_004",
    )

    assert reader.title == "INT. STATION - DAWN"
    assert reader.metadata["scene_id"] == "SC_004"
    assert "Mara waits beside the locked platform." in reader.body
    assert "MARA" in reader.body
    assert reader.linked_comments == [comment]
    assert reader.linked_validation[0]["message"] == "Dialogue voice drift in scene 4."


def test_artifact_reader_renders_matrix_scene_camera_and_assets() -> None:
    artifact = RecordingGateway().inspect_artifact("scene_matrix", "script", 2, "field-message")

    reader = build_artifact_reader(artifact, comments=[], validation=None, scene_id="SC_004")

    assert reader.metadata["scene_id"] == "SC_004"
    assert "camera_profile: slow push-in" in reader.body
    assert "camera_movement: dolly forward from wide to close" in reader.body
    assert "assets: ref_station_platform, prop_warning_note" in reader.body
    assert "references: style_noir_dawn" in reader.body


def test_reader_index_and_link_rows_make_artifact_navigable() -> None:
    gateway = RecordingGateway()
    comment = gateway.add_operator_comment(
        OperatorCommentRequest(
            target_type="scene",
            target_id="SC_004",
            phase="script",
            body="Make the station feel colder.",
        ),
        "field-message",
    )
    artifact = gateway.inspect_artifact("script", "script", 4, "field-message")
    reader = build_artifact_reader(
        artifact,
        comments=[comment],
        validation=gateway.get_validation_workspace("field-message"),
        scene_id="SC_004",
    )

    index_rows = build_reader_index_rows(artifact)
    link_rows = build_reader_link_rows(reader)

    assert index_rows == [
        {
            "order": 1,
            "target_id": "SC_004",
            "target_type": "scene",
            "heading": "INT. STATION - DAWN",
            "command": "scene SC_004",
        }
    ]
    assert link_rows[0]["kind"] == "validation"
    assert link_rows[0]["command"] == "fix SC_004"
    assert link_rows[1]["kind"] == "comment"
    assert link_rows[1]["command"] == "thread SC_004"


def test_asset_action_rows_make_artifacts_actionable() -> None:
    rows = build_asset_action_rows(RecordingGateway().list_artifacts("field-message"))

    script_actions = [row for row in rows if row["artifact_id"] == "script"]
    assert [row["action"] for row in script_actions] == ["review", "change", "extend"]
    assert script_actions[0]["command"] == "asset review script"
    assert script_actions[1]["command"] == "asset change script | <note>"
    assert script_actions[2]["command"] == "asset extend script | <note>"


def test_artifact_reader_renders_text_treatment_scene_list_and_compact_bodies() -> None:
    text_artifact = ArtifactDetail(
        artifact_id="logline",
        artifact_type="text",
        phase="intake",
        version=1,
        status="candidate",
        body={"text": "A courier hears tomorrow's warning today.", "created_by": "agent"},
    )
    treatment_artifact = ArtifactDetail(
        artifact_id="treatment",
        artifact_type="treatment",
        phase="development",
        version=2,
        status="candidate",
        body={
            "treatment": {"text": "Act one opens at the abandoned platform."},
            "validation_refs": ["validation:1"],
        },
    )
    scene_list_artifact = ArtifactDetail(
        artifact_id="scene_list",
        artifact_type="scene_list",
        phase="script",
        version=1,
        status="candidate",
        body={
            "scene_list": {
                "scenes": [
                    {"scene_id": "SC_001", "dramatic_function": "Arrival"},
                    {"dramatic_function": "Missing id fallback"},
                ]
            },
            "approval_ref": "approval:1",
        },
    )
    compact_artifact = ArtifactDetail(
        artifact_id="metadata",
        artifact_type="metadata",
        phase="delivery",
        version=1,
        status="candidate",
        body={
            "title": "Field Message",
            "shots": [1, 2],
            "owner": {"agent": "delivery"},
            "empty": None,
        },
    )

    text_reader = build_artifact_reader(text_artifact, comments=[], validation=None)
    treatment_reader = build_artifact_reader(treatment_artifact, comments=[], validation=None)
    scene_reader = build_artifact_reader(scene_list_artifact, comments=[], validation=None)
    compact_reader = build_artifact_reader(compact_artifact, comments=[], validation=None)

    assert text_reader.body == "A courier hears tomorrow's warning today."
    assert text_reader.metadata["created_by"] == "agent"
    assert treatment_reader.body == "Act one opens at the abandoned platform."
    assert treatment_reader.metadata["validation_refs"] == ["validation:1"]
    assert scene_reader.outline == ["SC_001: Arrival", "?: Missing id fallback"]
    assert build_reader_index_rows(scene_list_artifact)[0]["command"] == "scene SC_001"
    assert compact_reader.body.splitlines() == [
        "title: Field Message",
        "shots: 2 item(s)",
        "owner: 1 field(s)",
        "empty: None",
    ]


def test_selection_from_row_covers_tui_table_sources() -> None:
    rows: dict[str, dict[str, object]] = {
        "asset_table": {"artifact_id": "script", "phase": "script"},
        "asset_table_manifest": {"asset_id": "clip_1", "scene_id": "SC_004", "shot_id": "shot_1"},
        "asset_action_table": {"artifact_id": "script", "action": "review", "phase": "script"},
        "dashboard_kpi_table": {"metric": "blockers"},
        "dashboard_action_table": {"action": "approve"},
        "project_table": {"project": "field-message", "kind": "production"},
        "guide_table": {"step": 3, "goal": "Inspect assets"},
        "review_checklist_table": {"check": "read script"},
        "review_issue_table": {"target_type": "scene", "target_id": "SC_004"},
        "comment_thread_table": {"target_type": "scene", "target_id": "SC_004"},
        "validation_table": {"target": "SC_004", "phase": "script"},
        "validation_group_table": {"validator_id": "dialogue-voice"},
        "validation_fix_table": {"target_type": "scene", "target_id": "SC_004"},
        "matrix_table": {"kind": "artifact", "target": "script", "phase": "script"},
        "matrix_pivot_table": {"value": "blocking"},
        "graph_table": {"phase": "script"},
        "graph_artifact_table": {"artifact_id": "script", "phase": "script"},
        "command_suggestion_table": {"command": "fix SC_004"},
        "reader_index_table": {"target_type": "scene", "target_id": "SC_004"},
        "reader_link_table": {"kind": "validation", "target_id": "SC_004"},
        "provider_table": {"provider_id": "imagen"},
        "checkpoint_table": {"checkpoint_id": "checkpoint:1", "phase": "script"},
        "unknown_table": {"first": "fallback"},
    }

    selections = {source: selection_from_row(source, row) for source, row in rows.items()}

    assert selections["asset_table"].target_type == "artifact"
    assert selection_from_row("asset_table", rows["asset_table_manifest"]).target_type == "asset"
    assert selection_from_row("asset_table", rows["asset_table_manifest"]).target_id == "clip_1"
    assert selections["asset_action_table"].target_type == "asset_action"
    assert selections["dashboard_kpi_table"].target_id == "blockers"
    assert selections["dashboard_action_table"].target_type == "dashboard_action"
    assert selections["project_table"].target_type == "project"
    assert selections["guide_table"].target_type == "guide_step"
    assert selections["review_checklist_table"].target_id == "read script"
    assert selections["review_issue_table"].target_type == "scene"
    assert selections["comment_thread_table"].target_id == "SC_004"
    assert selections["validation_table"].target_type == "validation_issue"
    assert selections["validation_group_table"].target_type == "validator"
    assert selections["validation_fix_table"].target_type == "scene"
    assert selections["matrix_table"].target_type == "artifact"
    assert selections["matrix_pivot_table"].target_type == "matrix_pivot"
    assert selections["graph_table"].target_type == "graph_phase"
    assert selections["graph_artifact_table"].target_id == "script"
    assert selections["command_suggestion_table"].target_type == "command"
    assert selections["reader_index_table"].target_type == "scene"
    assert selections["reader_link_table"].target_type == "validation"
    assert selections["provider_table"].target_id == "imagen"
    assert selections["checkpoint_table"].phase == "script"
    assert selections["unknown_table"].target_id == "fallback"
    assert "comment script | <what you want changed>" in format_selection_detail(
        selections["asset_table"]
    )
    assert format_targeted_revision_note(None, "  no selection  ") == "no selection"


def test_validation_groups_and_fixes_turn_issues_into_actions() -> None:
    validation = RecordingGateway().get_validation_workspace("field-message")

    groups = build_validation_groups(validation)
    suggestions = build_validation_fix_suggestions(validation)
    blocking_rows = validation_issue_rows(validation, severity="blocking")
    dialogue_rows = validation_issue_rows(validation, validator_id="dialogue-voice")

    assert groups[0].validator_id == "dialogue-voice"
    assert groups[0].severity == "blocking"
    assert groups[0].count == 1
    assert groups[0].suggested_action == "fix SC_004"
    assert suggestions[0].target_id == "SC_004"
    assert suggestions[0].target_type == "scene"
    assert suggestions[0].command == "fix SC_004"
    assert format_fix_draft(suggestions[0]) == ("dialogue-voice: Dialogue voice drift in scene 4.")
    assert blocking_rows == dialogue_rows
    assert blocking_rows[0]["scene"] == "SC_004"


def test_review_models_build_checklist_issues_and_threads() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")
    review = gateway.get_review_workspace("field-message")
    comment = gateway.add_operator_comment(
        OperatorCommentRequest(
            target_type="scene",
            target_id="SC_004",
            phase="script",
            body="Make the voice more consistent.",
        ),
        "field-message",
    )

    checklist = build_review_checklist_rows(review, validation, [comment])
    issues = build_review_issue_rows(review, validation)
    threads = build_comment_thread_rows([comment])

    assert checklist[0]["check"] == "candidate_artifacts"
    assert checklist[1]["status"] == "blocked"
    assert issues[0]["target_id"] == "SC_004"
    assert issues[0]["command"] == "scene SC_004"
    assert any(row["severity"] == "warning" and row["target_id"] == "SC_007" for row in issues)
    assert threads == [
        {
            "target_id": "SC_004",
            "target_type": "scene",
            "open": 1,
            "latest": "Make the voice more consistent.",
            "updated": "2026-06-24T10:02:00",
            "command": "thread SC_004",
        }
    ]
