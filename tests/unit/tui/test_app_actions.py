"""Tests for FilmCockpitApp keybinding actions, button presses, and modal screens."""

from __future__ import annotations

import asyncio
from typing import Any

from textual.widgets import Button, DataTable, Input, Select, Static, TabbedContent, TextArea

from film_pipeline.app.services.errors import ProjectNotFoundError
from film_pipeline.app.services.models import (
    MutationResult,
    OperatorCommentRequest,
    ProjectCreateRequest,
    ValidationWorkspace,
)
from film_pipeline.tui.app import FilmCockpitApp
from film_pipeline.tui.screens import NewProjectScreen, ReviseIdeaScreen
from film_pipeline.tui.view_models import selection_from_row
from tests.unit.tui.conftest import NoAssetGateway, RecordingGateway


def _press(screen: Any, button_id: str) -> None:
    button = screen.query_one(f"#{button_id}", Button)
    screen.on_button_pressed(Button.Pressed(button))


class FailingGateway(RecordingGateway):
    """Gateway whose mutations raise to exercise error branches."""

    def create_project(self, request: ProjectCreateRequest) -> MutationResult:
        raise ProjectNotFoundError("create boom")

    def run_validation(self, project_id: str | None = None) -> ValidationWorkspace:
        raise ProjectNotFoundError("validation boom")

    def submit_idea(self, project_id: str, idea: str) -> MutationResult:
        raise ProjectNotFoundError("idea boom")


def test_textual_cockpit_revision_action_uses_comment_note() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.query_one("#comment_input", Input).value = "Fix SC_004 voice but keep the ending."
            app.action_request_revision()
            await pilot.pause()

            assert gateway.revision_notes == ["Fix SC_004 voice but keep the ending."]

    asyncio.run(run())


def test_textual_cockpit_add_comment_action_uses_selected_target() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.selected_target = selection_from_row(
                "scene_table",
                {"scene": "SC_007", "phase": "script"},
            )
            app.query_one("#comment_input", Input).value = "This scene needs a sharper turn."
            app.action_add_comment()
            await pilot.pause()

            assert gateway.comments is not None
            assert gateway.comments[0].target_type == "scene"
            assert gateway.comments[0].target_id == "SC_007"
            assert gateway.comments[0].body == "This scene needs a sharper turn."

    asyncio.run(run())


def test_textual_cockpit_asset_action_row_prefills_command() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            rows = app._table_rows["asset_action_table"]
            row_index = next(
                index
                for index, row in enumerate(rows)
                if row["artifact_id"] == "script" and row["action"] == "change"
            )
            table = app.query_one("#asset_action_table", DataTable)
            table.move_cursor(row=row_index)
            table.action_select_cursor()
            await pilot.pause()

            palette = app.query_one("#command_palette", Input)
            assert palette.value == "asset change script | <note>"
            assert "open" in palette.classes

    asyncio.run(run())


def test_textual_cockpit_reader_link_table_runs_link_command() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        gateway.add_operator_comment(
            OperatorCommentRequest(
                target_type="scene",
                target_id="SC_004",
                phase="script",
                body="Keep the platform empty.",
            ),
            "field-message",
        )
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("scene SC_004")
            await pilot.pause()

            link_table = app.query_one("#reader_link_table", DataTable)
            assert link_table.row_count == 2
            rows = app._table_rows["reader_link_table"]
            row_index = next(index for index, row in enumerate(rows) if row["kind"] == "comment")
            link_table.move_cursor(row=row_index)
            link_table.action_select_cursor()
            await pilot.pause()

            context = app.query_one("#context_panel", Static).renderable
            assert "Comment Thread" in str(context)
            assert "Keep the platform empty." in str(context)

    asyncio.run(run())


def test_textual_cockpit_scene_row_selection_opens_reader() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_open_tab("scenes")
            table = app.query_one("#scene_table", DataTable)
            rows = app._table_rows["scene_table"]
            row_index = next(index for index, row in enumerate(rows) if row["scene"] == "SC_004")
            table.move_cursor(row=row_index)
            table.action_select_cursor()
            await pilot.pause()

            assert app.reader is not None
            assert app.reader.metadata["scene_id"] == "SC_004"
            assert app.reader.metadata["artifact_count"] == 2
            body = app.query_one("#reader_body", Static).renderable
            assert "The message arrived before the train." in str(body)
            assert "camera_profile: slow push-in" in str(body)
            assert "Manifest Assets" in str(body)

    asyncio.run(run())


