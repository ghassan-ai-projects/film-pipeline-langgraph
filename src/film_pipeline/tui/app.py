"""Textual interface for the LangGraph Film Studio.

Run with:

```
python -m film_pipeline.tui.app
```

The studio is organized around the film pipeline itself: a compact stage rail
on the left, content tabs (scenes, artifacts, assets, issues) in the center,
and a wide reader pane on the right so scripts and scenes can be reviewed
without leaving the terminal. Common actions are always visible as buttons;
the command palette remains available for power users.

This module is the App shell: key bindings, screen wiring, project actions,
and status plumbing. Two mixins compose in the rest of the behavior —
:class:`~film_pipeline.tui.app_snapshot.SnapshotLoaderMixin` loads gateway
state and :class:`~film_pipeline.tui.app_commands.CommandPaletteMixin` runs
the command palette. The shared mutable state lives in
:mod:`film_pipeline.tui.app_state` and is re-exported here because screens
and widgets import ``AppState`` from this module.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from typing import ClassVar

from textual.app import App
from textual.binding import Binding
from textual.widgets import Input, Static

from film_pipeline.app.services.errors import ServiceError
from film_pipeline.app.services.models import MutationResult, ProjectCreateRequest
from film_pipeline.tui.app_commands import CommandPaletteMixin
from film_pipeline.tui.app_snapshot import SnapshotLoaderMixin
from film_pipeline.tui.app_state import AppState as AppState
from film_pipeline.tui.gateway import StudioGateway
from film_pipeline.tui.gateways import default_gateway
from film_pipeline.tui.screens.home import ProjectGalleryScreen
from film_pipeline.tui.screens.studio import StudioScreen
from film_pipeline.tui.view_models.models import GRAPH_PHASES, TargetSelection

__all__ = ["AppState", "FilmStudioApp", "main"]


class FilmStudioApp(SnapshotLoaderMixin, CommandPaletteMixin, App[None]):
    """The film studio TUI."""

    CSS = """
    Screen {
        background: #0b0d10;
        color: #d8dee9;
    }

    #status_footer {
        dock: bottom;
        height: 1;
        background: #1e2229;
        color: #88c0d0;
        padding: 0 1;
    }

    #command_palette {
        dock: bottom;
        display: none;
    }

    #command_palette.open {
        display: block;
    }

    .headline {
        color: #88c0d0;
        text-style: bold;
    }

    .ok { color: #a3be8c; }
    .warn { color: #ebcb8b; }
    .danger { color: #bf616a; }
    .muted { color: #6b7480; }
    """

    BINDINGS: ClassVar = [
        Binding("q", "quit", "Quit"),
        Binding("f5", "refresh", "Refresh"),
        Binding("escape", "back", "Back"),
        Binding("slash", "command_palette", "Command"),
        Binding("n", "new_project", "New Project"),
    ]

    def __init__(self, gateway: StudioGateway | None = None, *, start_create: bool = False) -> None:
        super().__init__()
        self.gateway = gateway or default_gateway()
        self.start_create = start_create
        self.state = AppState()
        self.active_project_id = ""
        self.selected_stage = ""
        self._last_seen_phase: tuple[str, str] = ("", "")

    def on_mount(self) -> None:
        self.title = "LangGraph Film Studio"
        self.sub_title = "make a movie"
        self.push_screen(ProjectGalleryScreen(id="home_screen"))
        if self.start_create:
            self.action_new_project()

    def action_refresh(self) -> None:
        """Reload snapshot state from the gateway and propagate to child widgets."""
        try:
            self.state.snapshot = self._load_snapshot()
        except (ServiceError, ValueError, FileNotFoundError) as exc:
            self.state.add_message(f"Refresh failed: {exc}")
            self._set_status(f"Refresh failed: {exc}")
            return

        dashboard = self.state.dashboard
        if dashboard is not None:
            self.active_project_id = dashboard.project_id
            current_phase = dashboard.current_phase or ""
            if (not self.selected_stage and current_phase) or (
                current_phase and self.selected_stage not in GRAPH_PHASES
            ):
                self.selected_stage = current_phase
            self._follow_phase(dashboard.project_id, current_phase)
            self.state.providers_healthy = sum(
                1 for p in self.state.snapshot.providers if str(p.get("status", "")) == "healthy"
            )
            self.state.providers_total = len(self.state.snapshot.providers)
            status = (
                f"{dashboard.title}  •  {dashboard.current_phase or 'no phase'}  •  "
                f"{dashboard.status}  •  "
                f"providers {self.state.providers_healthy}/{self.state.providers_total}"
            )
        else:
            status = "No active project — create or open one from the home screen."
        self._set_status(status)
        self._propagate_state()

    def _follow_phase(self, project_id: str, current_phase: str) -> None:
        """Snap the selected stage forward when the pipeline advances.

        Keeps the workspace on the stage the film is actually at after an
        approval, instead of staying on the stage that was just approved.
        """
        last_project, last_phase = self._last_seen_phase
        if (
            current_phase
            and last_project == project_id
            and last_phase
            and last_phase != current_phase
            and self.selected_stage == last_phase
        ):
            self.selected_stage = current_phase
            self.state.reader = None
            self.state.selected_target = None
            self.state.selected_artifact = None
        self._last_seen_phase = (project_id, current_phase)

    def _propagate_state(self) -> None:
        """Push the updated app state down to every screen that renders it."""
        self.state.selected_stage = self.selected_stage
        for screen in self.screen_stack:
            update = getattr(screen, "update_state", None)
            if callable(update):
                update(self.state)
        with contextlib.suppress(Exception):
            self.screen.query_one("#status_footer", Static).update(self._status_text())

    def _set_status(self, message: str) -> None:
        self.state.add_message(message)
        with contextlib.suppress(Exception):
            self.screen.query_one("#status_footer", Static).update(message)

    def _status_text(self) -> str:
        return self.state.messages[-1] if self.state.messages else ""

    def action_new_project(self) -> None:
        """Open the new-project modal from anywhere."""
        current = self.screen
        if isinstance(current, ProjectGalleryScreen):
            current.action_new_project()
        else:
            self.switch_screen(ProjectGalleryScreen(id="home_screen"))
            if isinstance(self.screen, ProjectGalleryScreen):
                self.screen.action_new_project()

    async def action_back(self) -> None:
        """Return to the project gallery (or close the command palette)."""
        with contextlib.suppress(Exception):
            palette = self.screen.query_one("#command_palette", Input)
            if "open" in palette.classes:
                palette.remove_class("open")
                return
        if len(self.screen_stack) > 1:
            await self.pop_screen()
            if isinstance(self.screen, ProjectGalleryScreen):
                return
        if len(self.screen_stack) <= 1:
            await self.push_screen(ProjectGalleryScreen(id="home_screen"))
        else:
            await self.switch_screen(ProjectGalleryScreen(id="home_screen"))

    def create_project(self, request: ProjectCreateRequest) -> MutationResult:
        """Create a project, run intake if needed, and switch to the studio."""
        try:
            result = self.gateway.create_project(request)
        except Exception as exc:
            self._set_status(f"Failed to create project: {exc}")
            return MutationResult(
                ok=False,
                project_id=request.project_id,
                current_phase="",
                message=str(exc),
            )
        self.active_project_id = result.project_id
        if request.idea.strip() and not result.current_phase:
            try:
                result = self.gateway.submit_idea(request.project_id, request.idea.strip())
            except Exception as exc:
                self._set_status(f"Project created, but intake failed: {exc}")
        self.selected_stage = result.current_phase or ""
        self.switch_screen(StudioScreen(id="studio_screen"))
        return result

    def open_project(self, project_id: str) -> None:
        """Open an existing project and switch to the studio."""
        dashboard = self.gateway.set_active_project(project_id)
        self.active_project_id = dashboard.project_id
        self.selected_stage = dashboard.current_phase or ""
        self.state.reader = None
        self.state.selected_target = None
        self.state.selected_artifact = None
        if isinstance(self.screen, StudioScreen):
            self.action_refresh()
        else:
            self.switch_screen(StudioScreen(id="studio_screen"))

    def set_selected_stage(self, stage: str) -> None:
        """Public API for child widgets to change the active stage."""
        self.selected_stage = stage
        self._propagate_state()

    def set_selected_target(self, target: TargetSelection | None) -> None:
        """Public API for child widgets to change the reader target."""
        self.state.selected_target = target
        self._propagate_state()

    def set_status(self, message: str) -> None:
        """Public API for child widgets to update the status footer."""
        self._set_status(message)

    def _submit_revision(self, note: str) -> None:
        """Submit a revision note directly from the command palette."""
        if not self.active_project_id:
            self._set_status("No active project.")
            return
        if not note.strip():
            self._set_status("Revision note cannot be empty.")
            return
        try:
            result = self.gateway.request_revision(note.strip(), self.active_project_id)
            self._set_status(f"Revision requested → {result.current_phase}")
            self.action_refresh()
        except Exception as exc:
            self._set_status(f"Revision failed: {exc}")


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Textual TUI."""
    parser = argparse.ArgumentParser(description="Run the LangGraph Film Studio TUI.")
    parser.add_argument("--create", action="store_true", help="Open the create-project form.")
    parser.add_argument(
        "--real",
        action="store_true",
        dest="real_mode",
        help="Start the MCP server in real mode (live model generation).",
    )
    args = parser.parse_args(argv)
    if args.real_mode:
        os.environ["FILM_PIPELINE_MCP_MODE"] = "real"
    os.environ["FILM_PIPELINE_PERSIST_STATE"] = "1"
    FilmStudioApp(start_create=args.create).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
