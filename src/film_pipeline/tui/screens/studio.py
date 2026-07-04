"""Main studio workspace screen."""

from __future__ import annotations

import time
from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.containers import Horizontal as ModalHorizontal
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, Static
from textual.widgets import Button as ModalButton
from textual.widgets import Label as ModalLabel
from textual.widgets import Static as ModalStatic
from textual.widgets import TextArea as ModalTextArea

from film_pipeline.tui.view_models.models import GRAPH_PHASES, ReaderView
from film_pipeline.tui.widgets.action_bar import ActionBar
from film_pipeline.tui.widgets.artifact_list import ArtifactList
from film_pipeline.tui.widgets.asset_browser import AssetBrowser
from film_pipeline.tui.widgets.current_node import CurrentNode
from film_pipeline.tui.widgets.film_meta import FilmMeta
from film_pipeline.tui.widgets.inspector import Inspector
from film_pipeline.tui.widgets.issue_list import IssueList
from film_pipeline.tui.widgets.scene_browser import SceneBrowser
from film_pipeline.tui.widgets.stage_nav import StageNav

_STAGE_EXPLANATIONS: dict[str, str] = {
    "intake": "Capture the idea and route it into the pipeline.",
    "constitution": "Define the film's voice, rules, and creative boundaries.",
    "development": "Shape story, characters, and world before writing scenes.",
    "script": "Write and review the screenplay scene by scene.",
    "visual_dev": "Establish look, style, references, and environments.",
    "shot_bible": "Plan shots, camera, and continuity for every scene.",
    "gen_planning": "Prepare prompts and budgets for generation.",
    "generation": "Generate images, clips, and other media assets.",
    "qc": "Quality-check outputs against the constitution and script.",
    "post": "Edit, sound design, subtitle, and assemble the final cut.",
    "delivery": "Package the finished film and assets for export.",
}


