"""Main studio workspace screen."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Static,
    TabbedContent,
    TabPane,
)

from film_pipeline.app.services.models import DashboardSummary, GenerationWorkspace
from film_pipeline.tui.app_state import AppState
from film_pipeline.tui.gateway import StudioGateway
from film_pipeline.tui.screens.modals import ConfirmScreen, RevisionForm
from film_pipeline.tui.view_models.models import GRAPH_PHASES, StudioSnapshot
from film_pipeline.tui.widgets.action_bar import ActionBar
from film_pipeline.tui.widgets.artifact_list import ArtifactList
from film_pipeline.tui.widgets.asset_browser import AssetBrowser
from film_pipeline.tui.widgets.issue_list import IssueList
from film_pipeline.tui.widgets.reader import Reader
from film_pipeline.tui.widgets.scene_browser import SceneBrowser
from film_pipeline.tui.widgets.stage_nav import StageNav

if TYPE_CHECKING:
    from collections.abc import Callable

    from film_pipeline.tui.app import FilmStudioApp


@dataclass(frozen=True)
class _ProjectSession:
    """A studio command's bound context: host app, state, and live dashboard."""

    app: FilmStudioApp
    state: AppState
    dashboard: DashboardSummary


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

# Which content tab is most useful when a stage is selected.
_STAGE_DEFAULT_TAB: dict[str, str] = {
    "script": "tab_scenes",
    "shot_bible": "tab_scenes",
    "generation": "tab_assets",
    "qc": "tab_issues",
    "post": "tab_assets",
    "delivery": "tab_assets",
}

# Generation polling: check job status once per second, give up after 2 minutes.
_GENERATION_POLL_SECONDS = 1.0
_GENERATION_POLL_ATTEMPTS = 120


def _viewed_stage(selected_stage: str, current_phase: str) -> str:
    """Return the stage whose workspace the operator is looking at."""
    if selected_stage in GRAPH_PHASES:
        return selected_stage
    return current_phase


def _stage_heading(stage: str, current_phase: str) -> str:
    """Render the stage title, flagging when it is not the live phase."""
    label = stage.replace("_", " ").title()
    if stage and stage != current_phase:
        return f"{label} — viewing past stage"
    return label


def _regeneration_is_destructive(snapshot: StudioSnapshot | None) -> bool:
    """Return True when delivered clips would be overwritten by another batch."""
    if snapshot is None or snapshot.generation is None:
        return False
    return snapshot.generation.completed > 0 and len(snapshot.assets) > 0


def _execute_generation_batch(gateway: StudioGateway, project_id: str) -> GenerationWorkspace:
    """Plan, fund, launch, and poll one generation batch until it settles."""
    workspace = gateway.get_generation_workspace(project_id)
    if not workspace.rows:
        workspace = gateway.plan_generation(project_id)
    if workspace.planned:
        workspace = gateway.approve_generation_spend(project_id)
    if workspace.submitted:
        workspace = gateway.start_generation(project_id)
    for _ in range(_GENERATION_POLL_ATTEMPTS):
        if workspace.running == 0:
            break
        time.sleep(_GENERATION_POLL_SECONDS)
        workspace = gateway.poll_generation(project_id)
    return workspace


def _generation_outcome_message(result: GenerationWorkspace) -> str:
    """Summarize how a finished generation batch ended for the status footer."""
    if result.failed:
        return (
            f"Generation finished with failures: {result.completed} done, {result.failed} failed."
        )
    if result.completed:
        return f"Generation complete: {result.completed} clips delivered."
    return (
        f"Generation update: planned={result.planned} submitted={result.submitted} "
        f"running={result.running} completed={result.completed}."
    )