def test_textual_cockpit_asset_row_selection_targets_manifest_asset() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_open_tab("assets")
            table = app.query_one("#asset_table", DataTable)
            rows = app._table_rows["asset_table"]
            row_index = next(
                index for index, row in enumerate(rows) if row["asset_id"] == "ref_station_platform"
            )
            table.move_cursor(row=row_index)
            table.action_select_cursor()
            await pilot.pause()

            assert app.query_one("#tabs", TabbedContent).active == "assets"
            assert app.selected_target is not None
            assert app.selected_target.target_type == "asset"
            assert app.selected_target.target_id == "ref_station_platform"
            context = app.query_one("#context_panel", Static).renderable
            assert "references/environments/station/ref_station_platform.png" in str(context)

    asyncio.run(run())


def test_textual_cockpit_asset_table_falls_back_to_artifact_reader() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=NoAssetGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_open_tab("assets")
            table = app.query_one("#asset_table", DataTable)
            rows = app._table_rows["asset_table"]
            row_index = next(
                index for index, row in enumerate(rows) if row["artifact_id"] == "scene_matrix"
            )
            table.move_cursor(row=row_index)
            table.action_select_cursor()
            await pilot.pause()

            assert app.selected_artifact is not None
            assert app.selected_artifact.artifact_id == "scene_matrix"
            assert app.query_one("#reader_index_table", DataTable).row_count == 1

    asyncio.run(run())


def test_textual_cockpit_approve_requires_confirmation() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("approve")
            await pilot.pause()

            context = app.query_one("#context_panel", Static).renderable
            assert gateway.approved_count == 0
            assert app.pending_confirmation == "approve"
            assert "Confirm Approval" in str(context)
            assert "press y" in str(context)

    asyncio.run(run())


def test_textual_cockpit_confirm_approve_calls_gateway() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("approve")
            await pilot.pause()
            app._run_command("confirm approve")
            await pilot.pause()

            assert gateway.approved_count == 1
            assert app.pending_confirmation == ""

    asyncio.run(run())


def test_textual_cockpit_second_approve_press_confirms_gateway_call() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_approve_phase()
            await pilot.pause()
            app.action_approve_phase()
            await pilot.pause()

            assert gateway.approved_count == 1
            assert app.pending_confirmation == ""

    asyncio.run(run())


def test_textual_cockpit_command_suggestion_selection_prefills_palette() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            rows = app._table_rows["command_suggestion_table"]
            row_index = next(
                index for index, row in enumerate(rows) if row["command"] == "fix SC_004"
            )
            table = app.query_one("#command_suggestion_table", DataTable)
            table.move_cursor(row=row_index)
            table.action_select_cursor()
            await pilot.pause()

            palette = app.query_one("#command_palette", Input)
            context = app.query_one("#context_panel", Static).renderable
            assert palette.value == "fix SC_004"
            assert "open" in palette.classes
            assert "Command ready" in str(context)

    asyncio.run(run())


def test_textual_cockpit_create_command_opens_modal() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("create")
            await pilot.pause()
            assert isinstance(app.screen, NewProjectScreen)

    asyncio.run(run())


def test_textual_cockpit_new_project_modal_creates_with_selected_mode() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_new_project()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewProjectScreen)
            screen.query_one("#np_id", Input).value = "lighthouse-keeper"
            screen.query_one("#np_title", Input).value = "The Lighthouse Keeper"
            screen.query_one("#np_idea", TextArea).text = "A keeper finds a prophetic bottle."
            screen.query_one("#np_runtime", Select).value = "real"
            screen._submit()
            await pilot.pause()

            assert gateway.created_request is not None
            assert gateway.created_request.project_id == "lighthouse-keeper"
            assert gateway.created_request.runtime_mode == "real"
            assert gateway.runtime_mode == "real"
            assert app.active_project_id == "lighthouse-keeper"

    asyncio.run(run())


def test_textual_cockpit_new_project_modal_blocks_missing_fields() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_new_project()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewProjectScreen)
            screen._submit()
            await pilot.pause()

            assert isinstance(app.screen, NewProjectScreen)
            assert gateway.created_request is None
            assert "required" in str(screen.query_one("#np_error", Static).renderable)

    asyncio.run(run())


def test_new_project_modal_validates_each_field() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_new_project()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewProjectScreen)
            error = screen.query_one("#np_error", Static)

            screen.query_one("#np_id", Input).value = "has spaces"
            screen._submit()
            assert "spaces" in str(error.renderable)

            screen.query_one("#np_id", Input).value = "valid-id"
            screen._submit()
            assert "Title is required" in str(error.renderable)

            screen.query_one("#np_title", Input).value = "Valid Title"
            screen._submit()
            assert "idea" in str(error.renderable).lower()
            assert isinstance(app.screen, NewProjectScreen)

    asyncio.run(run())


