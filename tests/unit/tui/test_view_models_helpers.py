"""Tests for cockpit view-model helper utilities."""

from __future__ import annotations

from film_pipeline.app.services.models import DashboardSummary, ValidationWorkspace
from film_pipeline.tui.view_models.helpers import (
    _all_issues,
    _dedupe_command_rows,
    _issue_label,
    _issue_target,
    _phase_blockers,
    _preview_values,
    _row_matches_token,
    _row_text,
    _scene_ids_from_summary,
    _severity_rank,
    _target_type_for_issue,
    _validation_bucket,
)


def test_all_issues_merges_blocking_and_non_blocking() -> None:
    validation = ValidationWorkspace(
        project_id="p1",
        phase="script",
        source="test",
        reports=[],
        blocking_issues=[{"message": "blocking"}],
        non_blocking_issues=[{"message": "warning"}],
    )
    issues = _all_issues(validation)
    assert len(issues) == 2


def test_scene_ids_from_summary_extracts_ids() -> None:
    artifact: dict[str, object] = {
        "scene_id": "SC_001",
        "scene_ids": ["SC_002"],
        "body": {"scenes": [{"scene_id": "SC_003"}]},
    }
    assert _scene_ids_from_summary(artifact) == ["SC_001", "SC_002", "SC_003"]


def test_phase_blockers_includes_dashboard_blocked_actions() -> None:
    dashboard = DashboardSummary(
        project_id="p1",
        title="T",
        slug="t",
        current_phase="script",
        runtime_mode="mock",
        workflow_mode="manual",
        status="awaiting_review",
        next_action="review",
        route_reason="",
        blocked_actions=[{"action": "generation", "reason": "approval required"}],
    )
    blockers = _phase_blockers("script", dashboard, None)
    assert any("approval required" in b for b in blockers)


def test_dedupe_command_rows_removes_duplicate_commands() -> None:
    rows: list[dict[str, object]] = [
        {"command": "approve"},
        {"command": "approve"},
        {"command": "revise"},
    ]
    assert _dedupe_command_rows(rows) == [{"command": "approve"}, {"command": "revise"}]


def test_issue_target_prefers_artifact_id() -> None:
    assert _issue_target({"artifact_id": "script", "scene_id": "SC_001"}) == "script"


def test_issue_target_falls_back_to_scene_id() -> None:
    assert _issue_target({"scene_id": "SC_001"}) == "SC_001"


def test_severity_rank_orders_blocking_first() -> None:
    assert _severity_rank("blocking") < _severity_rank("warning")


def test_target_type_for_issue_detects_scene() -> None:
    assert _target_type_for_issue({"scene_id": "SC_001"}, "SC_001") == "scene"


def test_target_type_for_issue_detects_asset() -> None:
    assert _target_type_for_issue({"asset_id": "a1"}, "a1") == "asset"


def test_validation_bucket_classifies_blocking() -> None:
    assert _validation_bucket("blocking failure") == "blocking"


def test_validation_bucket_classifies_warning() -> None:
    assert _validation_bucket("warn") == "warning"


def test_issue_label_shows_first_blocking_message() -> None:
    issues = [
        {"severity": "blocking", "message": "voice drift"},
        {"severity": "warning", "message": "payoff unclear"},
    ]
    assert "voice drift" in _issue_label(issues)


def test_preview_values_truncates() -> None:
    values = ["a", "b", "c", "d", "e", "f", "g"]
    assert "+1 more" in _preview_values(values, limit=6)


def test_row_text_joins_values() -> None:
    assert "hello" in _row_text({"a": "hello", "b": "world"})


def test_row_matches_token_detects_blocking() -> None:
    row: dict[str, object] = {"status": "blocking failure"}
    assert _row_matches_token(row, "blocked") is True


def test_row_matches_token_key_filter() -> None:
    row: dict[str, object] = {"phase": "script"}
    assert _row_matches_token(row, "phase:scri") is True
