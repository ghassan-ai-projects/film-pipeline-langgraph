"""Tests for the ProjectForm modal: key bindings, validation, and dismissal values."""

from __future__ import annotations

import asyncio
from typing import Any

from textual.widgets import Button, Input, Select, Static, TextArea

from film_pipeline.app.services.models import ProjectCreateRequest
from film_pipeline.tui.app import FilmStudioApp
from film_pipeline.tui.widgets.project_form import ProjectForm
from tests.unit.tui.conftest import RecordingGateway


def _run(async_fn: Any) -> Any:
    return asyncio.run(async_fn)


def _fill_identity_fields(form: ProjectForm) -> None:
    form.query_one("#pf_id", Input).value = "lighthouse"
    form.query_one("#pf_title", Input).value = "The Lighthouse Keeper"
    form.query_one("#pf_idea", TextArea).text = "A keeper defends the last light."


def test_project_form_prefills_defaults() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(
                ProjectForm(
                    default_id="lighthouse",
                    default_idea="A keeper defends the last light.",
                )
            )
            await pilot.pause()
            form = app.screen
            assert isinstance(form, ProjectForm)
            assert form.query_one("#pf_id", Input).value == "lighthouse"
            assert form.query_one("#pf_idea", TextArea).text == "A keeper defends the last light."

    _run(_body())


def test_project_form_f2_key_submits_valid_form() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        results: list[ProjectCreateRequest | None] = []

        def callback(request: ProjectCreateRequest | None) -> None:
            results.append(request)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ProjectForm(), callback)
            await pilot.pause()
            form = app.screen
            assert isinstance(form, ProjectForm)
            _fill_identity_fields(form)
            await pilot.press("f2")
            await pilot.pause()
            assert not isinstance(app.screen, ProjectForm)

        assert len(results) == 1
        assert results[0] is not None
        assert results[0].project_id == "lighthouse"

    _run(_body())


def test_project_form_ctrl_enter_key_submits_valid_form() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        results: list[ProjectCreateRequest | None] = []

        def callback(request: ProjectCreateRequest | None) -> None:
            results.append(request)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ProjectForm(), callback)
            await pilot.pause()
            form = app.screen
            assert isinstance(form, ProjectForm)
            _fill_identity_fields(form)
            await pilot.press("ctrl+enter")
            await pilot.pause()
            assert not isinstance(app.screen, ProjectForm)

        assert len(results) == 1
        assert results[0] is not None
        assert results[0].title == "The Lighthouse Keeper"

    _run(_body())


def test_project_form_escape_key_dismisses_none() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        results: list[ProjectCreateRequest | None] = []

        def callback(request: ProjectCreateRequest | None) -> None:
            results.append(request)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ProjectForm(), callback)
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert results == [None]
            assert not isinstance(app.screen, ProjectForm)

    _run(_body())


def test_project_form_rejects_invalid_id_characters() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ProjectForm())
            await pilot.pause()
            form = app.screen
            assert isinstance(form, ProjectForm)
            form.query_one("#pf_id", Input).value = "Lighthouse!"
            create_button = form.query_one("#pf_create", Button)
            form.on_button_pressed(Button.Pressed(button=create_button))
            await pilot.pause()
            error = form.query_one("#pf_error", Static)
            message = str(error.renderable).lower()
            assert "lowercase letters, numbers, hyphens, or underscores" in message
            # The form stays open so the operator can correct the id.
            assert isinstance(app.screen, ProjectForm)

    _run(_body())


def test_project_form_real_mode_requires_real_provider() -> None:
    async def _body() -> None:
        gateway = RecordingGateway()
        app = FilmStudioApp(gateway=gateway)
        results: list[ProjectCreateRequest | None] = []

        def callback(request: ProjectCreateRequest | None) -> None:
            results.append(request)

        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ProjectForm(), callback)
            await pilot.pause()
            form = app.screen
            assert isinstance(form, ProjectForm)
            _fill_identity_fields(form)
            runtime = form.query_one("#pf_runtime", Select)
            runtime.value = "real"
            await pilot.pause()
            provider = form.query_one("#pf_provider", Select)
            assert str(provider.value) == "local-real-provider"
            # An operator can still pick a mock profile; submitting must be blocked.
            provider.value = "mock-demo"
            await pilot.pause()
            create_button = form.query_one("#pf_create", Button)
            form.on_button_pressed(Button.Pressed(button=create_button))
            await pilot.pause()
            error = form.query_one("#pf_error", Static)
            assert "non-mock provider" in str(error.renderable)
            # Validation moves focus to the offending field.
            focused = app.focused
            assert focused is not None
            assert focused.id == "pf_provider"
            # The form stays open and nothing was created.
            assert isinstance(app.screen, ProjectForm)

        assert results == []

    _run(_body())