class StudioScreen(Screen[None]):
    """The main single-screen workspace for the active project."""

    CSS = """
    #studio_layout {
        height: 1fr;
    }

    #left_rail {
        width: 26;
        border: solid #2e3440;
        padding: 0 1;
    }

    #center_workspace {
        width: 1fr;
        border: solid #3b4252;
        padding: 1 2;
    }

    #right_drawer {
        width: 38;
        border: solid #2e3440;
        padding: 0 1;
    }

    #stage_header {
        height: auto;
        margin: 0 0 1 0;
    }

    #stage_name {
        color: #88c0d0;
        text-style: bold;
        height: auto;
    }

    #stage_explanation {
        color: #6b7480;
        height: auto;
    }

    #stage_body {
        height: 1fr;
    }

    #workspace_left {
        width: 1fr;
        height: 1fr;
    }

    #workspace_right {
        width: 1fr;
        height: 1fr;
    }

    .panel {
        border: solid #3b4252;
        padding: 0 1;
        margin: 0 0 1 0;
        height: 1fr;
    }

    #top_bar {
        height: auto;
        margin: 0 0 1 0;
    }

    #view_toggle {
        width: auto;
        margin: 0 0 0 1;
    }

    #advanced_workspace {
        height: 1fr;
    }

    #simplified_workspace {
        height: 1fr;
        display: none;
    }

    #simplified_top {
        height: auto;
    }

    #simplified_top CurrentNode {
        width: 1fr;
    }

    #simplified_top FilmMeta {
        width: 1fr;
    }

    #simplified_bottom {
        height: 1fr;
    }

    #simplified_bottom AssetBrowser {
        width: 1fr;
    }

    #simplified_bottom SceneBrowser {
        width: 1fr;
    }
    """

    BINDINGS: ClassVar = [
        Binding("a", "approve", "Approve"),
        Binding("v", "validate", "Validate"),
        Binding("g", "generate", "Generate"),
        Binding("escape", "home", "Home"),
    ]

    _app_state: object | None = None

    def on_mount(self) -> None:
        from film_pipeline.tui.app import FilmStudioApp

        if isinstance(self.app, FilmStudioApp):
            self.app.action_refresh()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="studio_layout"):
            with Vertical(id="left_rail"):
                yield StageNav(id="stage_nav")
            with Vertical(id="center_workspace"):
                with Vertical(id="stage_header"):
                    yield Static("No project loaded", id="stage_name")
                    yield Static("Open or create a project to begin.", id="stage_explanation")
                with Horizontal(id="top_bar"):
                    yield ActionBar(id="action_bar")
                    yield Button("Simplified view", id="view_toggle")
                with Horizontal(id="advanced_workspace"):
                    with Vertical(id="workspace_left"):
                        yield Static("Artifacts", id="artifact_header", classes="headline")
                        yield ArtifactList(id="artifact_list")
                    with Vertical(id="workspace_right"):
                        yield Static("Issues", id="issue_header", classes="headline")
                        yield IssueList(id="issue_list")
                with Vertical(id="simplified_workspace"):
                    with Horizontal(id="simplified_top"):
                        yield CurrentNode(id="current_node")
                        yield FilmMeta(id="film_meta")
                    with Horizontal(id="simplified_bottom"):
                        yield AssetBrowser(id="asset_browser")
                        yield SceneBrowser(id="scene_browser")
            with Vertical(id="right_drawer"):
                yield Inspector(id="inspector")
        yield Static("", id="status_footer")
        yield Input(
            placeholder="Command palette: try 'next', 'approve', 'validate', 'project <id>'",
            id="command_palette",
        )
        yield Footer()

    def update_state(self, app_state: object) -> None:
        """Refresh the workspace from parent app state."""
        self._app_state = app_state
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        name = self.query_one("#stage_name", Static)
        explanation = self.query_one("#stage_explanation", Static)
        if state is None or state.dashboard is None:
            name.update("No project loaded")
            explanation.update("Open or create a project to begin.")
            return

        stage = state.selected_stage or state.dashboard.current_phase or ""
        if stage not in GRAPH_PHASES:
            stage = state.dashboard.current_phase or ""
        label = stage.replace("_", " ").title()
        current = state.dashboard.current_phase or ""
        label = f"▸ {label} (current)" if stage == current else f"{label} (past)"
        name.update(label)
        explanation.update(_STAGE_EXPLANATIONS.get(stage, "Inspect artifacts and issues."))

        action_bar = self.query_one("#action_bar", ActionBar)
        action_bar.update_state(state)
        artifact_list = self.query_one("#artifact_list", ArtifactList)
        artifact_list.update_state(state)
        issue_list = self.query_one("#issue_list", IssueList)
        issue_list.update_state(state)
        inspector = self.query_one("#inspector", Inspector)
        inspector.update_state(state)
        nav = self.query_one("#stage_nav", StageNav)
        nav.update_state(state)
        current_node = self.query_one("#current_node", CurrentNode)
        current_node.update_state(state)
        film_meta = self.query_one("#film_meta", FilmMeta)
        film_meta.update_state(state)
        asset_browser = self.query_one("#asset_browser", AssetBrowser)
        asset_browser.update_state(state)
        scene_browser = self.query_one("#scene_browser", SceneBrowser)
        scene_browser.update_state(state)

        # If the project has just been created and there are no artifacts yet,
        # surface the idea in the inspector so the intake screen is not blank.
        if (
            state.dashboard is not None
            and state.dashboard.idea
            and state.reader is None
            and (not state.snapshot or not state.snapshot.artifacts)
        ):
            state.reader = ReaderView(
                title="Idea",
                subtitle=state.dashboard.title,
                body=state.dashboard.idea,
                outline=[],
                metadata={},
                linked_comments=[],
                linked_validation=[],
            )
            inspector.update_state(state)

    def action_approve(self) -> None:
        """Keybinding action for approving the current phase."""
        self._approve_phase()

    def action_validate(self) -> None:
        """Keybinding action for running validation."""
        self._run_validation()

    def action_generate(self) -> None:
        """Keybinding action for running the generation batch."""
        self._run_generation()

    async def action_home(self) -> None:
        """Keybinding action to return to the project gallery."""
        from film_pipeline.tui.app import FilmStudioApp

        if isinstance(self.app, FilmStudioApp):
            await self.app.action_back()

    def action_toggle_view(self) -> None:
        """Switch between advanced (stage-centric) and simplified (asset/scene) views."""
        advanced = self.query_one("#advanced_workspace", Horizontal)
        simplified = self.query_one("#simplified_workspace", Vertical)
        toggle = self.query_one("#view_toggle", Button)
        if advanced.styles.display == "none":
            advanced.styles.display = "block"
            simplified.styles.display = "none"
            toggle.label = "Simplified view"
        else:
            advanced.styles.display = "none"
            simplified.styles.display = "block"
            toggle.label = "Advanced view"
        self.update_state(self._app_state)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "action_approve":
            self._approve_phase()
        elif event.button.id == "action_revise":
            self._request_revision()
        elif event.button.id == "action_validate":
            self._run_validation()
        elif event.button.id == "action_generate":
            self._run_generation()
        elif event.button.id == "action_next":
            self._do_next_action()
        elif event.button.id == "view_toggle":
            self.action_toggle_view()

    def _approve_phase(self) -> None:
        from film_pipeline.tui.app import AppState, FilmStudioApp

        if not isinstance(self.app, FilmStudioApp) or not isinstance(self._app_state, AppState):
            return
        if self._app_state.dashboard is None:
            self.app.set_status("No active project.")
            return
        if "approve_phase" not in self._app_state.dashboard.eligible_actions:
            self.app.set_status("Approval is not eligible right now.")
            return
        try:
            result = self.app.gateway.approve_phase(self.app.active_project_id)
            self.app.action_refresh()
            self.app.set_status(
                f"Phase approved: {result.message} → {result.current_phase or 'done'}"
            )
        except Exception as exc:
            self.app.set_status(f"Approval failed: {exc}")

    def _request_revision(self) -> None:
        from film_pipeline.tui.app import AppState, FilmStudioApp

        if not isinstance(self.app, FilmStudioApp) or not isinstance(self._app_state, AppState):
            return
        if self._app_state.dashboard is None:
            self.app.set_status("No active project.")
            return
        self.app.push_screen(
            RevisionForm(
                project_id=self._app_state.dashboard.project_id,
                phase=self._app_state.dashboard.current_phase or "",
            ),
            self._on_revision_result,
        )

    def _on_revision_result(self, note: object) -> None:
        from film_pipeline.tui.app import FilmStudioApp

        if not isinstance(note, str) or not note.strip() or not isinstance(self.app, FilmStudioApp):
            return
        try:
            result = self.app.gateway.request_revision(note.strip(), self.app.active_project_id)
            self.app.set_status(f"Revision requested: {result.message} → {result.current_phase}")
            self.app.action_refresh()
        except Exception as exc:
            self.app.set_status(f"Revision failed: {exc}")

    def _run_validation(self) -> None:
        from film_pipeline.tui.app import AppState, FilmStudioApp

        if not isinstance(self.app, FilmStudioApp) or not isinstance(self._app_state, AppState):
            return
        if self._app_state.dashboard is None:
            self.app.set_status("No active project.")
            return
        try:
            workspace = self.app.gateway.run_validation(self.app.active_project_id)
            blocking = len(workspace.blocking_issues)
            warnings = len(workspace.non_blocking_issues)
            self.app.action_refresh()
            self.app.set_status(f"Validation complete: {blocking} blocking, {warnings} warnings.")
        except Exception as exc:
            self.app.set_status(f"Validation failed: {exc}")

    def _do_next_action(self) -> None:
        from film_pipeline.tui.app import AppState, FilmStudioApp

        if not isinstance(self.app, FilmStudioApp) or not isinstance(self._app_state, AppState):
            return
        dashboard = self._app_state.dashboard
        if dashboard is None:
            self.app.set_status("No active project.")
            return
        if dashboard.current_phase == "generation":
            self._run_generation()
        elif dashboard.next_action in {"present_review_package", "wait_for_human"}:
            if "request_revision" in dashboard.eligible_actions:
                self._request_revision()
            elif "approve_phase" in dashboard.eligible_actions:
                self._approve_phase()
        elif dashboard.has_blockers or (
            self._app_state.snapshot
            and self._app_state.snapshot.validation
            and self._app_state.snapshot.validation.blocking_issues
        ):
            self._run_validation()
        elif "approve_phase" in dashboard.eligible_actions:
            self._approve_phase()
        else:
            self.app.set_status(f"Next action: {dashboard.next_action or 'none'}")

    def _run_generation(self) -> None:
        """Drive the generation batch plan → spend → start → poll in a worker."""
        from film_pipeline.tui.app import AppState, FilmStudioApp

        if not isinstance(self.app, FilmStudioApp) or not isinstance(self._app_state, AppState):
            return
        if self._app_state.dashboard is None:
            self.app.set_status("No active project.")
            return

        project_id = self.app.active_project_id
        gateway = self.app.gateway
        app = self.app

        def _generate() -> Any:
            workspace = gateway.get_generation_workspace(project_id)
            if not workspace.rows:
                workspace = gateway.plan_generation(project_id)
            if workspace.planned:
                workspace = gateway.approve_generation_spend(project_id)
            if workspace.submitted:
                workspace = gateway.start_generation(project_id)
            for _ in range(120):
                if workspace.running == 0:
                    break
                time.sleep(1.0)
                workspace = gateway.poll_generation(project_id)
            return workspace

        def _on_done(result: Any) -> None:
            app.action_refresh()
            failed = getattr(result, "failed", 0)
            completed = getattr(result, "completed", 0)
            planned = getattr(result, "planned", 0)
            submitted = getattr(result, "submitted", 0)
            running = getattr(result, "running", 0)
            if failed:
                app.set_status(
                    f"Generation finished with failures: {completed} done, {failed} failed."
                )
            elif completed:
                app.set_status(f"Generation complete: {completed} clips delivered.")
            else:
                app.set_status(
                    f"Generation update: planned={planned} submitted={submitted} "
                    f"running={running} completed={completed}."
                )

        def _task() -> None:
            try:
                result = _generate()
            except Exception as exc:
                app.call_from_thread(app.set_status, f"Generation failed: {exc}")
                return
            app.call_from_thread(_on_done, result)

        for worker in self.workers:
            if (
                worker.name == "generation_batch"
                and not worker.is_cancelled
                and not worker.is_finished
            ):
                app.set_status("Generation is already running.")
                return

        app.set_status("Generation: planning batch...")
        self.run_worker(_task, thread=True, exclusive=False, name="generation_batch")


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
            yield ModalStatic(
                f"Request Revision — {self._project_id}",
                classes="dialog-title",
            )
            yield ModalStatic(
                f"Phase: {self._phase or 'current'}. Describe what should change.",
                classes="dialog-hint",
            )
            yield ModalLabel("Revision note", classes="field-label")
            yield ModalTextArea("", id="revision_note")
            yield ModalStatic("", id="revision_error", classes="dialog-error")
            with ModalHorizontal(id="dialog_buttons"):
                yield ModalButton("Submit", id="rf_submit", variant="primary")
                yield ModalButton("Cancel", id="rf_cancel")

    def on_mount(self) -> None:
        self.query_one("#revision_note", ModalTextArea).focus()

    def on_button_pressed(self, event: ModalButton.Pressed) -> None:
        if event.button.id == "rf_cancel":
            self.dismiss(None)
        elif event.button.id == "rf_submit":
            self._submit()

    def _submit(self) -> None:
        note = self.query_one("#revision_note", ModalTextArea).text.strip()
        if not note:
            self.query_one("#revision_error", ModalStatic).update("Revision note is required.")
            return
        self.dismiss(note)

    def action_cancel(self) -> None:
        self.dismiss(None)
