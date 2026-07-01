"""Compact current-node indicator for the simplified studio view."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static


class CurrentNode(Vertical):
    """Show where the project is right now and what to do next."""

    CSS = """
    CurrentNode {
        height: auto;
        border: solid #3b4252;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    #current_node_title {
        color: #88c0d0;
        text-style: bold;
        height: auto;
    }

    #current_node_body {
        height: auto;
        color: #d8dee9;
    }

    .node-blocked {
        color: #bf616a;
    }

    .node-ready {
        color: #a3be8c;
    }

    .node-warn {
        color: #ebcb8b;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Current Node", id="current_node_title")
        yield Static("Open a project to see the current node.", id="current_node_body")

    def update_state(self, app_state: object) -> None:
        """Refresh from parent app state."""
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        body = self.query_one("#current_node_body", Static)
        if state is None or state.dashboard is None:
            body.update("Open a project to see the current node.")
            return

        dashboard = state.dashboard
        phase = dashboard.current_phase or "none"
        status = dashboard.status or "unknown"
        next_action = dashboard.next_action or "none"
        issue_count = dashboard.issue_count
        blocking = len(
            state.snapshot.validation.blocking_issues
            if state.snapshot and state.snapshot.validation
            else []
        )

        status_class = "node-ready"
        if dashboard.has_blockers or blocking:
            status_class = "node-blocked"
        elif status.lower() in {"awaiting_review", "warning"}:
            status_class = "node-warn"

        lines = [
            f"Phase:    {phase}",
            f"Status:   [{status_class}]{status}[/{status_class}]",
            f"Next:     {next_action}",
        ]
        if dashboard.route_reason:
            lines.append(f"Reason:   {dashboard.route_reason}")
        if blocking:
            lines.append(f"Blockers: {blocking} blocking issue(s)")
        elif issue_count:
            lines.append(f"Issues:   {issue_count}")

        body.update("\n".join(lines))
