"""Tests for the simplified-view widgets."""

from __future__ import annotations

import asyncio
from typing import Any

from textual.coordinate import Coordinate
from textual.widgets import Static

from film_pipeline.app.services.models import DashboardSummary
from film_pipeline.tui.app import FilmStudioApp
from film_pipeline.tui.screens.studio import StudioScreen
from film_pipeline.tui.widgets.asset_browser import AssetBrowser
from film_pipeline.tui.widgets.current_node import CurrentNode
from film_pipeline.tui.widgets.film_meta import FilmMeta
from film_pipeline.tui.widgets.scene_browser import SceneBrowser
from tests.unit.tui.conftest import RecordingGateway


def _run(async_fn: Any) -> Any:
    return asyncio.run(async_fn)


def _dashboard_with_profiles() -> DashboardSummary:
    return DashboardSummary(
        project_id="field-message",
        title="The Field Message",
        slug="field-message",
        current_phase="script",
        runtime_mode="mock",
        workflow_mode="hybrid",
        status="awaiting_review",
        next_action="present_review_package",
        route_reason="script requires operator review",
        eligible_actions=["approve_phase", "request_revision"],
        blocked_actions=[{"action": "generation", "reason": "approval required"}],
        idea="A woman receives a message from the future.",
        issue_count=1,
        artifact_count=2,
        checkpoint_count=1,
        has_blockers=True,
        profile_stack={
            "film_type_profile": "film-type.narrative",
            "quality_profile": "quality.draft",
            "provider_profile": "mock-demo",
        },
    )


def test_current_node_shows_blockers() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            current_node = app.screen.query_one("#current_node", CurrentNode)
            current_node.update_state(app.state)
            await pilot.pause()
            body = current_node.query_one("#current_node_body", Static)
            rendered = str(body.renderable).lower()
            assert "script" in rendered
            assert "blocking" in rendered

    _run(_body())


def test_film_meta_shows_profiles() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            app.state.dashboard = _dashboard_with_profiles()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen.action_toggle_view()
            await pilot.pause()
            film_meta = screen.query_one("#film_meta", FilmMeta)
            film_meta.update_state(app.state)
            await pilot.pause()
            body = film_meta.query_one("#film_meta_body", Static)
            rendered = str(body.renderable)
            assert "The Field Message" in rendered
            assert "narrative" in rendered
            assert "draft" in rendered

    _run(_body())


def test_asset_browser_selects_artifact() -> None:
    class BodyGateway(RecordingGateway):
        def list_artifacts(
            self, project_id: str | None = None, phase: str | None = None
        ) -> list[dict[str, object]]:
            rows = super().list_artifacts(project_id, phase)
            rows[0]["body"] = {
                "scenes": [{"scene_id": "SC_004", "scene_heading": "INT. STATION - DAWN"}]
            }
            return rows

    async def _body() -> None:
        gateway = BodyGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen.action_toggle_view()
            await pilot.pause()
            browser = screen.query_one("#asset_browser", AssetBrowser)
            # First two rows are asset-manifest entries; row 2 is the script artifact.
            browser.cursor_coordinate = Coordinate(2, 0)
            browser.action_select_cursor()
            await pilot.pause()
            assert app.state.selected_target is not None
            assert app.state.selected_target.target_type == "artifact"

    _run(_body())


def test_scene_browser_selects_scene() -> None:
    class BodyGateway(RecordingGateway):
        def list_artifacts(
            self, project_id: str | None = None, phase: str | None = None
        ) -> list[dict[str, object]]:
            rows = super().list_artifacts(project_id, phase)
            rows[0]["body"] = {
                "scenes": [
                    {
                        "scene_id": "SC_004",
                        "scene_heading": "INT. STATION - DAWN",
                        "duration_seconds": 45,
                        "characters": ["MARA"],
                        "environment": "station",
                        "camera_profile": "push-in",
                    }
                ]
            }
            return rows

    async def _body() -> None:
        gateway = BodyGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            screen.action_toggle_view()
            await pilot.pause()
            browser = screen.query_one("#scene_browser", SceneBrowser)
            browser.cursor_coordinate = Coordinate(0, 0)
            browser.action_select_cursor()
            await pilot.pause()
            assert app.state.selected_target is not None
            assert app.state.selected_target.target_type == "scene"
            assert app.state.reader is not None
            assert "SC_004" in app.state.reader.title

    _run(_body())
