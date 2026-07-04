"""Dedicated review gate screen for explicit human approval."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static


class ReviewGateScreen(Screen[None]):
    """Focused approval/revision workspace."""

    CSS = """
    #review_container {
        padding: 2 4;
        height: 1fr;
    }

    #review_title {
        color: #88c0d0;
        text-style: bold;
        height: auto;
    }

    #review_summary {
        color: #d8dee9;
        margin: 1 0;
        height: auto;
    }

    #review_actions {
        height: auto;
        margin: 1 0;
    }

    #review_actions Button {
        margin: 0 1 0 0;
    }

    #review_table {
        height: 1fr;
        border: solid #3b4252;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="review_container"):
            yield Static("Review Gate", id="review_title")
            yield Static("", id="review_summary")
            with Horizontal(id="review_actions"):
                yield Button("Approve", id="review_approve", variant="success")
                yield Button("Request Revision", id="review_revise", variant="warning")
                yield Button("Back", id="review_back")
            yield DataTable(id="review_table")

    def on_mount(self) -> None:
        table = self.query_one("#review_table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        self._refresh_view()

    def _refresh_view(self) -> None:
        from film_pipeline.tui.app import AppState, FilmStudioApp

        summary = self.query_one("#review_summary", Static)
        table = self.query_one("#review_table", DataTable)
        if not isinstance(self.app, FilmStudioApp):
            summary.update("Not running inside the film studio app.")
            return
        state = self.app.state if isinstance(self.app.state, AppState) else None
        review = state.snapshot.review if state and state.snapshot else None
        if review is None:
            summary.update("No review package available.")
            table.clear(columns=True)
            return
        summary.update(
            f"Phase: {review.phase or 'none'}\n"
            f"Recommendation: {review.recommendation}\n"
            f"Open issues: {len(review.open_issues)}"
        )
        table.clear(columns=True)
        table.add_columns("Item", "Value")
        for artifact in review.candidate_artifacts:
            table.add_row(
                str(artifact.get("artifact_id", "")),
                str(artifact.get("artifact_type", "")),
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from film_pipeline.tui.app import FilmStudioApp

        if not isinstance(self.app, FilmStudioApp):
            return
        if event.button.id == "review_back":
            self.app.pop_screen()
        elif event.button.id == "review_approve":
            try:
                result = self.app.gateway.approve_phase(self.app.active_project_id)
                self.app.set_status(f"Approved → {result.current_phase or 'done'}")
                self.app.action_refresh()
                self.app.pop_screen()
            except Exception as exc:
                self.app.set_status(f"Approval failed: {exc}")
        elif event.button.id == "review_revise":
            self.app.pop_screen()
            # The studio screen handles the revision modal flow.
            if hasattr(self.app.screen, "_request_revision"):
                self.app.screen._request_revision()
