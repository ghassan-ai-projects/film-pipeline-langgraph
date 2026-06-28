"""Tests for FilmCockpitApp snapshot loading, enrichment, and dense layouts."""

from __future__ import annotations

import asyncio

from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Static

from film_pipeline.app.services.models import DashboardSummary
from film_pipeline.tui.app import FilmCockpitApp
from tests.unit.tui.conftest import BrokenArtifactGateway, RecordingGateway


def test_textual_cockpit_loads_gateway_snapshot() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            assert app.snapshot is not None
            assert app.snapshot.dashboard is not None
            assert app.snapshot.dashboard.current_phase == "script"
            status = app.query_one("#status_bar", Static).renderable
            project_table = app.query_one("#project_table", DataTable)
            dashboard_kpi_table = app.query_one("#dashboard_kpi_table", DataTable)
            dashboard_action_table = app.query_one("#dashboard_action_table", DataTable)
            graph_artifact_table = app.query_one("#graph_artifact_table", DataTable)
            asset_table = app.query_one("#asset_table", DataTable)
            asset_action_table = app.query_one("#asset_action_table", DataTable)
            matrix_table = app.query_one("#matrix_table", DataTable)
            matrix_pivot_table = app.query_one("#matrix_pivot_table", DataTable)
            review_checklist_table = app.query_one("#review_checklist_table", DataTable)
            review_issue_table = app.query_one("#review_issue_table", DataTable)
            command_suggestion_table = app.query_one("#command_suggestion_table", DataTable)
            command_help_table = app.query_one("#command_help_table", DataTable)
            command_validation = app.query_one("#command_validation", Static)
            validation_group_table = app.query_one("#validation_group_table", DataTable)
            validation_fix_table = app.query_one("#validation_fix_table", DataTable)
            assert "The Field Message" in str(status)
            assert project_table.row_count == 1
            assert dashboard_kpi_table.row_count == 5
            assert dashboard_action_table.row_count >= 3
            assert graph_artifact_table.row_count == 2
            assert asset_table.row_count == 2
            assert app._table_rows["asset_table"][0]["asset_id"] == (
                "clip_SC_004_shot_001_take_001"
            )
            assert asset_action_table.row_count == 6
            assert matrix_table.row_count >= 3
            assert matrix_pivot_table.row_count >= 2
            assert review_checklist_table.row_count == 5
            assert review_issue_table.row_count == 3
            assert command_suggestion_table.row_count >= 8
            assert command_help_table.row_count >= 8
            assert "Command:" in str(command_validation.renderable)
            assert validation_group_table.row_count == 2
            assert validation_fix_table.row_count == 2

    asyncio.run(run())


def test_textual_cockpit_enriches_artifact_rows_from_current_artifacts() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            assert app.snapshot is not None
            script = next(row for row in app.snapshot.artifacts if row["artifact_id"] == "script")
            assert script["scene_ids"] == ["SC_004"]
            assert script["scene_count"] == 1

    asyncio.run(run())


def test_textual_cockpit_keeps_artifact_row_when_enrichment_fails() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=BrokenArtifactGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            assert app.snapshot is not None
            matrix = next(
                row for row in app.snapshot.artifacts if row["artifact_id"] == "scene_matrix"
            )
            assert "scene_ids" not in matrix

    asyncio.run(run())


def test_textual_cockpit_uses_dense_dashboard_and_asset_layouts() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            assert app.query_one("#dashboard_top", Horizontal)
            assert app.query_one("#dashboard_ops", Horizontal)
            assert app.query_one("#asset_ops", Horizontal)
            assert app.query_one("#reader_ops", Horizontal)
            assert app.query_one("#reader_body_stack", Vertical)

    asyncio.run(run())


def test_textual_cockpit_guide_tab_exposes_validated_1min_path() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("open guide")
            await pilot.pause()

            guide_table = app.query_one("#guide_table", DataTable)
            guide_detail = app.query_one("#guide_detail", Static).renderable
            guide_summary = app.query_one("#guide_summary", Static).renderable
            context = app.query_one("#context_panel", Static).renderable
            rows = app._table_rows["guide_table"]
            assert guide_table.row_count == 6
            assert rows[0]["status"] == "done"
            assert rows[1]["status"] == "current"
            assert rows[2]["status"] == "done"
            assert rows[3]["status"] == "blocked"
            assert "2/6 done" in str(guide_summary)
            assert "create 1min-field" in str(guide_detail)
            assert "Status: done" in str(guide_detail)
            assert "Active project field-message is at script." in str(guide_detail)
            assert "A-Z path" in str(context)

    asyncio.run(run())


def test_guide_status_rows_cover_later_generation_states() -> None:
    gateway = RecordingGateway()
    dashboard = gateway.get_dashboard("field-message")
    generation_dashboard = DashboardSummary(
        project_id=dashboard.project_id,
        title=dashboard.title,
        slug=dashboard.slug,
        current_phase="generation",
        runtime_mode=dashboard.runtime_mode,
        workflow_mode=dashboard.workflow_mode,
        status="in_progress",
        next_action="run_generation",
        route_reason="generation approved",
    )
    snapshot = app_snapshot = None
    app = FilmCockpitApp(gateway=gateway)
    snapshot = app_snapshot or app._load_snapshot()
    generation_snapshot = type(snapshot)(
        projects=snapshot.projects,
        dashboard=generation_dashboard,
        review=snapshot.review,
        validation=snapshot.validation,
        artifacts=[
            *snapshot.artifacts,
            {
                "artifact_id": "clip_SC_004",
                "artifact_type": "clip",
                "phase": "generation",
                "version": 1,
                "status": "candidate",
            },
        ],
        assets=snapshot.assets,
        checkpoints=snapshot.checkpoints,
        providers=snapshot.providers,
        audit_events=snapshot.audit_events,
        comments=snapshot.comments,
        matrix_rows=snapshot.matrix_rows,
        graph_rows=snapshot.graph_rows,
        command_suggestions=snapshot.command_suggestions,
        command_options=snapshot.command_options,
    )

    rows = app._guide_rows(generation_snapshot)

    assert rows[1]["status"] == "done"
    assert rows[4]["status"] == "done"
    assert rows[5]["status"] == "done"
