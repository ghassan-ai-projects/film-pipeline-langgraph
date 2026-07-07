"""Modal dialogs for the studio screen: confirmation and revision note."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, TextArea


class ConfirmScreen(ModalScreen[bool]):
    """Simple yes/no confirmation modal."""

    CSS = """
    ConfirmScreen {
        align: center middle;
    }

    #confirm_dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        border: thick #bf616a;
        background: #11151a;
    }

    .dialog-title {
        color: #bf616a;
        text-style: bold;
        margin: 0 0 1 0;
    }

    .dialog-hint {
        color: #d8dee9;
        margin: 0 0 1 0;
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
        title: str,
        message: str,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm_dialog"):
            yield Static(self._title, classes="dialog-title")
            yield Static(self._message, classes="dialog-hint")
            with Horizontal(id="dialog_buttons"):
                yield Button("Yes", id="cf_yes", variant="error")
                yield Button("No", id="cf_no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cf_yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class RevisionForm(ModalScreen[str | None]):
    """Collect a revision note for the active phase."""

    CSS = """
    RevisionForm {
        align: center middle;
    }

    #revision_dialog {
        width: 72;
        height: auto;
        max-height: 90%;
        padding: 1 2;
        border: thick #ebcb8b;
        background: #11151a;
    }

    .dialog-title {
        color: #ebcb8b;
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

    #revision_note {
        width: 100%;
        height: 8;
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
        project_id: str,
        phase: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._project_id = project_id
        self._phase = phase

    def compose(self) -> ComposeResult:
        with Vertical(id="revision_dialog"):
            yield Static(
                f"Request Revision — {self._project_id}",
                classes="dialog-title",
            )
            yield Static(
                f"Phase: {self._phase or 'current'}. Describe what should change.",
                classes="dialog-hint",
            )
            yield Label("Revision note", classes="field-label")
            yield TextArea("", id="revision_note")
            yield Static("", id="revision_error", classes="dialog-error")
            with Horizontal(id="dialog_buttons"):
                yield Button("Submit", id="rf_submit", variant="primary")
                yield Button("Cancel", id="rf_cancel")

    def on_mount(self) -> None:
        self.query_one("#revision_note", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "rf_cancel":
            self.dismiss(None)
        elif event.button.id == "rf_submit":
            self._submit()

    def _submit(self) -> None:
        note = self.query_one("#revision_note", TextArea).text.strip()
        if not note:
            self.query_one("#revision_error", Static).update("Revision note is required.")
            return
        self.dismiss(note)

    def action_cancel(self) -> None:
        self.dismiss(None)
