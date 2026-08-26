"""Tests for the ConfirmScreen modal: button and key-binding dismissal paths."""

from __future__ import annotations

import asyncio
from typing import Any

from textual.widgets import Button, Static

from film_pipeline.tui.app import FilmStudioApp
from film_pipeline.tui.screens.modals import ConfirmScreen
from tests.unit.tui.conftest import RecordingGateway


def _run(async_fn: Any) -> Any:
    return asyncio.run(async_fn)


def test_confirm_screen_renders_title_and_message() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(
                ConfirmScreen("Regenerate clips?", "This will overwrite existing clips.")
            )
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ConfirmScreen)
            title = str(screen.query_one(".dialog-title", Static).renderable)
            message = str(screen.query_one(".dialog-hint", Static).renderable)
            assert "Regenerate clips?" in title
            assert "overwrite existing clips" in message

    _run(_body())


def test_confirm_screen_yes_button_dismisses_true() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        results: list[bool | None] = []

        def callback(confirmed: bool | None) -> None:
            results.append(confirmed)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ConfirmScreen("Regenerate clips?", "Costs may apply."), callback)
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ConfirmScreen)
            yes_button = screen.query_one("#cf_yes", Button)
            screen.on_button_pressed(Button.Pressed(button=yes_button))
            await pilot.pause()

        assert results == [True]

    _run(_body())


def test_confirm_screen_no_button_dismisses_false() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        results: list[bool | None] = []

        def callback(confirmed: bool | None) -> None:
            results.append(confirmed)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ConfirmScreen("Regenerate clips?", "Costs may apply."), callback)
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ConfirmScreen)
            no_button = screen.query_one("#cf_no", Button)
            screen.on_button_pressed(Button.Pressed(button=no_button))
            await pilot.pause()

        assert results == [False]

    _run(_body())


def test_confirm_screen_escape_cancels_with_false() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        results: list[bool | None] = []

        def callback(confirmed: bool | None) -> None:
            results.append(confirmed)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ConfirmScreen("Regenerate clips?", "Costs may apply."), callback)
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert results == [False]
            assert not isinstance(app.screen, ConfirmScreen)

    _run(_body())
