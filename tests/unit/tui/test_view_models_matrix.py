"""Tests for matrix/scene/phase-detail view model builders."""

from __future__ import annotations

from film_pipeline.app.services.models import OperatorCommentRequest
from film_pipeline.tui.view_models import (
    build_matrix_impact,
    build_matrix_pivot_rows,
    build_matrix_rows,
    build_phase_detail,
    build_scene_rows,
    filter_matrix_rows,
)
from tests.unit.tui.conftest import RecordingGateway


def test_phase_detail_summarizes_current_graph_position() -> None:
    gateway = RecordingGateway()
    dashboard = gateway.get_dashboard("field-message")
    validation = gateway.get_validation_workspace("field-message")

    detail = build_phase_detail(
        "script",
        dashboard=dashboard,
        artifacts=gateway.list_artifacts("field-message"),
        validation=validation,
    )

    assert detail.phase == "script"
    assert detail.status == "current"
    assert len(detail.artifacts) == 2
    assert "Dialogue voice drift in scene 4." in detail.blockers
    assert "approve" in detail.suggested_commands
    assert "artifact script" in detail.suggested_commands


def test_matrix_rows_merge_artifacts_and_validation_issues() -> None:
    gateway = RecordingGateway()
    artifacts = gateway.list_artifacts("field-message")
    validation = gateway.get_validation_workspace("field-message")

    rows = build_matrix_rows(artifacts, validation)

    script = next(row for row in rows if row["target"] == "script")
    scene_issue = next(row for row in rows if row["target"] == "SC_007")
    assert script["validation"] == "blocking: Dialogue voice drift in scene 4."
    assert script["action"] == "review issues"
    assert scene_issue["kind"] == "validation_issue"
    assert scene_issue["action"] == "request fix"


def test_matrix_pivot_rows_group_by_status_phase_and_validation() -> None:
    gateway = RecordingGateway()
    rows = build_matrix_rows(
        gateway.list_artifacts("field-message"),
        gateway.get_validation_workspace("field-message"),
    )

    by_status = build_matrix_pivot_rows(rows, "status")
    by_phase = build_matrix_pivot_rows(rows, "phase")
    by_validation = build_matrix_pivot_rows(rows, "validation")

    assert any(row["value"] == "candidate" and row["rows"] == 2 for row in by_status)
    assert by_phase[0]["value"] == "script"
    assert any(row["value"] == "blocking" for row in by_validation)
    assert any(row["command"] == "matrix status:candidate" for row in by_status)


def test_matrix_filter_supports_operator_queries() -> None:
    gateway = RecordingGateway()
    rows = build_matrix_rows(
        gateway.list_artifacts("field-message"),
        gateway.get_validation_workspace("field-message"),
    )

    blocking = filter_matrix_rows(rows, "blocking")
    warning_scene = filter_matrix_rows(rows, "scene:SC_007 warning")

    assert [row["target"] for row in blocking] == ["script"]
    assert [row["target"] for row in warning_scene] == ["SC_007"]


def test_matrix_impact_links_comments_and_validation() -> None:
    gateway = RecordingGateway()
    comment = gateway.add_operator_comment(
        OperatorCommentRequest(
            target_type="scene",
            target_id="SC_007",
            phase="script",
            body="Payoff needs to be more visual.",
        ),
        "field-message",
    )
    rows = build_matrix_rows(
        gateway.list_artifacts("field-message"),
        gateway.get_validation_workspace("field-message"),
    )
    row = next(row for row in rows if row["target"] == "SC_007")

    impact = build_matrix_impact(
        row,
        comments=[comment],
        validation=gateway.get_validation_workspace("field-message"),
    )

    assert impact.target_id == "SC_007"
    assert impact.linked_comments == [comment]
    assert impact.linked_validation[0]["message"] == "Payoff is unclear."
    assert "request targeted revision" in impact.suggested_actions


def test_scene_rows_extract_scene_targets_from_matrix() -> None:
    gateway = RecordingGateway()
    rows = build_matrix_rows(
        gateway.list_artifacts("field-message"),
        gateway.get_validation_workspace("field-message"),
    )

    scenes = build_scene_rows(rows)

    assert scenes == [
        {
            "scene": "SC_007",
            "phase": "script",
            "status": "warning",
            "validation": "Payoff is unclear.",
            "action": "request fix",
        }
    ]


def test_scene_rows_include_artifact_scene_ids_without_validation_issues() -> None:
    artifacts = [
        {
            "artifact_id": "script",
            "artifact_type": "script",
            "phase": "script",
            "version": 1,
            "status": "candidate",
            "scene_ids": ["SC_001", "SC_002"],
        }
    ]

    scenes = build_scene_rows([], artifacts=artifacts)

    assert scenes == [
        {
            "scene": "SC_001",
            "phase": "script",
            "status": "candidate",
            "validation": "passing/unknown",
            "action": "open scene",
        },
        {
            "scene": "SC_002",
            "phase": "script",
            "status": "candidate",
            "validation": "passing/unknown",
            "action": "open scene",
        },
    ]