def test_new_project_modal_buttons_create_and_cancel() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_new_project()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewProjectScreen)
            screen.query_one("#np_id", Input).value = "btn-film"
            screen.query_one("#np_title", Input).value = "Button Film"
            screen.query_one("#np_idea", TextArea).text = "A test idea via button."
            _press(screen, "np_create")
            await pilot.pause()
            assert gateway.created_request is not None
            assert gateway.created_request.project_id == "btn-film"

    asyncio.run(run())


def test_new_project_modal_cancel_button_dismisses() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_new_project()
            await pilot.pause()
            _press(app.screen, "np_cancel")
            await pilot.pause()
            assert not isinstance(app.screen, NewProjectScreen)
            assert gateway.created_request is None

    asyncio.run(run())


def test_revise_idea_modal_buttons_submit_and_empty_guard() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_revise_idea()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ReviseIdeaScreen)

            screen.query_one("#ri_idea", TextArea).text = ""
            _press(screen, "ri_submit")
            await pilot.pause()
            assert isinstance(app.screen, ReviseIdeaScreen)
            assert gateway.submitted_ideas == []

            screen.query_one("#ri_idea", TextArea).text = "A revised idea via button."
            _press(screen, "ri_submit")
            await pilot.pause()
            assert gateway.submitted_ideas == ["A revised idea via button."]

            app.action_revise_idea()
            await pilot.pause()
            _press(app.screen, "ri_cancel")
            await pilot.pause()
            assert not isinstance(app.screen, ReviseIdeaScreen)

    asyncio.run(run())


def test_textual_cockpit_new_project_modal_cancel_is_noop() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_new_project()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NewProjectScreen)
            screen.action_cancel()
            await pilot.pause()

            assert not isinstance(app.screen, NewProjectScreen)
            assert gateway.created_request is None

    asyncio.run(run())


def test_textual_cockpit_revise_idea_cancel_is_noop() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_revise_idea()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ReviseIdeaScreen)
            screen.action_cancel()
            await pilot.pause()

            assert gateway.submitted_ideas == []

    asyncio.run(run())


def test_new_actions_guard_without_active_project() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.active_project_id = ""

            app.action_run_validation()
            await pilot.pause()
            assert "No active project" in str(app.query_one("#context_panel", Static).renderable)

            app.action_revise_idea()
            await pilot.pause()
            assert "No active project" in str(app.query_one("#context_panel", Static).renderable)

    asyncio.run(run())


def test_new_actions_surface_gateway_errors() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=FailingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            app._on_new_project_result(ProjectCreateRequest(project_id="x", title="X", idea="idea"))
            await pilot.pause()
            assert "failed" in str(app.query_one("#context_panel", Static).renderable)

            app.action_run_validation()
            await pilot.pause()
            assert "failed" in str(app.query_one("#context_panel", Static).renderable)

            app._on_revise_idea_result("a fresh idea")
            await pilot.pause()
            assert "failed" in str(app.query_one("#context_panel", Static).renderable)

    asyncio.run(run())


def test_textual_cockpit_run_validation_action() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_run_validation()
            await pilot.pause()

            assert gateway.validation_runs == 1
            assert app.query_one("#tabs", TabbedContent).active == "validation"
            assert "Validation complete" in str(app.query_one("#context_panel", Static).renderable)

    asyncio.run(run())


def test_textual_cockpit_revise_idea_action_resubmits() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.action_revise_idea()
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ReviseIdeaScreen)
            screen.query_one("#ri_idea", TextArea).text = "A sharper, tighter logline."
            screen._submit()
            await pilot.pause()

            assert gateway.submitted_ideas == ["A sharper, tighter logline."]

    asyncio.run(run())


def test_textual_cockpit_matrix_pivot_selection_applies_filter() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("matrix pivot status")
            await pilot.pause()
            rows = app._table_rows["matrix_pivot_table"]
            row_index = next(index for index, row in enumerate(rows) if row["value"] == "candidate")
            table = app.query_one("#matrix_pivot_table", DataTable)
            table.move_cursor(row=row_index)
            table.action_select_cursor()
            await pilot.pause()

            assert app.matrix_filter == "status:candidate"
            assert app.query_one("#matrix_table", DataTable).row_count == 2

    asyncio.run(run())


def test_gateway_protocol_shape_accepts_recording_gateway() -> None:
    gateway = RecordingGateway()
    rows: list[dict[str, Any]] = gateway.list_artifacts()

    assert rows[0]["artifact_id"] == "script"