class StudioScreen(Screen[None]):
    """Single workspace: pipeline rail, content tabs, and a wide reader."""

    CSS = """
    #studio_layout {
        height: 1fr;
    }

    #stage_rail {
        width: 20;
        padding: 0 1;
        border-right: solid #2e3440;
    }

    #content_col {
        width: 1fr;
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

    #content_tabs {
        height: 1fr;
    }

    #reader {
        width: 42%;
        border-left: solid #2e3440;
    }

    #action_row {
        height: auto;
        padding: 0 1;
        border-top: solid #2e3440;
    }
    """

    BINDINGS: ClassVar = [
        Binding("a", "approve", "Approve"),
        Binding("r", "revise", "Revise"),
        Binding("v", "validate", "Validate"),
        Binding("g", "generate", "Generate"),
        Binding("1", "show_tab('tab_scenes')", "Scenes", show=False),
        Binding("2", "show_tab('tab_artifacts')", "Artifacts", show=False),
        Binding("3", "show_tab('tab_assets')", "Assets", show=False),
        Binding("4", "show_tab('tab_issues')", "Issues", show=False),
        Binding("escape", "home", "Home"),
    ]

    _app_state: object | None = None
    _auto_tab_stage: str = ""

    def on_mount(self) -> None:
        from film_pipeline.tui.app import FilmStudioApp

        if isinstance(self.app, FilmStudioApp):
            self.app.action_refresh()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="studio_layout"):
            with Vertical(id="stage_rail"):
                yield StageNav(id="stage_nav")
            with Vertical(id="content_col"):
                with Vertical(id="stage_header"):
                    yield Static("No project loaded", id="stage_name")
                    yield Static("Open or create a project to begin.", id="stage_explanation")
                with TabbedContent(id="content_tabs"):
                    with TabPane("Scenes", id="tab_scenes"):
                        yield SceneBrowser(id="scene_browser")
                    with TabPane("Artifacts", id="tab_artifacts"):
                        yield ArtifactList(id="artifact_list")
                    with TabPane("Assets", id="tab_assets"):
                        yield AssetBrowser(id="asset_browser")
                    with TabPane("Issues", id="tab_issues"):
                        yield IssueList(id="issue_list")
            yield Reader(id="reader")
        with Horizontal(id="action_row"):
            yield ActionBar(id="action_bar")
        yield Static("", id="status_footer")
        yield Input(
            placeholder="Command: next · approve · revise <note> · validate · project <id> · help",
            id="command_palette",
        )
        yield Footer()

    def update_state(self, app_state: object) -> None:
        """Refresh the workspace from parent app state."""
        self._app_state = app_state
        state = app_state if isinstance(app_state, AppState) else None
        name = self.query_one("#stage_name", Static)
        explanation = self.query_one("#stage_explanation", Static)
        if state is None or state.dashboard is None:
            name.update("No project loaded")
            explanation.update("Open or create a project to begin.")
            return

        current_phase = state.dashboard.current_phase or ""
        stage = _viewed_stage(state.selected_stage, current_phase)
        name.update(_stage_heading(stage, current_phase))
        explanation.update(_STAGE_EXPLANATIONS.get(stage, ""))

        self._auto_select_tab(stage)
        self._refresh_stage_widgets(state)

    def _refresh_stage_widgets(self, state: AppState) -> None:
        """Push the latest snapshot into every workspace child widget."""
        for widget in (
            self.query_one("#stage_nav", StageNav),
            self.query_one("#action_bar", ActionBar),
            self.query_one("#scene_browser", SceneBrowser),
            self.query_one("#artifact_list", ArtifactList),
            self.query_one("#asset_browser", AssetBrowser),
            self.query_one("#issue_list", IssueList),
            self.query_one("#reader", Reader),
        ):
            widget.update_state(state)

    def _auto_select_tab(self, stage: str) -> None:
        """Pick the most useful tab when the selected stage changes."""
        if not stage or stage == self._auto_tab_stage:
            return
        first_selection = not self._auto_tab_stage
        self._auto_tab_stage = stage
        tabs = self.query_one("#content_tabs", TabbedContent)
        tabs.active = _STAGE_DEFAULT_TAB.get(stage, "tab_artifacts")
        if first_selection:
            self._focus_active_table()

    def action_show_tab(self, tab_id: str) -> None:
        """Keybinding action to switch content tabs."""
        self.query_one("#content_tabs", TabbedContent).active = tab_id
        self._focus_active_table()

    def _focus_active_table(self) -> None:
        """Move focus into the active tab so arrow keys browse its rows."""
        tabs = self.query_one("#content_tabs", TabbedContent)
        pane = tabs.get_pane(tabs.active) if tabs.active else None
        if pane is None:
            return
        for child in pane.children:
            if child.can_focus:
                child.focus()
                return

    def action_approve(self) -> None:
        """Keybinding action for approving the current phase."""
        self._approve_phase()

    def action_revise(self) -> None:
        """Keybinding action for requesting a revision."""
        self._request_revision()

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

    def _active_project_session(self) -> _ProjectSession | None:
        """Return the bound command context, reporting when no project is open."""
        from film_pipeline.tui.app import FilmStudioApp

        if not isinstance(self.app, FilmStudioApp) or not isinstance(self._app_state, AppState):
            return None
        if self._app_state.dashboard is None:
            self.app.set_status("No active project.")
            return None
        return _ProjectSession(self.app, self._app_state, self._app_state.dashboard)

    def _approve_phase(self) -> None:
        """Approve the current phase through the gateway."""
        session = self._active_project_session()
        if session is None:
            return
        app, dashboard = session.app, session.dashboard
        if "approve_phase" not in dashboard.eligible_actions:
            app.set_status("Approval is not eligible right now.")
            return
        try:
            result = app.gateway.approve_phase(app.active_project_id)
            app.action_refresh()
            app.set_status(f"Phase approved: {result.message} → {result.current_phase or 'done'}")
        except Exception as exc:
            app.set_status(f"Approval failed: {exc}")

    def _request_revision(self) -> None:
        """Open the revision form for the current phase."""
        session = self._active_project_session()
        if session is None:
            return
        app, dashboard = session.app, session.dashboard
        app.push_screen(
            RevisionForm(
                project_id=dashboard.project_id,
                phase=dashboard.current_phase or "",
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
        """Run validation for the active project through the gateway."""
        session = self._active_project_session()
        if session is None:
            return
        app = session.app
        try:
            workspace = app.gateway.run_validation(app.active_project_id)
            blocking = len(workspace.blocking_issues)
            warnings = len(workspace.non_blocking_issues)
            app.action_refresh()
            app.set_status(f"Validation complete: {blocking} blocking, {warnings} warnings.")
        except Exception as exc:
            app.set_status(f"Validation failed: {exc}")

    def _do_next_action(self) -> None:
        """Dispatch the single most useful action for the current dashboard."""
        session = self._active_project_session()
        if session is None:
            return
        app, state, dashboard = session.app, session.state, session.dashboard
        if dashboard.current_phase == "generation":
            self._run_generation()
        elif dashboard.next_action in {"present_review_package", "wait_for_human"}:
            if "request_revision" in dashboard.eligible_actions:
                self._request_revision()
            elif "approve_phase" in dashboard.eligible_actions:
                self._approve_phase()
        elif dashboard.has_blockers or (
            state.snapshot
            and state.snapshot.validation
            and state.snapshot.validation.blocking_issues
        ):
            self._run_validation()
        elif "approve_phase" in dashboard.eligible_actions:
            self._approve_phase()
        else:
            app.set_status(f"Next action: {dashboard.next_action or 'none'}")

    def _run_generation(self, *, confirmed: bool = False) -> None:
        """Drive the generation batch plan → spend → start → poll in a worker."""
        session = self._active_project_session()
        if session is None:
            return
        app = session.app
        if _regeneration_is_destructive(session.state.snapshot) and not confirmed:
            app.push_screen(
                ConfirmScreen(
                    "Regenerate clips?",
                    "This will overwrite existing generated clips and may incur cost.",
                ),
                lambda ok: self._run_generation(confirmed=bool(ok)) if ok else None,
            )
            return
        if self._generation_in_flight():
            app.set_status("Generation is already running.")
            return

        app.set_status("Generation: planning batch...")
        self.run_worker(
            self._generation_batch_task(app),
            thread=True,
            exclusive=False,
            name="generation_batch",
        )

    def _generation_in_flight(self) -> bool:
        """Return True while a previous generation batch worker is still active."""
        return any(
            worker.name == "generation_batch" and not worker.is_cancelled and not worker.is_finished
            for worker in self.workers
        )

    def _generation_batch_task(self, app: FilmStudioApp) -> Callable[[], None]:
        """Build the threaded job that runs one batch and posts its outcome."""
        gateway = app.gateway
        project_id = app.active_project_id

        def run_batch() -> None:
            try:
                result = _execute_generation_batch(gateway, project_id)
            except Exception as exc:
                app.call_from_thread(app.set_status, f"Generation failed: {exc}")
                return
            app.call_from_thread(self._post_generation_outcome, app, result)

        return run_batch

    def _post_generation_outcome(self, app: FilmStudioApp, result: GenerationWorkspace) -> None:
        """Refresh the workspace and report how the finished batch ended."""
        app.action_refresh()
        app.set_status(_generation_outcome_message(result))
