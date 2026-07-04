"""Primary action bar for the active stage."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Static


class ActionBar(Horizontal):
    """Shows the most relevant actions for the current stage."""

    CSS = """
    ActionBar {
        height: auto;
        margin: 0 0 1 0;
        align: left middle;
    }

    ActionBar Button {
        margin: 0 1 0 0;
    }

    #action_hint {
        color: #6b7480;
        content-align: center middle;
        height: auto;
        display: block;
    }

    .action-button {
        display: none;
    }
    """

    def __init__(self, *, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        self._actions: list[tuple[str, str, bool]] = []

    def compose(self) -> ComposeResult:
        yield Static("Open a project to see available actions.", id="action_hint")
        yield Button("Validate", id="action_validate", classes="action-button")
        yield Button("Approve Phase", id="action_approve", classes="action-button")
        yield Button("Request Revision", id="action_revise", classes="action-button")
        yield Button("Generate", id="action_generate", classes="action-button")
        yield Button("Next", id="action_next", classes="action-button")
        yield Button("Inspect", id="action_inspect", classes="action-button")

    def update_state(self, app_state: object) -> None:
        """Refresh actions from parent app state."""
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        hint = self.query_one("#action_hint", Static)
        buttons = {str(button.id): button for button in self.query(Button) if button.id is not None}

        if state is None or state.dashboard is None:
            hint.styles.display = "block"
            for button in buttons.values():
                button.styles.display = "none"
            return

        dashboard = state.dashboard
        actions: list[tuple[str, str, bool]] = []
        current_phase = dashboard.current_phase or ""
        selected = state.selected_stage or current_phase
        on_current = selected == current_phase

        if on_current:
            if dashboard.has_blockers or (
                state.snapshot
                and state.snapshot.validation
                and state.snapshot.validation.blocking_issues
            ):
                actions.append(("action_validate", "Validate", True))
            if current_phase == "generation":
                generation_complete = (
                    state.snapshot
                    and state.snapshot.generation is not None
                    and state.snapshot.generation.completed > 0
                )
                if dashboard.generation_policy == "text_only":
                    if not generation_complete:
                        actions.append(("action_generate", "Complete Text-Only", True))
                elif generation_complete and "approve_phase" in dashboard.eligible_actions:
                    actions.append(("action_generate", "Regenerate", False))
                else:
                    actions.append(("action_generate", "Generate", True))
            if "approve_phase" in dashboard.eligible_actions:
                actions.append(("action_approve", "Approve Phase", True))
            if "request_revision" in dashboard.eligible_actions:
                actions.append(("action_revise", "Request Revision", False))
            if not actions:
                actions.append(("action_next", "Next", True))
        else:
            actions.append(("action_inspect", "Inspect", True))

        hint.styles.display = "none"
        active_ids = {button_id for button_id, _, _ in actions}
        for button_id, button in buttons.items():
            if button_id in active_ids:
                button.styles.display = "block"
                button.disabled = False
            else:
                button.styles.display = "none"
                button.disabled = True

        for button_id, label, primary in actions:
            button = buttons[button_id]
            button.label = label
            button.variant = "primary" if primary else "default"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "action_inspect":
            from film_pipeline.tui.app import FilmStudioApp

            if isinstance(self.app, FilmStudioApp):
                self.app.set_selected_stage(self.app.state.selected_stage or "")
