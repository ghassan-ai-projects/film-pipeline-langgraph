"""Modal form for creating a new film project."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, TextArea

from film_pipeline.app.services.models import ProjectCreateRequest


class ProjectForm(ModalScreen[ProjectCreateRequest | None]):
    """Collect the minimum fields needed to create a new project."""

    CSS = """
    ProjectForm {
        align: center middle;
    }

    #dialog {
        width: 72;
        height: auto;
        max-height: 90%;
        padding: 1 2;
        border: thick #88c0d0;
        background: #11151a;
    }

    .dialog-title {
        color: #88c0d0;
        text-style: bold;
        margin: 0 0 1 0;
    }

    .dialog-hint {
        color: #6b7480;
        margin: 0 0 1 0;
    }

    .field-label {
        color: #d8dee9;
        margin: 1 0 0 0;
    }

    #dialog Input, #dialog Select {
        width: 100%;
    }

    #dialog TextArea {
        width: 100%;
        height: 6;
    }

    .dialog-error {
        color: #bf616a;
        margin: 1 0 0 0;
    }

    #dialog_buttons {
        height: auto;
        margin: 1 0 0 0;
    }

    #dialog_buttons Button {
        margin: 0 1 0 0;
    }
    """

    BINDINGS: ClassVar = [Binding("escape", "cancel", "Cancel")]

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
            yield Static("New Project", classes="dialog-title")
            yield Static(
                "Give your film an id, a title, and a short idea.",
                classes="dialog-hint",
            )
            yield Label("Project ID", classes="field-label")
            yield Input(
                value=self._default_id,
                placeholder="e.g. lighthouse-keeper (lowercase, no spaces)",
                id="pf_id",
            )
            yield Label("Title", classes="field-label")
            yield Input(placeholder="e.g. The Lighthouse Keeper", id="pf_title")
            yield Label("Idea / logline", classes="field-label")
            yield TextArea(self._default_idea, id="pf_idea")
            yield Label("Runtime mode", classes="field-label")
            yield Select(
                [
                    ("mock — fast, free, no model calls", "mock"),
                    ("real — live model generation", "real"),
                ],
                value="mock",
                allow_blank=False,
                id="pf_runtime",
            )
            yield Label("Film type profile", classes="field-label")
            yield Select(
                [
                    ("narrative", "film-type.narrative"),
                    ("visual poetry", "film-type.visual_poetry"),
                ],
                value="film-type.narrative",
                allow_blank=False,
                id="pf_film_type",
            )
            yield Label("Quality profile", classes="field-label")
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
            yield Label("Provider profile", classes="field-label")
            yield Select(
                [
                    ("mock demo", "mock-demo"),
                    ("seedance primary", "provider.seedance_primary"),
                    ("free / low cost", "provider.free_or_low_cost"),
                    ("local real provider", "local-real-provider"),
                ],
                value="mock-demo",
                allow_blank=False,
                id="pf_provider",
            )
            yield Label("Review profile", classes="field-label")
            yield Select(
                [("strict continuity", "review.strict_continuity")],
                value="review.strict_continuity",
                allow_blank=False,
                id="pf_review",
            )
            yield Label("Auto-approve profile (optional)", classes="field-label")
            yield Select(
                [("none", ""), ("auto-approve", "auto-approve")],
                value="",
                allow_blank=False,
                id="pf_auto_approve",
            )
            yield Static("", id="pf_error", classes="dialog-error")
            with Horizontal(id="dialog_buttons"):
                yield Button("Create", id="pf_create", variant="primary")
                yield Button("Cancel", id="pf_cancel")

    def on_mount(self) -> None:
        self.query_one("#pf_id", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pf_cancel":
            self.dismiss(None)
        elif event.button.id == "pf_create":
            self._submit()

    def _submit(self) -> None:
        project_id = self.query_one("#pf_id", Input).value.strip()
        title = self.query_one("#pf_title", Input).value.strip()
        idea = self.query_one("#pf_idea", TextArea).text.strip()
        runtime_mode = str(self.query_one("#pf_runtime", Select).value)
        film_type_profile = str(self.query_one("#pf_film_type", Select).value)
        quality_profile = str(self.query_one("#pf_quality", Select).value)
        provider_profile = str(self.query_one("#pf_provider", Select).value)
        review_profile = str(self.query_one("#pf_review", Select).value)
        auto_approve_profile = str(self.query_one("#pf_auto_approve", Select).value)
        error = self.query_one("#pf_error", Static)
        if not project_id:
            error.update("Project ID is required.")
            self.query_one("#pf_id", Input).focus()
            return
        if " " in project_id:
            error.update("Project ID cannot contain spaces.")
            self.query_one("#pf_id", Input).focus()
            return
        if not title:
            error.update("Title is required.")
            self.query_one("#pf_title", Input).focus()
            return
        if not idea:
            error.update("Add an idea so intake has something to work from.")
            self.query_one("#pf_idea", TextArea).focus()
            return
        self.dismiss(
            ProjectCreateRequest(
                project_id=project_id,
                title=title,
                slug=project_id,
                idea=idea,
                runtime_mode=runtime_mode,
                workflow_mode="manual",
                project_kind="production",
                film_type_profile=film_type_profile,
                quality_profile=quality_profile,
                provider_profile=provider_profile,
                review_profile=review_profile,
                auto_approve_profile=auto_approve_profile,
            )
        )

    def action_cancel(self) -> None:
        self.dismiss(None)
