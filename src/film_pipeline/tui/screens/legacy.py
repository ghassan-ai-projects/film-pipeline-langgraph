"""Legacy modal screens used by the operator cockpit.

These keep multi-field operator input (creating a project, revising an idea)
out of the single-line command palette so the most common production actions
are fast and hard to get wrong.
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, TextArea

from film_pipeline.app.services.models import ProjectCreateRequest

_DIALOG_CSS = """
NewProjectScreen, ReviseIdeaScreen {
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


class NewProjectScreen(ModalScreen[ProjectCreateRequest | None]):
    """Collect the fields needed to create and run a new project."""

    CSS = _DIALOG_CSS

    BINDINGS: ClassVar = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, *, default_id: str = "", default_idea: str = "") -> None:
        super().__init__()
        self._default_id = default_id
        self._default_idea = default_idea

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("New Project", classes="dialog-title")
            yield Static(
                "Give it an id, a title, and your idea, then pick how to run it.",
                classes="dialog-hint",
            )
            yield Label("Project ID", classes="field-label")
            yield Input(
                value=self._default_id,
                placeholder="e.g. lighthouse-keeper (lowercase, no spaces)",
                id="np_id",
            )
            yield Label("Title", classes="field-label")
            yield Input(placeholder="e.g. The Lighthouse Keeper", id="np_title")
            yield Label("Idea / logline", classes="field-label")
            yield TextArea(self._default_idea, id="np_idea")
            yield Label("Runtime mode", classes="field-label")
            yield Select(
                [
                    ("mock — fast, free, no model calls", "mock"),
                    ("real — live model generation", "real"),
                ],
                value="mock",
                allow_blank=False,
                id="np_runtime",
            )
            yield Label("Project kind", classes="field-label")
            yield Select(
                [
                    ("production", "production"),
                    ("test", "test"),
                ],
                value="production",
                allow_blank=False,
                id="np_kind",
            )
            yield Static("", id="np_error", classes="dialog-error")
            with Horizontal(id="dialog_buttons"):
                yield Button("Create", id="np_create", variant="primary")
                yield Button("Cancel", id="np_cancel")

    def on_mount(self) -> None:
        self.query_one("#np_id", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "np_cancel":
            self.dismiss(None)
        elif event.button.id == "np_create":
            self._submit()

    def _submit(self) -> None:
        project_id = self.query_one("#np_id", Input).value.strip()
        title = self.query_one("#np_title", Input).value.strip()
        idea = self.query_one("#np_idea", TextArea).text.strip()
        runtime_mode = str(self.query_one("#np_runtime", Select).value)
        project_kind = str(self.query_one("#np_kind", Select).value)
        error = self.query_one("#np_error", Static)
        if not project_id:
            error.update("Project ID is required.")
            self.query_one("#np_id", Input).focus()
            return
        if " " in project_id:
            error.update("Project ID cannot contain spaces.")
            self.query_one("#np_id", Input).focus()
            return
        if not title:
            error.update("Title is required.")
            self.query_one("#np_title", Input).focus()
            return
        if not idea:
            error.update("Add an idea so intake has something to work from.")
            self.query_one("#np_idea", TextArea).focus()
            return
        self.dismiss(
            ProjectCreateRequest(
                project_id=project_id,
                title=title,
                slug=project_id,
                idea=idea,
                runtime_mode=runtime_mode,
                workflow_mode="manual",
                project_kind=project_kind,
            )
        )

    def action_cancel(self) -> None:
        self.dismiss(None)


class ReviseIdeaScreen(ModalScreen[str | None]):
    """Replace a project's idea and re-run intake."""

    CSS = _DIALOG_CSS

    BINDINGS: ClassVar = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, *, project_id: str, current_idea: str = "") -> None:
        super().__init__()
        self._project_id = project_id
        self._current_idea = current_idea

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"Revise Idea — {self._project_id}", classes="dialog-title")
            yield Static(
                "Editing the idea re-runs intake on this project.",
                classes="dialog-hint",
            )
            yield Label("Idea / logline", classes="field-label")
            yield TextArea(self._current_idea, id="ri_idea")
            yield Static("", id="ri_error", classes="dialog-error")
            with Horizontal(id="dialog_buttons"):
                yield Button("Submit & Re-run", id="ri_submit", variant="primary")
                yield Button("Cancel", id="ri_cancel")

    def on_mount(self) -> None:
        self.query_one("#ri_idea", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ri_cancel":
            self.dismiss(None)
        elif event.button.id == "ri_submit":
            self._submit()

    def _submit(self) -> None:
        idea = self.query_one("#ri_idea", TextArea).text.strip()
        if not idea:
            self.query_one("#ri_error", Static).update("Idea cannot be empty.")
            return
        self.dismiss(idea)

    def action_cancel(self) -> None:
        self.dismiss(None)
