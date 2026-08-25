"""Command-palette handling for the studio TUI.

Split from :mod:`film_pipeline.tui.app`: everything typed into the ``/``
command palette — parsing, dispatch, and palette input events — lives here,
while :class:`FilmStudioApp` keeps the shell, bindings, and screen actions.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from textual.app import App
from textual.widgets import Input

from film_pipeline.app.services.models import ProjectCreateRequest
from film_pipeline.tui.screens.home import ProjectGalleryScreen
from film_pipeline.tui.screens.studio import StudioScreen
from film_pipeline.tui.view_models.models import GRAPH_PHASES

if TYPE_CHECKING:
    from film_pipeline.app.services.models import MutationResult


def parse_create_request(command: str) -> ProjectCreateRequest | None:
    """Parse a ``create <id> | <title> | <idea>[ | <mode>][ | <policy>]`` palette command.

    Returns ``None`` when the text is not a well-formed create command. The
    prefix check runs on the lowercased, trimmed form while the payload is
    split from the raw ``command``, matching the palette's historical
    behavior for mixed-case input.
    """
    normalized = command.lower().strip()
    if not normalized.startswith("create "):
        return None
    parts = command.removeprefix("create ").split(" | ")
    if len(parts) < 3:
        return None
    return ProjectCreateRequest(
        project_id=parts[0].strip(),
        title=parts[1].strip(),
        slug=parts[0].strip(),
        idea=parts[2].strip(),
        runtime_mode=parts[3].strip() if len(parts) >= 4 else "mock",
        workflow_mode="manual",
        project_kind="production",
        generation_policy=parts[4].strip() if len(parts) >= 5 else "generate",
    )


class CommandPaletteMixin(App[None]):
    """Methods that run and render the command palette for the app.

    Subclasses ``App`` so App-provided members (``screen``, ``switch_screen``,
    ...) type-check naturally; the type-only stubs below name the remaining
    members that the composing :class:`FilmStudioApp` provides. The stubs are
    guarded by ``TYPE_CHECKING`` so they do not exist at runtime and cannot
    shadow the real implementations.
    """

    if TYPE_CHECKING:

        def action_new_project(self) -> None: ...

        def create_project(self, request: ProjectCreateRequest) -> MutationResult: ...

        def open_project(self, project_id: str) -> None: ...

        def set_selected_stage(self, stage: str) -> None: ...

        def _set_status(self, message: str) -> None: ...

        def _submit_revision(self, note: str) -> None: ...

    def action_command_palette(self) -> None:
        """Toggle the command palette on the active screen."""
        with contextlib.suppress(Exception):
            palette = self.screen.query_one("#command_palette", Input)
            if "open" in palette.classes:
                palette.remove_class("open")
            else:
                palette.add_class("open")
                palette.focus()

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
        handled = (
            self._show_command_help(normalized)
            or self._navigate_for_command(normalized)
            or self._create_from_command(command)
            or self._dispatch_studio_action(normalized)
            or self._apply_command_target(command, normalized)
        )
        if not handled:
            self._set_status(f"Unknown command: {command}. Try 'help'.")

    def _show_command_help(self, normalized: str) -> bool:
        if normalized not in {"help", "commands"}:
            return False
        self._set_status(
            "Commands: next, approve, revise <note>, validate, generate, "
            "project <id>, stage <name>, create, home, assets"
        )
        return True

    def _navigate_for_command(self, normalized: str) -> bool:
        if normalized == "home":
            self.switch_screen(ProjectGalleryScreen(id="home_screen"))
            return True
        if normalized == "assets":
            self._show_studio_tab("tab_assets")
            return True
        if normalized == "create":
            self.action_new_project()
            return True
        return False

    def _create_from_command(self, command: str) -> bool:
        request = parse_create_request(command)
        if request is None:
            return False
        self.create_project(request)
        return True

    def _dispatch_studio_action(self, normalized: str) -> bool:
        studio_actions: dict[str, str] = {
            "next": "_do_next_action",
            "approve": "_approve_phase",
            "validate": "_run_validation",
            "generate": "_run_generation",
        }
        method_name = studio_actions.get(normalized)
        if method_name is None:
            return False
        self._dispatch_to_studio(method_name)
        return True

    def _apply_command_target(self, command: str, normalized: str) -> bool:
        if normalized.startswith("revise "):
            note = command.removeprefix("revise ").strip()
            self._submit_revision(note)
            return True
        if normalized.startswith("project "):
            project_id = command.removeprefix("project ").strip()
            try:
                self.open_project(project_id)
            except Exception as exc:
                self._set_status(f"Could not open project: {exc}")
            return True
        if normalized.startswith("stage "):
            stage = command.removeprefix("stage ").strip()
            if stage in GRAPH_PHASES:
                self.set_selected_stage(stage)
            else:
                self._set_status(f"Unknown stage: {stage}")
            return True
        return False

    def _show_studio_tab(self, tab_id: str) -> None:
        """Switch the studio content tabs, if the studio is active."""
        screen = self.screen
        if isinstance(screen, StudioScreen):
            screen.action_show_tab(tab_id)
        else:
            self._set_status("Open a project to browse its assets.")

    def _dispatch_to_studio(self, method_name: str) -> None:
        """Invoke a method on the current studio screen if it is active."""
        screen = self.screen
        if isinstance(screen, StudioScreen) and hasattr(screen, method_name):
            getattr(screen, method_name)()
        else:
            self._set_status("Switch to the studio workspace to use this command.")
