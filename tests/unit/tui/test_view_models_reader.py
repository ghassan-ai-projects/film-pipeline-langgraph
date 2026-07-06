"""Tests for the reader view builders."""

from __future__ import annotations

from film_pipeline.app.services.models import (
    ArtifactDetail,
    DashboardSummary,
    OperatorCommentRequest,
)
from film_pipeline.tui.view_models import (
    build_artifact_reader,
    build_overview_reader,
    validation_issue_rows,
)
from tests.unit.tui.conftest import RecordingGateway


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
    assert compact_reader.body.splitlines() == [
        "title: Field Message",
        "shots: 2 item(s)",
        "owner: 1 field(s)",
        "empty: None",
    ]


def test_validation_issue_rows_with_filters() -> None:
    validation = RecordingGateway().get_validation_workspace("field-message")

    all_rows = validation_issue_rows(validation)
    blocking_rows = validation_issue_rows(validation, severity="blocking")
    dialogue_rows = validation_issue_rows(validation, validator_id="dialogue-voice")

    assert len(all_rows) >= 2
    assert blocking_rows == dialogue_rows
    assert blocking_rows[0]["scene"] == "SC_004"
    assert validation_issue_rows(None) == []


def _dashboard(**overrides: object) -> DashboardSummary:
    values: dict[str, object] = {
        "project_id": "field-message",
        "title": "Field Message",
        "slug": "field-message",
        "current_phase": "script",
        "runtime_mode": "mock",
        "workflow_mode": "manual",
        "status": "awaiting_review",
        "next_action": "present_review_package",
        "route_reason": "script complete",
        "idea": "A courier hears tomorrow's warning today.",
    }
    values.update(overrides)
    return DashboardSummary(**values)  # type: ignore[arg-type]


def test_overview_reader_shows_idea_phase_and_next_action() -> None:
    overview = build_overview_reader(
        _dashboard(), stage_explanation="Write and review the screenplay."
    )

    assert overview.title == "Field Message"
    assert overview.subtitle == "project field-message"
    assert "A courier hears tomorrow's warning today." in overview.body
    assert "Now:  script — awaiting_review" in overview.body
    assert "Write and review the screenplay." in overview.body
    assert "Next: present_review_package" in overview.body
    assert "Why:  script complete" in overview.body
    assert overview.metadata["mode"] == "manual/mock"


def test_overview_reader_flags_blockers_and_text_only_policy() -> None:
    overview = build_overview_reader(
        _dashboard(generation_policy="text_only"),
        blocking_issues=2,
    )

    assert "Blocked by 2 validation issue(s)" in overview.body
    assert overview.metadata["policy"] == "text only (no generated media)"
