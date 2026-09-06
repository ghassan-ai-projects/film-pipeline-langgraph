"""Tests for the RevisionForm modal: submit validation, key bindings, dismiss values."""

from __future__ import annotations

from textual.widgets import Button, Static, TextArea

from film_pipeline.tui.app import FilmStudioApp
from film_pipeline.tui.screens.modals import RevisionForm
from tests.unit.tui.conftest import RecordingGateway

from .._helpers import _run


def test_revision_form_whitespace_note_is_rejected() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        results: list[str | None] = []

        def callback(note: str | None) -> None:
            results.append(note)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(RevisionForm(project_id="field-message", phase="script"), callback)
            await pilot.pause()
            form = app.screen
            assert isinstance(form, RevisionForm)
            form.query_one("#revision_note", TextArea).text = "   "
            submit_button = form.query_one("#rf_submit", Button)
            form.on_button_pressed(Button.Pressed(button=submit_button))
            await pilot.pause()
            error = form.query_one("#revision_error", Static)
            assert "required" in str(error.renderable).lower()
            # The modal stays open so the note can be entered.
            assert isinstance(app.screen, RevisionForm)

        assert results == []

    _run(_body())


def test_revision_form_submit_dismisses_stripped_note() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        results: list[str | None] = []

        def callback(note: str | None) -> None:
            results.append(note)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(RevisionForm(project_id="field-message", phase="script"), callback)
            await pilot.pause()
            form = app.screen
            assert isinstance(form, RevisionForm)
            form.query_one("#revision_note", TextArea).text = "  Tighten SC_004 dialogue.  "
            submit_button = form.query_one("#rf_submit", Button)
            form.on_button_pressed(Button.Pressed(button=submit_button))
            await pilot.pause()
            assert results == ["Tighten SC_004 dialogue."]
            assert not isinstance(app.screen, RevisionForm)

    _run(_body())


def test_revision_form_cancel_button_dismisses_none() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        results: list[str | None] = []

        def callback(note: str | None) -> None:
            results.append(note)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(RevisionForm(project_id="field-message", phase="script"), callback)
            await pilot.pause()
            form = app.screen
            assert isinstance(form, RevisionForm)
            cancel_button = form.query_one("#rf_cancel", Button)
            form.on_button_pressed(Button.Pressed(button=cancel_button))
            await pilot.pause()

        assert results == [None]

    _run(_body())


def test_revision_form_escape_key_dismisses_none() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        results: list[str | None] = []

        def callback(note: str | None) -> None:
            results.append(note)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(RevisionForm(project_id="field-message", phase="script"), callback)
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert results == [None]
            assert not isinstance(app.screen, RevisionForm)

    _run(_body())
