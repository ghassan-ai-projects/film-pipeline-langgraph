"""Compact film/project metadata panel for the simplified studio view."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static


class FilmMeta(Vertical):
    """Show the high-level film metadata and selected profile stack."""

    CSS = """
    FilmMeta {
        height: auto;
        border: solid #3b4252;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    #film_meta_title {
        color: #88c0d0;
        text-style: bold;
        height: auto;
    }

    #film_meta_body {
        height: auto;
        color: #d8dee9;
    }

    .meta-muted {
        color: #6b7480;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Film", id="film_meta_title")
        yield Static("Open a project to see film metadata.", id="film_meta_body")

    def update_state(self, app_state: object) -> None:
        """Refresh from parent app state."""
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        body = self.query_one("#film_meta_body", Static)
        if state is None or state.dashboard is None:
            body.update("Open a project to see film metadata.")
            return

        dashboard = state.dashboard
        lines = [f"Title:  {dashboard.title}"]
        if dashboard.idea:
            idea = dashboard.idea
            if len(idea) > 80:
                idea = idea[:77] + "..."
            lines.append(f"Idea:   {idea}")
        lines.append(f"Mode:   {dashboard.workflow_mode} / {dashboard.runtime_mode}")
        if dashboard.profile_stack:
            lines.append("Profiles:")
            label_map = {
                "film_type_profile": "type",
                "quality_profile": "quality",
                "provider_profile": "provider",
                "review_profile": "review",
                "auto_approve_profile": "auto-approve",
            }
            for key, label in label_map.items():
                value = dashboard.profile_stack.get(key, "")
                if value:
                    lines.append(f"  {label}: {value}")
        body.update("\n".join(lines))
