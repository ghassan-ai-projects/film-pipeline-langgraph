"""Tests for the studio widgets: reader, scene browser, and asset browser."""

from __future__ import annotations

from unittest.mock import patch

from textual.coordinate import Coordinate
from textual.widgets import Static

from film_pipeline.tui.app import FilmStudioApp
from film_pipeline.tui.screens.studio import StudioScreen
from film_pipeline.tui.widgets.asset_browser import AssetBrowser
from film_pipeline.tui.widgets.reader import Reader
from film_pipeline.tui.widgets.scene_browser import SceneBrowser
from tests.unit.tui.conftest import RecordingGateway

from ._helpers import _run


def test_reader_shows_project_overview_by_default() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            reader = screen.query_one("#reader", Reader)
            title = str(reader.query_one("#reader_title", Static).renderable)
            body = str(reader.query_one("#reader_body", Static).renderable)
            assert "Field Message" in title
            assert "Now:" in body
            assert "Next:" in body

    _run(_body())


def test_asset_browser_selects_media_asset() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            browser = screen.query_one("#asset_browser", AssetBrowser)
            browser.update_state(app.state)
            await pilot.pause()
            assert app.state.snapshot is not None
            assert len(browser._rows) == len(app.state.snapshot.assets)
            browser.cursor_coordinate = Coordinate(0, 0)
            browser.action_select_cursor()
            await pilot.pause()
            assert app.state.selected_target is not None
            assert app.state.selected_target.target_type == "asset"

    _run(_body())


def test_scene_browser_selects_scene_and_builds_reader() -> None:
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
            browser = screen.query_one("#scene_browser", SceneBrowser)
            browser.cursor_coordinate = Coordinate(0, 0)
            browser.action_select_cursor()
            await pilot.pause()
            assert app.state.selected_target is not None
            assert app.state.selected_target.target_type == "scene"
            assert app.state.reader is not None
            assert "SC_004" in app.state.reader.title
            # The reader pane renders the screenplay text.
            reader = screen.query_one("#reader", Reader)
            body = str(reader.query_one("#reader_body", Static).renderable)
            assert "INT. STATION - DAWN" in body

    _run(_body())


def test_asset_browser_open_asset_paths() -> None:
    async def _body() -> None:
        opened: list[str] = []

        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            browser = screen.query_one("#asset_browser", AssetBrowser)
            browser.update_state(app.state)
            await pilot.pause()

            # Successful open uses the system opener.
            browser.cursor_coordinate = Coordinate(0, 0)
            with patch(
                "film_pipeline.tui.widgets.asset_browser.open_path",
                side_effect=opened.append,
            ):
                browser.action_open_asset()
            assert opened and opened[0].endswith("take_001.mp4")
            assert any("opened" in str(m).lower() for m in app.state.messages)

            # A failing opener surfaces the error in the status line.
            with patch(
                "film_pipeline.tui.widgets.asset_browser.open_path",
                side_effect=FileNotFoundError("gone"),
            ):
                browser.action_open_asset()
            assert any("could not open asset" in str(m).lower() for m in app.state.messages)

            # A row without a path is reported, not opened.
            browser._rows[0]["path"] = ""
            browser.action_open_asset()
            assert any("no file path" in str(m).lower() for m in app.state.messages)

    _run(_body())


def test_asset_browser_empty_state_row() -> None:
    async def _body() -> None:
        class NoAssetsGateway(RecordingGateway):
            def list_assets(self, project_id: str | None = None) -> list[dict[str, object]]:
                return []

        gateway = NoAssetsGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            browser = app.screen.query_one("#asset_browser", AssetBrowser)
            browser.update_state(app.state)
            await pilot.pause()
            assert browser._rows == []
            assert browser.row_count == 1  # placeholder hint row
            # Opening with no selection is a no-op.
            browser.action_open_asset()

    _run(_body())


def test_scene_browser_fetches_scene_bodies_from_gateway() -> None:
    """Artifact list rows are summaries; the browser inspects scene artifacts."""

    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_project("field-message")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, StudioScreen)
            browser = screen.query_one("#scene_browser", SceneBrowser)
            # The recording gateway serves a script artifact whose body is only
            # available through inspect_artifact.
            assert any("script" in str(s.get("source_artifact", "")) for s in browser._rows) or (
                browser._rows == [] and not gateway.list_artifacts("field-message")
            )

    _run(_body())
