"""Tests for command palette suggestion/option/help/validation builders."""

from __future__ import annotations

from film_pipeline.tui.view_models import (
    build_command_help_rows,
    build_command_options,
    build_command_suggestions,
    build_command_validation,
    build_matrix_rows,
    complete_command_prefix,
    filter_command_suggestions,
)
from tests.unit.tui.conftest import RecordingGateway


def test_command_suggestions_include_live_navigation_and_fix_commands() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")
    artifacts = gateway.list_artifacts("field-message")
    matrix_rows = build_matrix_rows(artifacts, validation)

    suggestions = build_command_suggestions(
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=artifacts,
        matrix_rows=matrix_rows,
    )

    commands = [str(row["command"]) for row in suggestions]
    assert "open guide" in commands
    assert "phase script" in commands
    assert "project field-message" in commands
    assert "projects production" in commands
    assert "projects test" in commands
    assert "approve" in commands
    assert "confirm approve" in commands
    assert "fix SC_004" in commands
    assert "artifact script" in commands
    assert "scene SC_007" in commands


def test_command_options_collect_selectable_ids() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")

    options = build_command_options(
        projects=gateway.list_projects(),
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=gateway.list_artifacts("field-message"),
        providers=gateway.list_provider_status(),
    )

    assert options.project_ids == ["field-message"]
    assert options.project_kinds == ["production", "test", "all"]
    assert "script" in options.phases
    assert options.artifact_ids == ["scene_matrix", "script"]
    assert options.scene_ids == ["SC_004", "SC_007"]
    assert options.validator_ids == ["dialogue-voice", "payoff", "script-structure"]
    assert options.provider_ids == ["imagen", "seedance"]


def test_command_options_collect_scene_ids_from_artifact_summaries() -> None:
    options = build_command_options(
        projects=[],
        dashboard=None,
        validation=None,
        artifacts=[
            {
                "artifact_id": "shot_matrix",
                "artifact_type": "matrix",
                "phase": "shot_bible",
                "scene_ids": ["SC_010"],
            }
        ],
        providers=[],
    )

    assert options.scene_ids == ["SC_010"]


def test_command_help_rows_include_live_argument_values() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")
    options = build_command_options(
        projects=gateway.list_projects(),
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=gateway.list_artifacts("field-message"),
        providers=gateway.list_provider_status(),
    )

    help_rows = build_command_help_rows(options)

    by_command = {str(row["command"]): row for row in help_rows}
    assert "field-message" in str(by_command["project <project_id>"]["values"])
    assert "production" in str(by_command["projects <production|test|all>"]["values"])
    assert "script" in str(by_command["artifact <artifact_id>"]["values"])
    assert "script" in str(by_command["asset review <artifact_id>"]["values"])
    assert "script" in str(by_command["asset change <artifact_id> | <note>"]["values"])
    assert "SC_004" in str(by_command["scene <scene_id>"]["values"])
    assert "dialogue-voice" in str(by_command["validator <validator_id>"]["values"])
    assert by_command["create <project_id> | <title> | <idea>"]["purpose"]


def test_command_validation_accepts_known_values_and_rejects_unknown_values() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")
    artifacts = gateway.list_artifacts("field-message")
    matrix_rows = build_matrix_rows(artifacts, validation)
    suggestions = build_command_suggestions(
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=artifacts,
        matrix_rows=matrix_rows,
    )
    options = build_command_options(
        projects=gateway.list_projects(),
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=artifacts,
        providers=gateway.list_provider_status(),
    )

    assert build_command_validation("artifact script", options, suggestions).status == "ready"
    assert build_command_validation("asset review script", options, suggestions).status == "ready"
    assert (
        build_command_validation(
            "asset change script | Sharpen the visual beat.", options, suggestions
        ).status
        == "ready"
    )
    assert (
        build_command_validation(
            "asset extend script | Add one image beat.", options, suggestions
        ).status
        == "ready"
    )
    assert build_command_validation("project field-message", options, suggestions).status == "ready"
    assert build_command_validation("projects test", options, suggestions).status == "ready"
    assert build_command_validation("scene SC_004", options, suggestions).status == "ready"
    assert (
        build_command_validation("create film | Film | Idea", options, suggestions).status
        == "ready"
    )
    unknown = build_command_validation("artifact missing", options, suggestions)
    unknown_asset = build_command_validation("asset review missing", options, suggestions)
    unknown_project = build_command_validation("project missing", options, suggestions)
    bad_pivot = build_command_validation("matrix pivot mood", options, suggestions)
    partial = build_command_validation("artifact sc", options, suggestions)

    assert unknown.status == "unknown"
    assert "Unknown artifact" in unknown.message
    assert unknown_asset.status == "unknown"
    assert "Unknown asset review" in unknown_asset.message
    assert unknown_project.status == "unknown"
    assert "Unknown project" in unknown_project.message
    assert bad_pivot.status == "unknown"
    assert "Unknown matrix pivot" in bad_pivot.message
    assert partial.status == "incomplete"
    assert partial.completion == "artifact scene_matrix"


def test_command_validation_guides_incomplete_and_pipe_commands() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")
    artifacts = gateway.list_artifacts("field-message")
    matrix_rows = build_matrix_rows(artifacts, validation)
    suggestions = build_command_suggestions(
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=artifacts,
        matrix_rows=matrix_rows,
    )
    options = build_command_options(
        projects=gateway.list_projects(),
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=artifacts,
        providers=gateway.list_provider_status(),
    )

    assert build_command_validation("", options, suggestions).completion == "open review"
    assert build_command_validation("create", options, suggestions).status == "incomplete"
    assert build_command_validation("asset", options, suggestions).status == "incomplete"
    assert (
        build_command_validation("asset change script | <note>", options, suggestions).status
        == "incomplete"
    )
    assert (
        build_command_validation("create <project_id> | Film | Idea", options, suggestions).status
        == "incomplete"
    )
    assert build_command_validation("phase", options, suggestions).completion == "phase script"
    assert build_command_validation("validator", options, suggestions).completion.startswith(
        "validator "
    )
    assert build_command_validation("matrix", options, suggestions).status == "ready"
    assert build_command_validation("matr", options, suggestions).completion == "matrix"
    assert (
        build_command_validation("matrix pivot", options, suggestions).completion
        == "matrix pivot status"
    )
    assert build_command_validation("matrix blocking", options, suggestions).status == "ready"
    assert build_command_validation("comment", options, suggestions).status == "incomplete"
    assert (
        build_command_validation("comment SC_004 | keep this quiet", options, suggestions).status
        == "ready"
    )
    assert (
        build_command_validation("draft SC_004 | <note>", options, suggestions).status
        == "incomplete"
    )
    assert build_command_validation("review issue", options, suggestions).status == "incomplete"
    assert build_command_validation("review issue SC_004", options, suggestions).status == "ready"
    assert build_command_validation("appr", options, suggestions).completion == "approve"
    assert build_command_validation("nonsense", options, suggestions).status == "unknown"


def test_command_suggestions_filter_and_complete_prefixes() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")
    artifacts = gateway.list_artifacts("field-message")
    suggestions = build_command_suggestions(
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=artifacts,
        matrix_rows=build_matrix_rows(artifacts, validation),
    )

    filtered = filter_command_suggestions(suggestions, "fix")

    assert [row["command"] for row in filtered] == ["fix SC_004", "fix SC_007"]
    assert complete_command_prefix("art", suggestions) == "artifact script"
