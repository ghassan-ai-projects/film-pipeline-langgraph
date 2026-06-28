"""Tests for dashboard-related view model builders."""

from __future__ import annotations

from film_pipeline.app.services.models import DashboardSummary, OperatorCommentRequest
from film_pipeline.tui.view_models import (
    build_command_suggestions,
    build_dashboard_action_rows,
    build_dashboard_kpi_rows,
    build_graph_rows,
    summarize_attention,
)
from tests.unit.tui.conftest import RecordingGateway


def test_graph_rows_mark_current_phase() -> None:
    dashboard = RecordingGateway().get_dashboard("field-message")

    rows = build_graph_rows(dashboard)

    current = [row for row in rows if row["status"] == "current"]
    assert current == [
        {
            "step": 4,
            "phase": "script",
            "status": "current",
            "next_action": "present_review_package",
        }
    ]


def test_dashboard_kpis_and_actions_surface_operator_priorities() -> None:
    gateway = RecordingGateway()
    dashboard = gateway.get_dashboard("field-message")
    validation = gateway.get_validation_workspace("field-message")
    comment = gateway.add_operator_comment(
        OperatorCommentRequest(
            target_type="scene",
            target_id="SC_004",
            phase="script",
            body="Keep the scene quiet.",
        ),
        "field-message",
    )

    kpis = build_dashboard_kpi_rows(
        dashboard,
        validation,
        gateway.list_provider_status(),
        [comment],
    )
    actions = build_dashboard_action_rows(
        dashboard,
        gateway.get_review_workspace("field-message"),
        validation,
    )

    assert kpis[0]["metric"] == "phase"
    assert kpis[1]["state"] == "blocked"
    assert kpis[3]["state"] == "degraded"
    assert kpis[4]["value"] == 1
    assert actions[0]["command"] == "next"
    assert any(row["command"] == "fix SC_004" for row in actions)
    assert any(row["command"] == "approve" for row in actions)


def test_dashboard_rows_surface_stalled_phase() -> None:
    dashboard = DashboardSummary(
        project_id="field-message",
        title="The Field Message",
        slug="field-message",
        current_phase="shot_bible",
        runtime_mode="mock",
        workflow_mode="hybrid",
        status="stalled",
        next_action="wait_for_human",
        route_reason="repair stalled",
        stalled_phase="shot_bible",
        has_blockers=True,
        issue_count=1,
    )

    actions = build_dashboard_action_rows(dashboard, None, None)
    suggestions = build_command_suggestions(
        dashboard=dashboard,
        validation=None,
        artifacts=[],
        matrix_rows=[],
    )
    graph = build_graph_rows(dashboard)
    attention = summarize_attention(dashboard, None, [])

    assert any(row["action"] == "escalate stalled phase" for row in actions)
    assert any(row["scope"] == "escalation" for row in suggestions)
    assert any(row["phase"] == "shot_bible" and row["status"] == "stalled" for row in graph)
    assert any("STALLED: shot_bible" in line for line in attention)


def test_attention_summary_surfaces_review_validation_and_provider_risk() -> None:
    gateway = RecordingGateway()

    lines = summarize_attention(
        gateway.get_dashboard("field-message"),
        gateway.get_validation_workspace("field-message"),
        gateway.list_provider_status(),
    )

    assert any(line.startswith("BLOCKED") for line in lines)
    assert any(line.startswith("REVIEW") for line in lines)
    assert any(line.startswith("VALIDATION") for line in lines)
    assert any(line.startswith("PROVIDERS") for line in lines)
