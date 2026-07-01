"""Future-forward Textual interface for the LangGraph Film Studio.

Run with:

```
python -m film_pipeline.tui.app
```

The new studio is organized around the film pipeline itself: a stage navigator
on the left, a contextual workspace in the center, and an inspector on the
right. Common actions are always visible as buttons; the command palette
remains available for power users.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from dataclasses import dataclass, field
from typing import ClassVar

from textual.app import App
from textual.binding import Binding
from textual.widgets import Input, Static

from film_pipeline.app.services.errors import ServiceError
from film_pipeline.app.services.models import (
    ArtifactDetail,
    DashboardSummary,
    MutationResult,
    ProjectCreateRequest,
    ProjectListItem,
)
from film_pipeline.tui.gateway import StudioGateway
from film_pipeline.tui.gateways import default_gateway
from film_pipeline.tui.screens.home import ProjectGalleryScreen
from film_pipeline.tui.screens.studio import StudioScreen
from film_pipeline.tui.view_models.models import (
    GRAPH_PHASES,
    CockpitSnapshot,
    CommandOptions,
    ReaderView,
    TargetSelection,
)


@dataclass
class AppState:
    """Mutable, non-reactive holder for the current studio state.

    Textual's reactive descriptors live on the App; this dataclass is used
    internally to pass a coherent snapshot to screens and widgets without
    exposing every field as a reactive attribute.
    """

    snapshot: CockpitSnapshot | None = None
    active_project: ProjectListItem | None = None
    dashboard: DashboardSummary | None = None
    selected_stage: str = ""
    selected_target: TargetSelection | None = None
    selected_artifact: ArtifactDetail | None = None
    reader: ReaderView | None = None
    providers_healthy: int = 0
    providers_total: int = 0
    messages: list[str] = field(default_factory=list)

    def add_message(self, text: str) -> None:
        self.messages.append(text)
        if len(self.messages) > 40:
            self.messages = self.messages[-40:]


class FilmStudioApp(App[None]):
    """The redesigned film studio TUI."""

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
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, gateway: StudioGateway | None = None, *, start_create: bool = False) -> None:
        super().__init__()
        self.gateway = gateway or default_gateway()
        self.start_create = start_create
        self.state = AppState()
        self.active_project_id = ""
        self.selected_stage = ""

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
            self.state.providers_healthy = sum(
                1 for p in self.state.snapshot.providers if str(p.get("status", "")) == "healthy"
            )
            self.state.providers_total = len(self.state.snapshot.providers)
            status = (
                f"{dashboard.title}  •  {dashboard.current_phase or 'no phase'}  •  "
                f"{dashboard.status}  •  {dashboard.workflow_mode}/{dashboard.runtime_mode}  •  "
                f"providers {self.state.providers_healthy}/{self.state.providers_total}"
            )
        else:
            status = "No active project — create or open one from the home screen."
        self._set_status(status)
        self._propagate_state()

    def _load_snapshot(self) -> CockpitSnapshot:
        projects = self.gateway.list_projects()
        active = self._resolve_active_project(projects)
        self.state.active_project = active
        dashboard = self.gateway.get_dashboard(active.project_id) if active else None
        self.state.dashboard = dashboard
        project_id = dashboard.project_id if dashboard else None
        artifacts = self.gateway.list_artifacts(project_id) if project_id else []
        assets = self.gateway.list_assets(project_id) if project_id else []
        review = self.gateway.get_review_workspace(project_id) if project_id else None
        validation = self.gateway.get_validation_workspace(project_id) if project_id else None
        checkpoints = self.gateway.list_checkpoints(project_id) if project_id else []
        providers = self.gateway.list_provider_status()
        audit_events = self.gateway.get_audit_feed(project_id, limit=30) if project_id else []
        comments = self.gateway.list_operator_comments(project_id) if project_id else []
        return CockpitSnapshot(
            projects=projects,
            dashboard=dashboard,
            review=review,
            validation=validation,
            artifacts=artifacts,
            assets=assets,
            checkpoints=checkpoints,
            providers=providers,
            audit_events=audit_events,
            comments=comments,
            matrix_rows=[],
            graph_rows=[],
            command_suggestions=[],
            command_options=CommandOptions(),
        )

    def _resolve_active_project(self, projects: list[ProjectListItem]) -> ProjectListItem | None:
        if self.active_project_id:
            match = next((p for p in projects if p.project_id == self.active_project_id), None)
            if match is not None:
                return match
        live = [p for p in projects if p.status != "discovered"]
        if live:
            return live[0]
        discovered = [p for p in projects if p.status == "discovered"]
        if discovered:
            return discovered[0]
        return None

    def _propagate_state(self) -> None:
        """Push the updated app state down to whichever screen is active."""
        from film_pipeline.tui.screens.home import ProjectGalleryScreen
        from film_pipeline.tui.screens.studio import StudioScreen

        self.state.selected_stage = self.selected_stage
        current = self.screen
        if isinstance(current, (ProjectGalleryScreen, StudioScreen)) and hasattr(
            current, "update_state"
        ):
            current.update_state(self.state)
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

    def action_command_palette(self) -> None:
        """Toggle the command palette on the active screen."""
        with contextlib.suppress(Exception):
            palette = self.screen.query_one("#command_palette", Input)
            if "open" in palette.classes:
                palette.remove_class("open")
            else:
                palette.add_class("open")
                palette.focus()

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
        self.switch_screen(StudioScreen(id="studio_screen"))

    def set_selected_stage(self, stage: str) -> None:
        """Public API for child widgets to change the active stage."""
        self.selected_stage = stage
        self._propagate_state()

    def set_selected_target(self, target: TargetSelection | None) -> None:
        """Public API for child widgets to change the inspector target."""
        self.state.selected_target = target
        self._propagate_state()

    def set_status(self, message: str) -> None:
        """Public API for child widgets to update the status footer."""
        self._set_status(message)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Run a command from the palette and hide it."""
        if event.input.id != "command_palette":
            return
        self._run_command(event.value.strip())
        event.input.value = ""
        event.input.remove_class("open")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Live feedback while typing in the palette."""
        if event.input.id != "command_palette":
            return
        if event.value.strip():
            self._set_status(f"Command: {event.value}")
        else:
            self._set_status("")

    def _run_command(self, command: str) -> None:
        """Minimal power-user command dispatcher."""
        normalized = command.lower().strip()
        if not normalized:
            return
        if normalized in {"help", "commands"}:
            self._set_status(
                "Commands: next, approve, revise <note>, validate, "
                "project <id>, create, home, assets"
            )
            return
        if normalized == "home":
            self.switch_screen(ProjectGalleryScreen(id="home_screen"))
            return
        if normalized == "assets":
            from film_pipeline.tui.screens.asset_viewer import AssetViewerScreen

            self.push_screen(AssetViewerScreen(id="asset_viewer"))
            return
        if normalized == "create":
            self.action_new_project()
            return
        if normalized == "next":
            self._dispatch_to_studio("_do_next_action")
            return
        if normalized == "approve":
            self._dispatch_to_studio("_approve_phase")
            return
        if normalized == "validate":
            self._dispatch_to_studio("_run_validation")
            return
        if normalized.startswith("revise "):
            note = command.removeprefix("revise ").strip()
            self._submit_revision(note)
            return
        if normalized.startswith("project "):
            project_id = command.removeprefix("project ").strip()
            try:
                self.open_project(project_id)
            except Exception as exc:
                self._set_status(f"Could not open project: {exc}")
            return
        if normalized.startswith("stage "):
            stage = command.removeprefix("stage ").strip()
            if stage in GRAPH_PHASES:
                self.set_selected_stage(stage)
            else:
                self._set_status(f"Unknown stage: {stage}")
            return
        self._set_status(f"Unknown command: {command}. Try 'help'.")

    def _dispatch_to_studio(self, method_name: str) -> None:
        """Invoke a method on the current studio screen if it is active."""
        from film_pipeline.tui.screens.studio import StudioScreen

        screen = self.screen
        if isinstance(screen, StudioScreen) and hasattr(screen, method_name):
            getattr(screen, method_name)()
        else:
            self._set_status("Switch to the studio workspace to use this command.")

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
    """Entry point for the redesigned Textual TUI."""
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
