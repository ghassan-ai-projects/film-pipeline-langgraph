"""Tests for FilmCockpitApp command palette dispatch and navigation."""

from __future__ import annotations

import asyncio

from textual.widgets import DataTable, Input, Static, TabbedContent

from film_pipeline.app.services.models import OperatorCommentRequest, ProjectListItem
from film_pipeline.tui.cockpit import FilmCockpitApp
from film_pipeline.tui.screens import NewProjectScreen, ReviseIdeaScreen
from tests.unit.tui.conftest import NoApprovalGateway, RecordingGateway


def test_textual_cockpit_dashboard_metric_command_routes_to_blockers() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("dashboard blockers")
            await pilot.pause()

            table = app.query_one("#validation_table", DataTable)
            context = app.query_one("#context_panel", Static).renderable
            assert table.row_count == 1
            assert "Validation filter: blocking" in str(context)

    asyncio.run(run())


def test_textual_cockpit_targeted_comment_command_stores_annotation() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("comment SC_007 | Make the payoff clearer.")
            await pilot.pause()

            assert gateway.comments is not None
            assert gateway.comments[0].target_type == "validation_issue"
            assert gateway.comments[0].target_id == "SC_007"
            assert gateway.comments[0].phase == "script"
            assert gateway.comments[0].body == "Make the payoff clearer."

    asyncio.run(run())


def test_textual_cockpit_review_issue_command_prefills_and_opens_target() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("review issue review:1")
            await pilot.pause()

            assert app.selected_target is not None
            assert app.selected_target.target_type == "scene"
            assert app.selected_target.target_id == "SC_004"
            assert app.query_one("#comment_input", Input).value == "Dialogue voice drift in SC_004"
            context = app.query_one("#context_panel", Static).renderable
            assert "Review Issue" in str(context)

    asyncio.run(run())


def test_textual_cockpit_draft_command_prefills_targeted_review_note() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("draft SC_007 | Make the payoff more visual.")
            await pilot.pause()

            assert app.selected_target is not None
            assert app.selected_target.target_id == "SC_007"
            assert app.query_one("#comment_input", Input).value == "Make the payoff more visual."
            context = app.query_one("#context_panel", Static).renderable
            assert "Draft Ready" in str(context)

    asyncio.run(run())


def test_textual_cockpit_thread_command_shows_grouped_comments() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        gateway.add_operator_comment(
            OperatorCommentRequest(
                target_type="scene",
                target_id="SC_004",
                phase="script",
                body="Voice is too polished.",
            ),
            "field-message",
        )
        gateway.add_operator_comment(
            OperatorCommentRequest(
                target_type="scene",
                target_id="SC_004",
                phase="script",
                body="Keep the station silence.",
            ),
            "field-message",
        )
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            thread_table = app.query_one("#comment_thread_table", DataTable)
            assert thread_table.row_count == 1

            app._run_command("thread SC_004")
            await pilot.pause()

            assert app.selected_target is not None
            assert app.selected_target.target_id == "SC_004"
            context = app.query_one("#context_panel", Static).renderable
            assert "Comment Thread" in str(context)
            assert "Voice is too polished." in str(context)
            assert "Keep the station silence." in str(context)

    asyncio.run(run())


def test_textual_cockpit_artifact_command_loads_reader_context() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("artifact script")
            await pilot.pause()

            assert app.selected_artifact is not None
            assert app.selected_artifact.artifact_id == "script"
            assert app.reader is not None
            assert app.selected_target is not None
            assert app.selected_target.target_type == "artifact"
            context = app.query_one("#context_panel", Static).renderable
            body = app.query_one("#reader_body", Static).renderable
            index_table = app.query_one("#reader_index_table", DataTable)
            assert "Reader" in str(context)
            assert "INT. STATION - DAWN" in str(body)
            assert "SC_004" in str(context)
            assert index_table.row_count == 1

    asyncio.run(run())


def test_textual_cockpit_asset_review_command_stores_review_comment() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("asset review script")
            await pilot.pause()

            assert gateway.comments is not None
            assert gateway.comments[0].target_type == "artifact"
            assert gateway.comments[0].target_id == "script"
            assert gateway.comments[0].phase == "script"
            assert "[asset_action=review]" in gateway.comments[0].body

    asyncio.run(run())


def test_textual_cockpit_asset_change_and_extend_submit_targeted_revisions() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("asset change script | Make scene four less verbal.")
            await pilot.pause()
            app._run_command("asset extend scene_matrix | Add one visual bridge shot.")
            await pilot.pause()

            assert gateway.revision_notes is not None
            assert "[asset_action=change] Make scene four less verbal." in gateway.revision_notes[0]
            assert "target_type=artifact target_id=script phase=script" in gateway.revision_notes[0]
            assert "[asset_action=extend] Add one visual bridge shot." in gateway.revision_notes[1]
            assert (
                "target_type=artifact target_id=scene_matrix phase=script"
                in gateway.revision_notes[1]
            )

    asyncio.run(run())


