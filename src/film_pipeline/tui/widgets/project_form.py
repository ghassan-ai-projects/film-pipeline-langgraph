"""Modal form for creating a new film project."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Collapsible, Input, Label, Select, Static, TextArea

from film_pipeline.app.services.models import ProjectCreateRequest


def _dialog_header() -> ComposeResult:
    with Vertical(id="dialog_header"):
        yield Static("New Project", classes="dialog-title")
        yield Static(
            "Give your film an id, a title, and a short idea.",
            classes="dialog-hint",
        )


def _identity_fields(default_id: str, default_idea: str) -> ComposeResult:
    yield Label("Project ID", classes="field-label")
    yield Input(
        value=default_id,
        placeholder="e.g. lighthouse-keeper (lowercase, no spaces)",
        id="pf_id",
    )
    yield Label("Title", classes="field-label")
    yield Input(placeholder="e.g. The Lighthouse Keeper", id="pf_title")
    yield Label("Idea / logline", classes="field-label")
    yield TextArea(default_idea, id="pf_idea")


def _runtime_grid() -> ComposeResult:
    with Grid(id="runtime_grid"):
        yield Label("Runtime", classes="field-label")
        yield Select(
            [
                ("mock — fast, free", "mock"),
                ("real — live models", "real"),
            ],
            value="mock",
            allow_blank=False,
            id="pf_runtime",
        )
        yield Label("Provider", classes="field-label")
        yield Select(
            [
                ("none", ""),
                ("mock demo", "mock-demo"),
                ("seedance primary", "provider.seedance_primary"),
                ("free / low cost", "provider.free_or_low_cost"),
                ("local real provider", "local-real-provider"),
            ],
            value="",
            allow_blank=False,
            id="pf_provider",
        )
        yield Label("Generation", classes="field-label")
        yield Select(
            [
                ("generate media", "generate"),
                ("text only", "text_only"),
            ],
            value="generate",
            allow_blank=False,
            id="pf_generation_policy",
        )


def _advanced_profiles() -> ComposeResult:
    with (
        Collapsible(title="Advanced profiles", collapsed=True),
        Grid(id="advanced_grid"),
    ):
        yield Label("Film type", classes="field-label")
        yield Select(
            [
                ("narrative", "film-type.narrative"),
                ("visual poetry", "film-type.visual_poetry"),
            ],
            value="film-type.narrative",
            allow_blank=False,
            id="pf_film_type",
        )
        yield Label("Quality", classes="field-label")
        yield Select(
            [
                ("draft", "quality.draft"),
                ("studio", "quality.studio"),
                ("festival", "quality.festival"),
            ],
            value="quality.draft",
            allow_blank=False,
            id="pf_quality",
        )
        yield Label("Review", classes="field-label")
        yield Select(
            [("strict continuity", "review.strict_continuity")],
            value="review.strict_continuity",
            allow_blank=False,
            id="pf_review",
        )
        yield Label("Auto-approve", classes="field-label")
        yield Select(
            [("none", ""), ("auto-approve", "auto-approve")],
            value="",
            allow_blank=False,
            id="pf_auto_approve",
        )


def _dialog_body(default_id: str, default_idea: str) -> ComposeResult:
    with VerticalScroll(id="dialog_body"):
        yield from _identity_fields(default_id, default_idea)
        yield from _runtime_grid()
        yield from _advanced_profiles()
        yield Static("", id="pf_error", classes="dialog-error")


def _dialog_buttons() -> ComposeResult:
    with Horizontal(id="dialog_buttons"):
        yield Button("Create", id="pf_create", variant="primary")
        yield Button("Cancel", id="pf_cancel")


@dataclass(frozen=True)
class _FormValues:
    """Field values read from the form before validation."""

    project_id: str
    title: str
    idea: str
    runtime_mode: str
    film_type_profile: str
    quality_profile: str
    provider_profile: str
    review_profile: str
    auto_approve_profile: str
    generation_policy: str


class ProjectForm(ModalScreen[ProjectCreateRequest | None]):
    """Collect the minimum fields needed to create a new project."""

    CSS = """
    ProjectForm {
        align: center middle;
    }

    #dialog {
        width: 72;
        height: 22;
        padding: 0;
        border: thick #88c0d0;
        background: #11151a;
        layout: grid;
        grid-size: 1 3;
        grid-rows: 3 1fr 3;
    }

    #dialog_header {
        padding: 1 2 0 2;
        height: 3;
    }

    #dialog_body {
        padding: 0 2;
        height: 1fr;
        overflow-y: auto;
    }

    #dialog_buttons {
        padding: 0 2 1 2;
        height: 3;
    }

    .dialog-title {
        color: #88c0d0;
        text-style: bold;
    }

    .dialog-hint {
        color: #6b7480;
    }

    .field-label {
        color: #d8dee9;
        margin: 0;
        text-align: left;
    }

    #dialog Input, #dialog Select {
        width: 100%;
    }

    #dialog TextArea {
        width: 100%;
        height: 3;
    }

    #runtime_grid {
        grid-size: 2;
        grid-columns: 16 1fr;
        grid-gutter: 0 1;
        height: auto;
        margin: 1 0 0 0;
    }

    #runtime_grid .field-label {
        text-align: right;
        padding: 1 0 0 0;
    }

    Collapsible {
        padding: 0;
        margin: 1 0 0 0;
    }

    Collapsible > .contents {
        padding: 0;
    }

    #advanced_grid {
        grid-size: 2;
        grid-columns: 16 1fr;
        grid-gutter: 0 1;
        height: auto;
    }

    #advanced_grid .field-label {
        text-align: right;
        padding: 1 0 0 0;
    }

    .dialog-error {
        color: #bf616a;
        text-style: bold;
        background: #2e1b1e;
        padding: 0 1;
        margin: 1 0 0 0;
    }

    #dialog_buttons Button {
        margin: 0 1 0 0;
    }
    """

    BINDINGS: ClassVar = [
        Binding("escape", "cancel", "Cancel"),
        Binding("f2", "submit", "Create"),
        Binding("ctrl+enter", "submit", "Create"),
    ]

    _VALID_ID: ClassVar = re.compile(r"^[a-z0-9_-]+$")

    def __init__(
        self,
        *,
        default_id: str = "",
        default_idea: str = "",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._default_id = default_id
        self._default_idea = default_idea

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield from _dialog_header()
            yield from _dialog_body(self._default_id, self._default_idea)
            yield from _dialog_buttons()

    def on_mount(self) -> None:
        self.query_one("#pf_id", Input).focus()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Keep provider profile in sync with the chosen runtime mode."""
        if event.select.id == "pf_runtime":
            provider = self.query_one("#pf_provider", Select)
            if event.value == "real" and str(provider.value) in {"", "mock-demo"}:
                provider.value = "local-real-provider"

    def action_submit(self) -> None:
        """Keyboard shortcut to submit the form."""
        self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pf_cancel":
            self.dismiss(None)
        elif event.button.id == "pf_create":
            self._submit()

    def _collect_form_values(self) -> _FormValues:
        return _FormValues(
            project_id=self.query_one("#pf_id", Input).value.strip(),
            title=self.query_one("#pf_title", Input).value.strip(),
            idea=self.query_one("#pf_idea", TextArea).text.strip(),
            runtime_mode=str(self.query_one("#pf_runtime", Select).value),
            film_type_profile=str(self.query_one("#pf_film_type", Select).value),
            quality_profile=str(self.query_one("#pf_quality", Select).value),
            provider_profile=str(self.query_one("#pf_provider", Select).value),
            review_profile=str(self.query_one("#pf_review", Select).value),
            auto_approve_profile=str(self.query_one("#pf_auto_approve", Select).value),
            generation_policy=str(self.query_one("#pf_generation_policy", Select).value),
        )

    @staticmethod
    def _first_validation_error(values: _FormValues) -> tuple[str, str] | None:
        """Return the first (message, focus-target-id) problem, if any."""
        if not values.project_id:
            return ("Project ID is required.", "#pf_id")
        if " " in values.project_id:
            return ("Project ID cannot contain spaces.", "#pf_id")
        if not ProjectForm._VALID_ID.match(values.project_id):
            return (
                "Project ID must be lowercase letters, numbers, hyphens, or underscores.",
                "#pf_id",
            )
        if not values.title:
            return ("Title is required.", "#pf_title")
        if not values.idea:
            return ("Add an idea so intake has something to work from.", "#pf_idea")
        if values.runtime_mode == "real" and values.provider_profile in {"", "mock-demo"}:
            return ("Real mode requires a non-mock provider profile.", "#pf_provider")
        return None

    @staticmethod
    def _build_request(values: _FormValues) -> ProjectCreateRequest:
        return ProjectCreateRequest(
            project_id=values.project_id,
            title=values.title,
            slug=values.project_id,
            idea=values.idea,
            runtime_mode=values.runtime_mode,
            workflow_mode="manual",
            project_kind="production",
            film_type_profile=values.film_type_profile,
            quality_profile=values.quality_profile,
            provider_profile=values.provider_profile,
            review_profile=values.review_profile,
            auto_approve_profile=values.auto_approve_profile,
            generation_policy=values.generation_policy,
        )

    def _submit(self) -> None:
        values = self._collect_form_values()
        problem = self._first_validation_error(values)
        if problem is not None:
            self._show_error(problem[0], problem[1])
            return
        error = self.query_one("#pf_error", Static)
        error.update("")
        self.dismiss(self._build_request(values))

    def _show_error(self, message: str, target_id: str) -> None:
        error = self.query_one("#pf_error", Static)
        error.update(message)
        self.query_one(target_id).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)
