"""Tests for the redesigned Film Pipeline TUI."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any
from unittest.mock import patch

from textual.coordinate import Coordinate
from textual.widgets import Button, Collapsible, DataTable, Input, Select, Static, TextArea

from film_pipeline.app.services.errors import ProjectNotFoundError, ServiceError
from film_pipeline.app.services.models import (
    DashboardSummary,
    GenerationWorkspace,
    MutationResult,
    ProjectCreateRequest,
    ProjectListItem,
    ValidationWorkspace,
)
from film_pipeline.tui.app import AppState, FilmStudioApp
from film_pipeline.tui.screens.asset_viewer import AssetViewerScreen
from film_pipeline.tui.screens.home import ProjectGalleryScreen
from film_pipeline.tui.screens.review import ReviewGateScreen
from film_pipeline.tui.screens.studio import RevisionForm, StudioScreen
from film_pipeline.tui.widgets.action_bar import ActionBar
from film_pipeline.tui.widgets.artifact_list import ArtifactList
from film_pipeline.tui.widgets.asset_browser import AssetBrowser
from film_pipeline.tui.widgets.current_node import CurrentNode
from film_pipeline.tui.widgets.film_meta import FilmMeta
from film_pipeline.tui.widgets.inspector import Inspector
from film_pipeline.tui.widgets.issue_list import IssueList
from film_pipeline.tui.widgets.project_form import ProjectForm
from film_pipeline.tui.widgets.scene_browser import SceneBrowser
from film_pipeline.tui.widgets.stage_nav import StageNav
from tests.unit.tui.conftest import (
    BrokenArtifactGateway,
    FailingGateway,
    NoApprovalGateway,
    RecordingGateway,
)


def _run(async_fn: Any) -> Any:
    """Run an async test body in a fresh event loop."""
    return asyncio.run(async_fn)


def test_app_starts_on_project_gallery() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, ProjectGalleryScreen)
            table = app.screen.query_one("#project_table", DataTable)
            assert table.row_count == 1

    _run(_body())


def test_home_screen_filters_projects() -> None:
    async def _body() -> None:
        extra = ProjectListItem(
            project_id="lighthouse",
            title="The Lighthouse Keeper",
            slug="lighthouse",
            current_phase="intake",
            status="discovered",
            has_blockers=False,
            awaiting_review=False,
        )
        gateway = RecordingGateway(extra_projects=[extra])
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ProjectGalleryScreen)
            screen._filter = "lighthouse"
            screen._refresh_view()
            await pilot.pause()
            table = screen.query_one("#project_table", DataTable)
            assert table.row_count == 1

    _run(_body())


def test_open_project_switches_to_studio() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            assert isinstance(app.screen, StudioScreen)
            stage_name = app.screen.query_one("#stage_name", Static)
            assert "Script" in str(stage_name.renderable)

    _run(_body())


def test_create_project_opens_studio() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            request = ProjectCreateRequest(
                project_id="lighthouse",
                title="The Lighthouse Keeper",
                slug="lighthouse",
                idea="A keeper defends the last light.",
                runtime_mode="mock",
                workflow_mode="manual",
                project_kind="production",
            )
            app.create_project(request)
            await pilot.pause()
            assert isinstance(app.screen, StudioScreen)
            assert gateway.created_request is request

    _run(_body())


def test_studio_action_bar_shows_approve_and_revise() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            action_bar = screen.query_one("#action_bar", ActionBar)
            buttons = list(action_bar.query(Button))
            labels = {str(b.label) for b in buttons}
            assert "Approve Phase" in labels
            assert "Request Revision" in labels

    _run(_body())


def test_approve_phase_calls_gateway() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.screen.query_one("#action_approve", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert gateway.approved_count == 1
            status = app.screen.query_one("#status_footer", Static)
            assert "visual_dev" in str(status.renderable)

    _run(_body())


def test_approve_disabled_when_not_eligible() -> None:
    async def _body() -> None:
        gateway = NoApprovalGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            approve_button = app.screen.query_one("#action_approve", Button)
            assert approve_button.styles.display == "none"
            assert approve_button.disabled
            assert gateway.approved_count == 0

    _run(_body())


def test_validate_phase_calls_gateway() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.screen.query_one("#action_validate", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert gateway.validation_runs == 1
            status = app.screen.query_one("#status_footer", Static)
            assert "blocking" in str(status.renderable).lower()

    _run(_body())


def test_command_palette_toggles() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            assert "open" not in palette.classes
            await pilot.press("slash")
            await pilot.pause()
            assert "open" in palette.classes
            await pilot.press("escape")
            await pilot.pause()
            assert "open" not in palette.classes

    _run(_body())


def test_stage_nav_highlights_current_phase() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            nav = screen.query_one("#stage_nav", StageNav)
            current_button = nav.query_one("#stage_script", Button)
            assert "stage-current" in current_button.classes

    _run(_body())


def test_stage_click_changes_workspace() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.screen.query_one("#stage_intake", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert app.selected_stage == "intake"
            stage_name = app.screen.query_one("#stage_name", Static)
            assert "Intake" in str(stage_name.renderable)

    _run(_body())


def test_artifact_list_loads_stage_artifacts() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            artifact_list = screen.query_one("#artifact_list", ArtifactList)
            assert len(artifact_list._rows) == 2

    _run(_body())


def test_issue_list_loads_validation_issues() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            issue_list = screen.query_one("#issue_list", IssueList)
            assert len(issue_list._rows) == 2

    _run(_body())


def test_revision_form_submits_note() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._request_revision()
            await pilot.pause()
            form = app.screen
            assert isinstance(form, RevisionForm)
            note = form.query_one("#revision_note", TextArea)
            note.text = "Make Mara quieter."
            await pilot.click("#rf_submit")
            await pilot.pause()
            assert gateway.revision_notes == ["Make Mara quieter."]

    _run(_body())


def test_command_palette_project_opens_studio() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            palette.add_class("open")
            palette.focus()
            palette.value = "project field-message"
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, StudioScreen)

    _run(_body())


def test_command_palette_assets_pushes_viewer() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            palette.add_class("open")
            palette.focus()
            palette.value = "assets"
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, AssetViewerScreen)

    _run(_body())


def test_command_palette_validation_runs() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            palette.add_class("open")
            palette.focus()
            palette.value = "validate"
            await pilot.press("enter")
            await pilot.pause()
            assert gateway.validation_runs == 1

    _run(_body())


def test_create_failure_surfaces_status() -> None:
    async def _body() -> None:
        gateway = FailingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            request = ProjectCreateRequest(
                project_id="boom",
                title="Boom",
                slug="boom",
                idea="fail",
                runtime_mode="mock",
                workflow_mode="manual",
                project_kind="production",
            )
            result = app.create_project(request)
            assert result.ok is False
            assert "failed to create project" in app._status_text().lower()

    _run(_body())


def test_review_gate_displays_package() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.push_screen(ReviewGateScreen(id="review_screen"))
            await pilot.pause()
            assert isinstance(app.screen, ReviewGateScreen)
            summary = app.screen.query_one("#review_summary", Static)
            assert "script" in str(summary.renderable).lower()

    _run(_body())


def test_project_form_creates_request() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        result: ProjectCreateRequest | None = None

        def callback(request: ProjectCreateRequest | None) -> None:
            nonlocal result
            result = request

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ProjectForm(), callback)
            await pilot.pause()
            form = app.screen
            assert isinstance(form, ProjectForm)
            form.query_one("#pf_id", Input).value = "lighthouse"
            form.query_one("#pf_title", Input).value = "The Lighthouse Keeper"
            form.query_one("#pf_idea", TextArea).text = "A keeper defends the last light."
            form.on_button_pressed(Button.Pressed(button=form.query_one("#pf_create", Button)))
            await pilot.pause()

        assert result is not None
        assert result.project_id == "lighthouse"
        assert result.title == "The Lighthouse Keeper"

    _run(_body())


def test_project_form_shows_validation_errors() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ProjectForm())
            await pilot.pause()
            form = app.screen
            assert isinstance(form, ProjectForm)
            create_button = form.query_one("#pf_create", Button)
            form.on_button_pressed(Button.Pressed(button=create_button))
            await pilot.pause()
            error = form.query_one("#pf_error", Static)
            assert "Project ID is required" in str(error.renderable)

            form.query_one("#pf_id", Input).value = "has space"
            form.on_button_pressed(Button.Pressed(button=create_button))
            await pilot.pause()
            assert "cannot contain spaces" in str(error.renderable).lower()

    _run(_body())


def test_home_project_row_opens_studio() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ProjectGalleryScreen)
            table = screen.query_one("#project_table", DataTable)
            table.cursor_coordinate = Coordinate(0, 0)
            table.action_select_cursor()
            await pilot.pause()
            assert isinstance(app.screen, StudioScreen)

    _run(_body())


def test_home_new_project_button() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ProjectGalleryScreen)
            button = screen.query_one("#new_project", Button)
            screen.on_button_pressed(Button.Pressed(button=button))
            await pilot.pause()
            assert isinstance(app.screen, ProjectForm)

    _run(_body())


def test_home_filter_input_event() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ProjectGalleryScreen)
            inp = screen.query_one("#project_filter", Input)
            screen.on_input_changed(Input.Changed(input=inp, value="lighthouse"))
            assert screen._filter == "lighthouse"

    _run(_body())


def test_inspector_shows_reader() -> None:
    async def _body() -> None:
        from film_pipeline.tui.view_models.models import ReaderView

        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.state.reader = ReaderView(
                title="Script",
                subtitle="v4 candidate",
                outline=["Scene 1"],
                body="Mara waits.",
                metadata={"phase": "script"},
                linked_comments=[],
                linked_validation=[],
            )
            app._propagate_state()
            await pilot.pause()
            inspector = app.screen.query_one("#inspector", Inspector)
            body = inspector.query_one("#inspector_body", Static)
            assert "Mara waits" in str(body.renderable)

    _run(_body())


def test_inspector_shows_selected_target() -> None:
    async def _body() -> None:
        from film_pipeline.tui.view_models.models import TargetSelection

        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.state.reader = None
            app.state.selected_target = TargetSelection(
                target_type="issue",
                target_id="dialogue-voice",
                phase="script",
                detail={"message": "Drift in scene 4."},
            )
            app._propagate_state()
            await pilot.pause()
            inspector = app.screen.query_one("#inspector", Inspector)
            body = inspector.query_one("#inspector_body", Static)
            assert "Drift in scene 4" in str(body.renderable)

    _run(_body())


def test_issue_list_selection_sets_target() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            issue_list = app.screen.query_one("#issue_list", IssueList)
            issue_list.cursor_coordinate = Coordinate(0, 0)
            issue_list.action_select_cursor()
            await pilot.pause()
            assert app.state.selected_target is not None
            assert app.state.selected_target.target_type == "issue"

    _run(_body())


def test_artifact_list_selection_loads_reader() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            artifact_list = app.screen.query_one("#artifact_list", ArtifactList)
            artifact_list.cursor_coordinate = Coordinate(0, 0)
            artifact_list.action_select_cursor()
            await pilot.pause()
            assert app.state.reader is not None
            assert app.state.selected_artifact is not None
            assert app.state.selected_target is not None

    _run(_body())


def test_asset_viewer_loads_assets() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.push_screen(AssetViewerScreen(id="asset_viewer"))
            await pilot.pause()
            assert isinstance(app.screen, AssetViewerScreen)
            table = app.screen.query_one("#asset_table", DataTable)
            assert table.row_count == 2

    _run(_body())


def test_review_gate_approve_calls_gateway() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.push_screen(ReviewGateScreen(id="review_screen"))
            await pilot.pause()
            app.screen.query_one("#review_approve", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert gateway.approved_count == 1

    _run(_body())


def test_review_gate_back_returns_to_studio() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.push_screen(ReviewGateScreen(id="review_screen"))
            await pilot.pause()
            app.screen.query_one("#review_back", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, StudioScreen)

    _run(_body())


def test_command_palette_help() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            palette.add_class("open")
            palette.focus()
            palette.value = "help"
            await pilot.press("enter")
            await pilot.pause()
            assert any("commands" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_command_palette_stage() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            palette.add_class("open")
            palette.focus()
            palette.value = "stage intake"
            await pilot.press("enter")
            await pilot.pause()
            assert app.selected_stage == "intake"

    _run(_body())


def test_command_palette_revise() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            palette.add_class("open")
            palette.focus()
            palette.value = "revise tighten the dialogue"
            await pilot.press("enter")
            await pilot.pause()
            assert gateway.revision_notes == ["tighten the dialogue"]

    _run(_body())


def test_command_palette_unknown() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            palette.add_class("open")
            palette.focus()
            palette.value = "foobar"
            await pilot.press("enter")
            await pilot.pause()
            assert any("unknown command" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_asset_viewer_row_select_and_back() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.push_screen(AssetViewerScreen(id="asset_viewer"))
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, AssetViewerScreen)
            table = screen.query_one("#asset_table", DataTable)
            table.cursor_coordinate = Coordinate(0, 0)
            table.action_select_cursor()
            await pilot.pause()
            detail = screen.query_one("#asset_detail", Static)
            assert "clip_SC_004" in str(detail.renderable)
            screen.query_one("#asset_back", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, StudioScreen)

    _run(_body())


def test_home_refresh_button() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ProjectGalleryScreen)
            refresh_button = screen.query_one("#refresh", Button)
            screen.on_button_pressed(Button.Pressed(button=refresh_button))
            await pilot.pause()
            table = screen.query_one("#project_table", DataTable)
            assert table.row_count == 1

    _run(_body())


def test_home_update_state_with_empty_snapshot() -> None:
    async def _body() -> None:
        class EmptyGateway(RecordingGateway):
            def list_projects(self) -> list[ProjectListItem]:
                return []

        gateway = EmptyGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ProjectGalleryScreen)
            app.action_refresh()
            await pilot.pause()
            table = screen.query_one("#project_table", DataTable)
            assert table.row_count == 0

    _run(_body())


def test_action_bar_no_dashboard() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            action_bar = app.screen.query_one("#action_bar", ActionBar)
            action_bar.update_state(None)
            await pilot.pause()
            assert action_bar.query_one("#action_hint", Static).styles.display == "block"

    _run(_body())


def test_inspector_with_comments_and_validation() -> None:
    async def _body() -> None:
        from film_pipeline.app.services.models import OperatorComment
        from film_pipeline.tui.view_models.models import ReaderView

        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.state.reader = ReaderView(
                title="Script",
                subtitle="v4",
                outline=[],
                body="",
                metadata={},
                linked_comments=[
                    OperatorComment(
                        comment_id="c1",
                        project_id="field-message",
                        target_type="scene",
                        target_id="SC_004",
                        body="Tighten Mara.",
                        phase="script",
                        source="test",
                        created_at="2026-06-24T10:00:00",
                    )
                ],
                linked_validation=[{"severity": "blocking", "message": "Voice drift."}],
            )
            app._propagate_state()
            await pilot.pause()
            inspector = app.screen.query_one("#inspector", Inspector)
            body = inspector.query_one("#inspector_body", Static)
            rendered = str(body.renderable)
            assert "Tighten Mara" in rendered
            assert "Voice drift" in rendered

    _run(_body())


def test_issue_list_empty_validation() -> None:
    async def _body() -> None:
        class NoIssueGateway(RecordingGateway):
            def get_validation_workspace(
                self, project_id: str | None = None
            ) -> ValidationWorkspace:
                return ValidationWorkspace(
                    project_id=project_id or self.active_project_id,
                    phase="script",
                    source="stored_state",
                    reports=[],
                    blocking_issues=[],
                    non_blocking_issues=[],
                )

        gateway = NoIssueGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            issue_list = app.screen.query_one("#issue_list", IssueList)
            assert len(issue_list._rows) == 0

    _run(_body())


def test_artifact_list_inspect_failure() -> None:
    async def _body() -> None:
        gateway = BrokenArtifactGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            artifact_list = app.screen.query_one("#artifact_list", ArtifactList)
            artifact_list.cursor_coordinate = Coordinate(1, 0)
            artifact_list.action_select_cursor()
            await pilot.pause()
            assert any("missing" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_project_form_title_and_idea_errors() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ProjectForm())
            await pilot.pause()
            form = app.screen
            assert isinstance(form, ProjectForm)
            form.query_one("#pf_id", Input).value = "lighthouse"
            create_button = form.query_one("#pf_create", Button)
            form.on_button_pressed(Button.Pressed(button=create_button))
            await pilot.pause()
            error = form.query_one("#pf_error", Static)
            assert "title is required" in str(error.renderable).lower()

            form.query_one("#pf_title", Input).value = "The Lighthouse Keeper"
            form.on_button_pressed(Button.Pressed(button=create_button))
            await pilot.pause()
            assert "idea" in str(error.renderable).lower()

    _run(_body())


def test_project_form_runtime_switch_syncs_provider() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ProjectForm())
            await pilot.pause()
            form = app.screen
            assert isinstance(form, ProjectForm)
            runtime = form.query_one("#pf_runtime", Select)
            provider = form.query_one("#pf_provider", Select)

            runtime.value = "real"
            await pilot.pause()
            assert str(provider.value) == "local-real-provider"

            runtime.value = "mock"
            await pilot.pause()
            assert str(provider.value) == "local-real-provider"

    _run(_body())


def test_project_form_advanced_profiles_collapsible() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ProjectForm())
            await pilot.pause()
            form = app.screen
            assert isinstance(form, ProjectForm)
            collapsible = form.query_one(Collapsible)
            assert "advanced" in str(collapsible.title).lower()
            # Expand the advanced section so the hidden selects are mounted.
            collapsible.collapsed = False
            await pilot.pause()
            assert form.query_one("#pf_film_type", Select) is not None
            assert form.query_one("#pf_quality", Select) is not None

    _run(_body())


def test_project_form_cancel_action() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        called = False

        def callback(request: ProjectCreateRequest | None) -> None:
            nonlocal called
            called = True

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ProjectForm(), callback)
            await pilot.pause()
            form = app.screen
            assert isinstance(form, ProjectForm)
            cancel_button = form.query_one("#pf_cancel", Button)
            form.on_button_pressed(Button.Pressed(button=cancel_button))
            await pilot.pause()

        assert called

    _run(_body())


def test_studio_approve_failure_surfaces_status() -> None:
    async def _body() -> None:
        class BoomApproveGateway(RecordingGateway):
            def approve_phase(self, project_id: str | None = None) -> MutationResult:
                raise ProjectNotFoundError("approve boom")

        gateway = BoomApproveGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.screen.query_one("#action_approve", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert any("approve boom" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_studio_request_revision_flow() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.screen.query_one("#action_revise", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, RevisionForm)

    _run(_body())


def test_studio_next_action_opens_revision_form() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._do_next_action()
            await pilot.pause()
            assert isinstance(app.screen, RevisionForm)

    _run(_body())


def test_command_palette_create_and_home() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            palette.add_class("open")
            palette.focus()
            palette.value = "home"
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ProjectGalleryScreen)

    _run(_body())


def test_command_palette_next() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            palette.add_class("open")
            palette.focus()
            palette.value = "next"
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, RevisionForm)

    _run(_body())


def test_new_project_action_from_studio() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.action_new_project()
            await pilot.pause()
            assert isinstance(app.screen, ProjectForm)

    _run(_body())


def test_review_gate_revise_opens_revision_form() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.push_screen(ReviewGateScreen(id="review_screen"))
            await pilot.pause()
            app.screen.query_one("#review_revise", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, RevisionForm)

    _run(_body())


def test_command_palette_toggle_changes_classes() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            assert "open" not in palette.classes
            app.action_command_palette()
            await pilot.pause()
            assert "open" in palette.classes
            app.action_command_palette()
            await pilot.pause()
            assert "open" not in palette.classes

    _run(_body())


def test_command_palette_create_opens_form() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            palette.add_class("open")
            palette.focus()
            palette.value = "create"
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ProjectForm)

    _run(_body())


def test_studio_validate_no_dashboard_is_noop() -> None:
    async def _body() -> None:
        class EmptyGateway(RecordingGateway):
            def list_projects(self) -> list[ProjectListItem]:
                return []

        gateway = EmptyGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.switch_screen(StudioScreen(id="studio_screen"))
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._run_validation()
            await pilot.pause()
            assert gateway.validation_runs == 0

    _run(_body())


def test_app_state_trims_messages() -> None:
    state = AppState()
    for i in range(42):
        state.add_message(f"msg {i}")
    assert len(state.messages) == 40
    assert state.messages[-1] == "msg 41"


def test_start_create_opens_project_form() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway, start_create=True)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, ProjectForm)

    _run(_body())


def test_action_refresh_failure_sets_status() -> None:
    async def _body() -> None:
        class BrokenListGateway(RecordingGateway):
            def list_projects(self) -> list[ProjectListItem]:
                raise ServiceError("refresh boom")

        gateway = BrokenListGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_refresh()
            await pilot.pause()
            assert any("refresh boom" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_resolve_active_project_falls_back_to_discovered() -> None:
    async def _body() -> None:
        class DiscoveredGateway(RecordingGateway):
            def list_projects(self) -> list[ProjectListItem]:
                return [
                    ProjectListItem(
                        project_id="lighthouse",
                        title="The Lighthouse Keeper",
                        slug="lighthouse",
                        current_phase="intake",
                        status="discovered",
                        has_blockers=False,
                        awaiting_review=False,
                    )
                ]

        gateway = DiscoveredGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_refresh()
            await pilot.pause()
            assert app.state.active_project is not None
            assert app.state.active_project.project_id == "lighthouse"

    _run(_body())


def test_action_back_pops_screen_and_returns_home() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.push_screen(AssetViewerScreen(id="asset_viewer"))
            await pilot.pause()
            await app.action_back()
            await pilot.pause()
            assert isinstance(app.screen, ProjectGalleryScreen)

    _run(_body())


def test_set_selected_target_propagates() -> None:
    async def _body() -> None:
        from film_pipeline.tui.view_models.models import TargetSelection

        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            target = TargetSelection(
                target_type="issue",
                target_id="x",
                phase="script",
                detail={},
            )
            app.set_selected_target(target)
            assert app.state.selected_target is target

    _run(_body())


def test_command_palette_input_changed() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            palette = app.screen.query_one("#command_palette", Input)
            app.on_input_changed(Input.Changed(input=palette, value="hello"))
            await pilot.pause()
            assert any("command: hello" in str(m).lower() for m in app.state.messages)
            app.on_input_changed(Input.Changed(input=palette, value=""))
            await pilot.pause()
            assert app._status_text() == ""

    _run(_body())


def test_non_palette_input_changed_is_ignored() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            other = Input(id="other_input")
            app.on_input_changed(Input.Changed(input=other, value="hello"))
            await pilot.pause()
            assert not any("hello" in str(m) for m in app.state.messages)

    _run(_body())


def test_run_command_empty_and_approve() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app._run_command("")
            assert gateway.approved_count == 0
            app._run_command("approve")
            assert gateway.approved_count == 1

    _run(_body())


def test_run_command_project_failure_surfaces_status() -> None:
    async def _body() -> None:
        class BadOpenGateway(RecordingGateway):
            def set_active_project(self, project_id: str) -> DashboardSummary:
                raise ProjectNotFoundError("no such project")

        gateway = BadOpenGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app._run_command("project missing")
            await pilot.pause()
            assert any("could not open" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_run_command_unknown_stage() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app._run_command("stage bogus")
            await pilot.pause()
            assert any("unknown stage" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_run_command_next_from_home_shows_hint() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app._run_command("next")
            await pilot.pause()
            assert any("switch to the studio" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_submit_revision_edge_cases() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.active_project_id = ""
            app._submit_revision("note")
            await pilot.pause()
            assert any("no active project" in str(m).lower() for m in app.state.messages)

            app.open_project("field-message")
            await pilot.pause()
            app._submit_revision("   ")
            await pilot.pause()
            assert any("cannot be empty" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_submit_revision_failure_surfaces_status() -> None:
    async def _body() -> None:
        class BoomRevisionGateway(RecordingGateway):
            def request_revision(self, note: str, project_id: str | None = None) -> MutationResult:
                raise ProjectNotFoundError("revision boom")

        gateway = BoomRevisionGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app._submit_revision("fix this")
            await pilot.pause()
            assert any("revision boom" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_main_entry_point() -> None:
    from film_pipeline.tui import app as app_module

    with patch.object(FilmStudioApp, "run", lambda _self: None):
        assert app_module.main([]) == 0
        assert app_module.main(["--create"]) == 0


def test_home_form_result_ignores_invalid_request() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ProjectGalleryScreen)
            screen._on_project_form_result("not a request")
            await pilot.pause()
            assert gateway.created_request is None

    _run(_body())


def test_home_update_state_with_none() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ProjectGalleryScreen)
            screen.update_state(None)
            await pilot.pause()
            table = screen.query_one("#project_table", DataTable)
            assert table.row_count == 0

    _run(_body())


def test_home_data_table_non_project_is_ignored() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ProjectGalleryScreen)
            other: DataTable[str] = DataTable(id="other_table")
            await screen.mount(other)
            await pilot.pause()
            screen.on_data_table_row_selected(
                type("Event", (), {"data_table": other, "cursor_row": 0})()
            )
            await pilot.pause()
            assert isinstance(app.screen, ProjectGalleryScreen)

    _run(_body())


def test_studio_update_state_invalid_stage_falls_back() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.selected_stage = "not_a_phase"
            app._propagate_state()
            await pilot.pause()
            stage_name = app.screen.query_one("#stage_name", Static)
            assert "Script" in str(stage_name.renderable)

    _run(_body())


def test_studio_next_action_wait_for_human_approve() -> None:
    async def _body() -> None:
        class ApproveOnlyGateway(RecordingGateway):
            def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
                dashboard = super().get_dashboard(project_id)
                return replace(
                    dashboard,
                    next_action="wait_for_human",
                    eligible_actions=["approve_phase"],
                )

        gateway = ApproveOnlyGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._do_next_action()
            await pilot.pause()
            assert gateway.approved_count == 1

    _run(_body())


def test_studio_next_action_runs_validation_when_blockers() -> None:
    async def _body() -> None:
        class BlockedGateway(RecordingGateway):
            def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
                dashboard = super().get_dashboard(project_id)
                return replace(
                    dashboard,
                    next_action="continue_work",
                    eligible_actions=[],
                    has_blockers=True,
                )

        gateway = BlockedGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._do_next_action()
            await pilot.pause()
            assert gateway.validation_runs == 1

    _run(_body())


def test_studio_next_action_reports_next_action() -> None:
    async def _body() -> None:
        class NoOpGateway(RecordingGateway):
            def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
                dashboard = super().get_dashboard(project_id)
                return replace(
                    dashboard,
                    next_action="continue_work",
                    eligible_actions=[],
                    has_blockers=False,
                )

            def get_validation_workspace(
                self, project_id: str | None = None
            ) -> ValidationWorkspace:
                return ValidationWorkspace(
                    project_id=project_id or self.active_project_id,
                    phase="script",
                    source="stored_state",
                    reports=[],
                    blocking_issues=[],
                    non_blocking_issues=[],
                )

        gateway = NoOpGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._do_next_action()
            await pilot.pause()
            assert any("continue_work" in str(m) for m in app.state.messages)

    _run(_body())


def test_studio_approve_no_dashboard_is_noop() -> None:
    async def _body() -> None:
        class EmptyGateway(RecordingGateway):
            def list_projects(self) -> list[ProjectListItem]:
                return []

        gateway = EmptyGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.switch_screen(StudioScreen(id="studio_screen"))
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._approve_phase()
            await pilot.pause()
            assert gateway.approved_count == 0

    _run(_body())


def test_studio_approve_not_eligible_sets_status() -> None:
    async def _body() -> None:
        gateway = NoApprovalGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._approve_phase()
            await pilot.pause()
            assert any("not eligible" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_studio_request_revision_no_dashboard() -> None:
    async def _body() -> None:
        class EmptyGateway(RecordingGateway):
            def list_projects(self) -> list[ProjectListItem]:
                return []

        gateway = EmptyGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.switch_screen(StudioScreen(id="studio_screen"))
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._request_revision()
            await pilot.pause()
            assert not isinstance(app.screen, RevisionForm)

    _run(_body())


def test_studio_revision_result_invalid_is_ignored() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._on_revision_result(None)
            screen._on_revision_result("   ")
            await pilot.pause()
            assert gateway.revision_notes == []

    _run(_body())


def test_studio_revision_form_cancel() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._request_revision()
            await pilot.pause()
            form = app.screen
            assert isinstance(form, RevisionForm)
            form.query_one("#rf_cancel", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, StudioScreen)

    _run(_body())


def test_studio_revision_form_empty_note_shows_error() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._request_revision()
            await pilot.pause()
            form = app.screen
            assert isinstance(form, RevisionForm)
            form.query_one("#rf_submit", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            error = form.query_one("#revision_error", Static)
            assert "required" in str(error.renderable).lower()

    _run(_body())


def test_studio_revision_submission_failure() -> None:
    async def _body() -> None:
        class BoomRevisionGateway(RecordingGateway):
            def request_revision(self, note: str, project_id: str | None = None) -> MutationResult:
                raise ProjectNotFoundError("revision boom")

        gateway = BoomRevisionGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen._on_revision_result("fix this")
            await pilot.pause()
            assert any("revision boom" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_studio_action_home_returns_to_gallery() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            await screen.action_home()
            await pilot.pause()
            assert isinstance(app.screen, ProjectGalleryScreen)

    _run(_body())


def test_review_gate_no_review_workspace() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            assert app.state.snapshot is not None
            app.state.snapshot = replace(app.state.snapshot, review=None)
            app.push_screen(ReviewGateScreen(id="review_screen"))
            await pilot.pause()
            summary = app.screen.query_one("#review_summary", Static)
            assert "no review" in str(summary.renderable).lower()

    _run(_body())


def test_review_gate_approve_failure_sets_status() -> None:
    async def _body() -> None:
        class BoomApproveGateway(RecordingGateway):
            def approve_phase(self, project_id: str | None = None) -> MutationResult:
                raise ProjectNotFoundError("approve boom")

        gateway = BoomApproveGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.push_screen(ReviewGateScreen(id="review_screen"))
            await pilot.pause()
            app.screen.query_one("#review_approve", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert any("approve boom" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_review_gate_revise_from_home_does_not_crash() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ReviewGateScreen(id="review_screen"))
            await pilot.pause()
            app.screen.query_one("#review_revise", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ProjectGalleryScreen)

    _run(_body())


def test_simplified_view_toggles_and_populates() -> None:
    class SceneBodyGateway(RecordingGateway):
        def list_artifacts(
            self, project_id: str | None = None, phase: str | None = None
        ) -> list[dict[str, object]]:
            rows = super().list_artifacts(project_id, phase)
            for row in rows:
                if row["artifact_id"] == "script":
                    row["body"] = {
                        "scenes": [
                            {
                                "scene_id": "SC_004",
                                "scene_heading": "INT. STATION - DAWN",
                                "duration_seconds": 45,
                                "characters": ["MARA"],
                                "environment": "abandoned station platform",
                            }
                        ]
                    }
                elif row["artifact_id"] == "scene_matrix":
                    row["body"] = {
                        "rows": [
                            {
                                "scene_id": "SC_004",
                                "camera_profile": "slow push-in",
                                "camera_movement": "dolly forward",
                            }
                        ]
                    }
            return rows

    async def _body() -> None:
        gateway = SceneBodyGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)

            advanced = screen.query_one("#advanced_workspace")
            simplified = screen.query_one("#simplified_workspace")
            assert advanced.styles.display != "none"
            assert simplified.styles.display == "none"

            screen.query_one("#view_toggle", Button).focus()
            await pilot.press("enter")
            await pilot.pause()

            assert advanced.styles.display == "none"
            assert simplified.styles.display != "none"

            current_node = screen.query_one("#current_node", CurrentNode)
            current_body = current_node.query_one("#current_node_body", Static)
            assert "script" in str(current_body.renderable).lower()

            film_meta = screen.query_one("#film_meta", FilmMeta)
            film_body = film_meta.query_one("#film_meta_body", Static)
            assert "The Field Message" in str(film_body.renderable)

            asset_browser = screen.query_one("#asset_browser", AssetBrowser)
            assert asset_browser.row_count >= 2

            scene_browser = screen.query_one("#scene_browser", SceneBrowser)
            assert scene_browser.row_count >= 1

    _run(_body())


def test_generate_button_shows_in_generation_phase() -> None:
    class GenerationPhaseGateway(RecordingGateway):
        def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
            dashboard = super().get_dashboard(project_id)
            return DashboardSummary(
                project_id=dashboard.project_id,
                title=dashboard.title,
                slug=dashboard.slug,
                current_phase="generation",
                runtime_mode=dashboard.runtime_mode,
                workflow_mode=dashboard.workflow_mode,
                status="in_progress",
                next_action="run_generation",
                route_reason="ready to generate",
                eligible_actions=["run_generation"],
                blocked_actions=dashboard.blocked_actions,
                issue_count=dashboard.issue_count,
                artifact_count=dashboard.artifact_count,
                checkpoint_count=dashboard.checkpoint_count,
                has_blockers=False,
            )

    async def _body() -> None:
        gateway = GenerationPhaseGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            generate_button = app.screen.query_one("#action_generate", Button)
            assert generate_button.styles.display != "none"
            assert "Generate" in str(generate_button.label)

    _run(_body())


def test_generate_button_runs_generation_batch() -> None:
    class GenerationPhaseGateway(RecordingGateway):
        _planned: bool = False

        def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
            dashboard = super().get_dashboard(project_id)
            return DashboardSummary(
                project_id=dashboard.project_id,
                title=dashboard.title,
                slug=dashboard.slug,
                current_phase="generation",
                runtime_mode=dashboard.runtime_mode,
                workflow_mode=dashboard.workflow_mode,
                status="in_progress",
                next_action="run_generation",
                route_reason="ready to generate",
                eligible_actions=["run_generation"],
                blocked_actions=dashboard.blocked_actions,
                issue_count=dashboard.issue_count,
                artifact_count=dashboard.artifact_count,
                checkpoint_count=dashboard.checkpoint_count,
                has_blockers=False,
            )

        def get_generation_workspace(self, project_id: str | None = None) -> GenerationWorkspace:
            if not self._planned:
                return GenerationWorkspace(
                    project_id=project_id or self.active_project_id,
                    phase="generation",
                    provider="mock-video-provider",
                    model="mock-fast",
                    estimated_cost_usd=0.0,
                    rows=[],
                    next_step="plan",
                )
            return super().get_generation_workspace(project_id)

        def plan_generation(self, project_id: str | None = None) -> GenerationWorkspace:
            self._planned = True
            return super().plan_generation(project_id)

        def start_generation(self, project_id: str | None = None) -> GenerationWorkspace:
            self.start_calls += 1
            workspace = self.get_generation_workspace(project_id)
            return GenerationWorkspace(
                project_id=workspace.project_id,
                phase=workspace.phase,
                provider=workspace.provider,
                model=workspace.model,
                estimated_cost_usd=workspace.estimated_cost_usd,
                rows=[{**row, "status": "running"} for row in workspace.rows],
                planned=1,
                submitted=1,
                running=1,
                next_step="poll",
            )

    async def _body() -> None:
        gateway = GenerationPhaseGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.screen.query_one("#action_generate", Button).focus()
            await pilot.press("enter")
            for _ in range(4):
                await pilot.pause(delay=0.3)
            assert gateway.plan_calls == 1
            assert gateway.spend_calls == 1
            assert gateway.start_calls == 1
            assert gateway.poll_calls >= 1
            status = app.screen.query_one("#status_footer", Static)
            assert "complete" in str(status.renderable).lower()

    _run(_body())


def test_command_palette_generate_runs_batch() -> None:
    class GenerationPhaseGateway(RecordingGateway):
        _planned: bool = False

        def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
            dashboard = super().get_dashboard(project_id)
            return DashboardSummary(
                project_id=dashboard.project_id,
                title=dashboard.title,
                slug=dashboard.slug,
                current_phase="generation",
                runtime_mode=dashboard.runtime_mode,
                workflow_mode=dashboard.workflow_mode,
                status="in_progress",
                next_action="run_generation",
                route_reason="ready to generate",
                eligible_actions=["run_generation"],
                blocked_actions=dashboard.blocked_actions,
                issue_count=dashboard.issue_count,
                artifact_count=dashboard.artifact_count,
                checkpoint_count=dashboard.checkpoint_count,
                has_blockers=False,
            )

        def get_generation_workspace(self, project_id: str | None = None) -> GenerationWorkspace:
            if not self._planned:
                return GenerationWorkspace(
                    project_id=project_id or self.active_project_id,
                    phase="generation",
                    provider="mock-video-provider",
                    model="mock-fast",
                    estimated_cost_usd=0.0,
                    rows=[],
                    next_step="plan",
                )
            return super().get_generation_workspace(project_id)

        def plan_generation(self, project_id: str | None = None) -> GenerationWorkspace:
            self._planned = True
            return super().plan_generation(project_id)

    async def _body() -> None:
        gateway = GenerationPhaseGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app._run_command("generate")
            for _ in range(4):
                await pilot.pause(delay=0.3)
            assert gateway.plan_calls == 1
            assert gateway.start_calls == 1

    _run(_body())


def test_inspector_shows_generation_prompts() -> None:
    class GenerationPhaseGateway(RecordingGateway):
        def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
            dashboard = super().get_dashboard(project_id)
            return DashboardSummary(
                project_id=dashboard.project_id,
                title=dashboard.title,
                slug=dashboard.slug,
                current_phase="generation",
                runtime_mode=dashboard.runtime_mode,
                workflow_mode=dashboard.workflow_mode,
                status="in_progress",
                next_action="run_generation",
                route_reason="ready to generate",
                eligible_actions=["run_generation"],
                blocked_actions=dashboard.blocked_actions,
                issue_count=dashboard.issue_count,
                artifact_count=dashboard.artifact_count,
                checkpoint_count=dashboard.checkpoint_count,
                has_blockers=False,
            )

    async def _body() -> None:
        gateway = GenerationPhaseGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            inspector = app.screen.query_one("#inspector", Inspector)
            body = inspector.query_one("#inspector_body", Static)
            assert "Batch status" in str(body.renderable)
            assert "Prompts" in str(body.renderable)
            assert "Wide establishing shot" in str(body.renderable)

    _run(_body())


def test_action_bar_generation_button_relabels_after_completion() -> None:
    class GenerationDoneGateway(RecordingGateway):
        def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
            dashboard = super().get_dashboard(project_id)
            return DashboardSummary(
                project_id=dashboard.project_id,
                title=dashboard.title,
                slug=dashboard.slug,
                current_phase="generation",
                runtime_mode=dashboard.runtime_mode,
                workflow_mode=dashboard.workflow_mode,
                status="in_progress",
                next_action="approve_phase",
                route_reason="generation complete",
                eligible_actions=["approve_phase", "request_revision"],
                blocked_actions=dashboard.blocked_actions,
                issue_count=dashboard.issue_count,
                artifact_count=dashboard.artifact_count,
                checkpoint_count=dashboard.checkpoint_count,
                has_blockers=False,
            )

        def get_generation_workspace(self, project_id: str | None = None) -> GenerationWorkspace:
            workspace = super().get_generation_workspace(project_id)
            return GenerationWorkspace(
                project_id=workspace.project_id,
                phase="generation",
                provider="mock-video-provider",
                model="mock-fast",
                estimated_cost_usd=0.0,
                rows=workspace.rows,
                planned=1,
                submitted=1,
                completed=2,
                next_step="approve_phase",
            )

    async def _body() -> None:
        gateway = GenerationDoneGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            generate_button = app.screen.query_one("#action_generate", Button)
            assert str(generate_button.label) == "Regenerate"
            assert generate_button.variant == "default"
            approve_button = app.screen.query_one("#action_approve", Button)
            assert str(approve_button.label) == "Approve Phase"
            assert approve_button.variant == "primary"

    _run(_body())


def test_inspector_shows_full_artifact_body() -> None:
    async def _body() -> None:
        from film_pipeline.tui.view_models.models import ReaderView

        long_body = "Line.\n" * 2000
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.state.reader = ReaderView(
                title="Script",
                subtitle="v1",
                outline=[],
                body=long_body,
                metadata={},
                linked_comments=[],
                linked_validation=[],
            )
            app._propagate_state()
            await pilot.pause()
            inspector = app.screen.query_one("#inspector", Inspector)
            body = inspector.query_one("#inspector_body", Static)
            rendered = str(body.renderable)
            assert len(rendered) > 10000
            assert rendered.count("Line.") == 2000

    _run(_body())