def test_textual_cockpit_reader_next_opens_index_target() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("artifact script")
            await pilot.pause()
            app._run_command("reader next")
            await pilot.pause()

            assert app.reader is not None
            assert app.reader.metadata["scene_id"] == "SC_004"
            assert app.selected_target is not None
            assert app.selected_target.target_type == "scene"

    asyncio.run(run())


def test_textual_cockpit_scene_command_loads_scene_reader() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("scene SC_004")
            await pilot.pause()

            assert app.reader is not None
            assert app.reader.metadata["scene_id"] == "SC_004"
            assert app.selected_target is not None
            assert app.selected_target.target_type == "scene"
            body = app.query_one("#reader_body", Static).renderable
            scene_reader = app.query_one("#scene_reader", Static).renderable
            assert "The message arrived before the train." in str(body)
            assert "camera_movement: dolly forward from wide to close" in str(body)
            assert "assets: ref_station_platform, prop_warning_note" in str(body)
            assert "Manifest Assets" in str(body)
            assert "clip_SC_004_shot_001_take_001" in str(body)
            assert "references/environments/station/ref_station_platform.png" in str(body)
            assert "Linked validation" in str(scene_reader)

    asyncio.run(run())


def test_textual_cockpit_unknown_scene_reports_missing_scene() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("scene SC_999")
            await pilot.pause()

            context = app.query_one("#context_panel", Static).renderable
            assert "Scene 'SC_999' was not found" in str(context)

    asyncio.run(run())


def test_textual_cockpit_phase_command_drills_into_graph() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("phase script")
            await pilot.pause()

            assert app.selected_target is not None
            assert app.selected_target.target_type == "graph_phase"
            assert app.selected_target.target_id == "script"
            detail = app.query_one("#graph_phase_detail", Static).renderable
            table = app.query_one("#graph_table", DataTable)
            context = app.query_one("#context_panel", Static).renderable
            assert "Phase: script" in str(detail)
            assert table.row_count >= 2
            assert "Suggested commands" in str(context)

    asyncio.run(run())


def test_textual_cockpit_next_command_opens_review_workspace() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("next")
            await pilot.pause()

            context = app.query_one("#context_panel", Static).renderable
            assert "Review Context" in str(context)

    asyncio.run(run())


def test_textual_cockpit_revise_alias_submits_note() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("revise Keep the ending but sharpen SC_004 voice.")
            await pilot.pause()

            assert gateway.revision_notes == ["Keep the ending but sharpen SC_004 voice."]

    asyncio.run(run())


def test_textual_cockpit_command_palette_filters_and_validates_input() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            palette = app.query_one("#command_palette", Input)
            palette.value = "artifact missing"
            await pilot.pause()

            validation = app.query_one("#command_validation", Static).renderable
            rows = app._table_rows["command_suggestion_table"]
            assert "Unknown artifact" in str(validation)
            assert all("artifact" in str(row["command"]) for row in rows)

    asyncio.run(run())


def test_textual_cockpit_commands_command_shows_help_surface() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("commands")
            await pilot.pause()

            context = app.query_one("#context_panel", Static).renderable
            help_rows = app._table_rows["command_help_table"]
            assert "Command Help" in str(context)
            assert any(row["command"] == "scene <scene_id>" for row in help_rows)

    asyncio.run(run())


def test_command_aliases_route_to_new_actions() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            app._run_command("validate")
            await pilot.pause()
            assert gateway.validation_runs == 1

            app._run_command("new")
            await pilot.pause()
            assert isinstance(app.screen, NewProjectScreen)
            app.screen.action_cancel()
            await pilot.pause()

            app._run_command("idea")
            await pilot.pause()
            assert isinstance(app.screen, ReviseIdeaScreen)
            app.screen.action_cancel()
            await pilot.pause()

    asyncio.run(run())


def test_textual_cockpit_project_lane_filter_and_switch_command() -> None:
    async def run() -> None:
        gateway = RecordingGateway(
            extra_projects=[
                ProjectListItem(
                    project_id="fixture-short-test",
                    title="Fixture Short",
                    slug="fixture-short-test",
                    current_phase="intake",
                    status="discovered",
                    has_blockers=False,
                    awaiting_review=False,
                    project_kind="test",
                    project_root="/tmp/projects/fixture-short-test",
                )
            ]
        )
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            assert app.query_one("#project_table", DataTable).row_count == 1

            app._run_command("projects test")
            await pilot.pause()
            rows = app._table_rows["project_table"]
            context = app.query_one("#context_panel", Static).renderable
            assert app.project_filter == "test"
            assert rows[0]["project"] == "fixture-short-test"
            assert "Project lane: test" in str(context)

            app._run_command("projects all")
            await pilot.pause()
            app._run_command("project field-message")
            await pilot.pause()

            assert gateway.active_project_id == "field-message"
            assert app.active_project_id == "field-message"

    asyncio.run(run())


