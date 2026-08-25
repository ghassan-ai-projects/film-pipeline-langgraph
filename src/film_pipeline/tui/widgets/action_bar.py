"""Primary action bar for the active stage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Static

if TYPE_CHECKING:
    from film_pipeline.app.services.models import DashboardSummary
    from film_pipeline.tui.app import AppState


class ActionBar(Horizontal):
    """Shows only the actions that are eligible right now."""

    DEFAULT_CSS = """
    ActionBar {
        height: auto;
        align: left middle;
    }

    ActionBar Button {
        margin: 0 1 0 0;
    }

    #action_hint {
        color: #6b7480;
        height: auto;
    }

    .action-button {
        display: none;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Open a project to see available actions.", id="action_hint")
        yield Button("Validate", id="action_validate", classes="action-button")
        yield Button("Approve Phase", id="action_approve", classes="action-button")
        yield Button("Request Revision", id="action_revise", classes="action-button")
        yield Button("Generate", id="action_generate", classes="action-button")
        yield Button("Next", id="action_next", classes="action-button")

    def update_state(self, app_state: object) -> None:
        """Refresh actions from parent app state."""
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        hint = self.query_one("#action_hint", Static)
        buttons = {str(button.id): button for button in self.query(Button) if button.id is not None}

        if state is None or state.dashboard is None:
            self._show_empty_state(hint, buttons)
            return

        actions = self._stage_actions(state, hint, state.dashboard)
        self._apply_button_states(buttons, actions)

    @staticmethod
    def _show_empty_state(hint: Static, buttons: dict[str, Button]) -> None:
        hint.update("Open a project to see available actions.")
        hint.styles.display = "block"
        for button in buttons.values():
            button.styles.display = "none"

    @staticmethod
    def _generation_action(
        dashboard: DashboardSummary, state: AppState
    ) -> tuple[str, str, bool] | None:
        """Return the generate-button action for the generation stage, if due."""
        if dashboard.current_phase != "generation":
            return None
        generation_complete = (
            state.snapshot
            and state.snapshot.generation is not None
            and state.snapshot.generation.completed > 0
        )
        if dashboard.generation_policy == "text_only":
            if not generation_complete:
                return ("action_generate", "Complete Text-Only", True)
            return None
        if generation_complete and "approve_phase" in dashboard.eligible_actions:
            return ("action_generate", "Regenerate", False)
        return ("action_generate", "Generate", True)

    @staticmethod
    def _stage_actions(
        state: AppState, hint: Static, dashboard: DashboardSummary
    ) -> list[tuple[str, str, bool]]:
        """Collect eligible actions for the viewed stage and update the hint."""
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
            generate_action = ActionBar._generation_action(dashboard, state)
            if current_phase == "generation" and generate_action is not None:
                actions.append(generate_action)
            if "approve_phase" in dashboard.eligible_actions:
                actions.append(("action_approve", "Approve Phase", True))
            if "request_revision" in dashboard.eligible_actions:
                actions.append(("action_revise", "Request Revision", False))
            if not actions:
                actions.append(("action_next", "Next", True))
            hint.styles.display = "none"
        else:
            hint.update("Viewing a past stage — actions apply to the current stage.")
            hint.styles.display = "block"

        return actions

    @staticmethod
    def _apply_button_states(
        buttons: dict[str, Button], actions: list[tuple[str, str, bool]]
    ) -> None:
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
