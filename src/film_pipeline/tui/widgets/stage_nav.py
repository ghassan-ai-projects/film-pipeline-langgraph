"""Pipeline stage navigator sidebar widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Static

from film_pipeline.tui.view_models.models import GRAPH_PHASES

_STAGE_LABELS: dict[str, str] = {
    "intake": "1. Intake",
    "constitution": "2. Vision",
    "development": "3. Development",
    "script": "4. Script",
    "visual_dev": "5. Visual Dev",
    "shot_bible": "6. Shot Bible",
    "gen_planning": "7. Gen Plan",
    "generation": "8. Generation",
    "qc": "9. QC",
    "post": "10. Post",
    "delivery": "11. Delivery",
}


class StageNav(Vertical):
    """Left-rail stage navigator with status badges."""

    CSS = """
    StageNav {
        height: 1fr;
        padding: 1 0;
    }

    #stage_nav_title {
        color: #88c0d0;
        text-style: bold;
        margin: 0 0 1 0;
    }

    .stage-button {
        width: 100%;
        height: auto;
        content-align: left middle;
        text-align: left;
        padding: 0 1;
        margin: 0 0 1 0;
        border: none;
        background: transparent;
    }

    .stage-button:hover {
        background: #1e2229;
    }

    .stage-current {
        background: #2e3440;
        color: #88c0d0;
        text-style: bold;
    }

    .stage-done {
        color: #a3be8c;
    }

    .stage-blocked {
        color: #bf616a;
    }

    .stage-review {
        color: #ebcb8b;
    }

    #project_hint {
        color: #6b7480;
        margin-top: 1;
        text-style: italic;
    }
    """

    def __init__(self, *, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        self._current_phase = ""
        self._selected_stage = ""
        self._phase_order = list(GRAPH_PHASES)
        self._issue_counts: dict[str, dict[str, int]] = {}

    def compose(self) -> ComposeResult:
        yield Static("Pipeline", id="stage_nav_title")
        for stage in self._phase_order:
            yield Button(
                _STAGE_LABELS.get(stage, stage),
                id=f"stage_{stage}",
                classes="stage-button",
            )
        yield Static("Open a project to see the pipeline.", id="project_hint")

    def update_state(self, app_state: object) -> None:
        """Refresh the navigator from parent app state."""
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        if state is None or state.dashboard is None:
            self._current_phase = ""
            self._selected_stage = ""
            self._issue_counts = {}
        else:
            self._current_phase = state.dashboard.current_phase or ""
            self._selected_stage = state.selected_stage or self._current_phase
            self._issue_counts = self._count_issues(state)
        self._refresh_view()

    @staticmethod
    def _count_issues(state: object) -> dict[str, dict[str, int]]:
        from film_pipeline.tui.app import AppState

        if (
            not isinstance(state, AppState)
            or state.snapshot is None
            or state.snapshot.validation is None
        ):
            return {}
        counts: dict[str, dict[str, int]] = {}
        for issue in state.snapshot.validation.blocking_issues:
            phase = str(issue.get("phase", state.snapshot.validation.phase or ""))
            counts.setdefault(phase, {"blocking": 0, "warning": 0})
            counts[phase]["blocking"] += 1
        for issue in state.snapshot.validation.non_blocking_issues:
            phase = str(issue.get("phase", state.snapshot.validation.phase or ""))
            counts.setdefault(phase, {"blocking": 0, "warning": 0})
            counts[phase]["warning"] += 1
        return counts

    def _refresh_view(self) -> None:
        title = self.query_one("#stage_nav_title", Static)
        hint = self.query_one("#project_hint", Static)
        if not self._current_phase:
            title.update("Pipeline")
            hint.update("Open a project to see the pipeline.")
            hint.styles.display = "block"
        else:
            hint.styles.display = "none"
            counts = self._issue_counts.get(self._current_phase, {})
            total = counts.get("blocking", 0) + counts.get("warning", 0)
            suffix = f" ({total} issues)" if total else ""
            title.update(f"Pipeline{suffix}")

        current_index = (
            self._phase_order.index(self._current_phase)
            if self._current_phase in self._phase_order
            else -1
        )
        for stage in self._phase_order:
            button = self.query_one(f"#stage_{stage}", Button)
            classes = set(button.classes)
            classes.discard("stage-current")
            classes.discard("stage-done")
            classes.discard("stage-blocked")
            classes.discard("stage-review")
            if stage == self._selected_stage:
                classes.add("stage-current")
            if current_index >= 0 and self._phase_order.index(stage) < current_index:
                classes.add("stage-done")
            issues = self._issue_counts.get(stage, {})
            if issues.get("blocking", 0):
                classes.add("stage-blocked")
            elif issues.get("warning", 0):
                classes.add("stage-review")
            button.classes = classes
            label = _STAGE_LABELS.get(stage, stage)
            if stage == self._current_phase:
                label = f"▸ {label}"
            if issues.get("blocking", 0):
                label = f"{label} ●"
            button.label = label

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if not button_id.startswith("stage_"):
            return
        stage = button_id.removeprefix("stage_")
        from film_pipeline.tui.app import FilmStudioApp

        if isinstance(self.app, FilmStudioApp):
            self.app.set_selected_stage(stage)