def test_textual_cockpit_guidance_branches_for_invalid_commands() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            app._asset_command("")
            assert "Asset commands" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("asset review missing")
            await pilot.pause()
            assert "Artifact 'missing'" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("asset change script")
            await pilot.pause()
            assert "Use: asset change" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("projects sandbox")
            await pilot.pause()
            assert "projects production" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("project ")
            await pilot.pause()
            assert "Unknown command" in str(app.query_one("#context_panel", Static).renderable)

            app._switch_project("")
            assert "Use: project" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("confirm approve")
            await pilot.pause()
            assert "No pending approval" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("create missing-parts")
            await pilot.pause()
            assert "Use: create" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("thread missing-target")
            await pilot.pause()
            assert "No comment thread" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("draft missing-target")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "review"

            app._show_phase_detail("")
            assert "Use: phase" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("dashboard ops")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "ops"

            app._run_command("dashboard comments")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "review"

            app._run_command("dashboard unknown")
            await pilot.pause()
            assert "Dashboard commands" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("replace <template>")
            await pilot.pause()
            assert "Replace template fields" in str(
                app.query_one("#context_panel", Static).renderable
            )

    asyncio.run(run())


def test_textual_cockpit_create_and_missing_target_branches() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            app._run_command(
                "create new-short | New Short | A one minute chase across three rooms."
            )
            await pilot.pause()
            assert gateway.created_request is not None
            assert gateway.created_request.project_id == "new-short"
            assert gateway.created_request.project_kind == "production"
            assert app.active_project_id == "new-short"

            app._open_artifact("missing-artifact")
            assert "missing-artifact" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("review issue missing-issue")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "review"

            app._run_command("asset extend missing-artifact | Add more coverage.")
            await pilot.pause()
            assert "missing-artifact" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("open unknown-target")
            await pilot.pause()
            assert "unknown-target" in str(app.query_one("#context_panel", Static).renderable)

    asyncio.run(run())


def test_textual_cockpit_no_snapshot_and_ineligible_approval_guards() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=NoApprovalGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            app._run_command("approve")
            await pilot.pause()
            assert "Approval is not eligible" in str(
                app.query_one("#context_panel", Static).renderable
            )

            app.snapshot = None
            app._show_phase_detail("script")
            assert "No snapshot loaded" in str(app.query_one("#context_panel", Static).renderable)

            app._start_fix("SC_004")
            assert "No snapshot loaded" in str(app.query_one("#context_panel", Static).renderable)

            app._show_thread("SC_004")
            assert "No snapshot loaded" in str(app.query_one("#context_panel", Static).renderable)

            app._request_asset_review("script")
            assert "No active project" in str(app.query_one("#context_panel", Static).renderable)

    asyncio.run(run())


def test_textual_cockpit_matrix_filter_command_filters_rows() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("matrix warning")
            await pilot.pause()

            table = app.query_one("#matrix_table", DataTable)
            summary = app.query_one("#matrix_summary", Static).renderable
            context = app.query_one("#context_panel", Static).renderable
            assert app.matrix_filter == "warning"
            assert table.row_count == 1
            assert "Rows: 1/" in str(summary)
            assert "Matrix filter: warning" in str(context)

    asyncio.run(run())


def test_textual_cockpit_matrix_pivot_command_groups_rows() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("matrix pivot validation")
            await pilot.pause()

            pivot_table = app.query_one("#matrix_pivot_table", DataTable)
            context = app.query_one("#context_panel", Static).renderable
            rows = app._table_rows["matrix_pivot_table"]
            assert pivot_table.row_count >= 2
            assert app._matrix_pivot == "validation"
            assert any(row["value"] == "blocking" for row in rows)
            assert "Matrix Pivot" in str(context)

    asyncio.run(run())


def test_textual_cockpit_validator_command_filters_validation_rows() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("validator dialogue-voice")
            await pilot.pause()

            table = app.query_one("#validation_table", DataTable)
            context = app.query_one("#context_panel", Static).renderable
            assert table.row_count == 1
            assert "Validation filter: dialogue-voice" in str(context)
            assert "Visible issues: 1" in str(context)

    asyncio.run(run())


def test_textual_cockpit_show_blocked_filters_validation_rows() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("show blocked")
            await pilot.pause()

            table = app.query_one("#validation_table", DataTable)
            context = app.query_one("#context_panel", Static).renderable
            assert table.row_count == 1
            assert "Validation filter: blocking" in str(context)

    asyncio.run(run())


def test_textual_cockpit_fix_command_prefills_targeted_note() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("fix SC_004")
            await pilot.pause()

            assert app.reader is not None
            assert app.selected_target is not None
            assert app.selected_target.target_id == "SC_004"
            comment = app.query_one("#comment_input", Input).value
            context = app.query_one("#context_panel", Static).renderable
            assert comment == "dialogue-voice: Dialogue voice drift in scene 4."
            assert "Fix Draft" in str(context)

    asyncio.run(run())


def test_textual_cockpit_open_target_command_opens_artifact_reader() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("open script")
            await pilot.pause()

            assert app.selected_artifact is not None
            assert app.selected_artifact.artifact_id == "script"
            assert app.reader is not None
            assert app.reader.title == "script:v4"

    asyncio.run(run())
