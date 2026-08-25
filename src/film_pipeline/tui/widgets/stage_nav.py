"""Compact pipeline stage navigator sidebar."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Static

from film_pipeline.tui.view_models.models import GRAPH_PHASES

if TYPE_CHECKING:
    from film_pipeline.tui.app import AppState

_STAGE_LABELS: dict[str, str] = {
    "intake": "Intake",
    "constitution": "Vision",
    "development": "Development",
    "script": "Script",
    "visual_dev": "Visual Dev",
    "shot_bible": "Shot Bible",
    "gen_planning": "Gen Plan",
    "generation": "Generation",
    "qc": "QC",
    "post": "Post",
    "delivery": "Delivery",
}


class StageNav(Vertical):
    """Left-rail stage navigator: one line per stage with a status glyph.

    Glyphs: ``✔`` done, ``▸`` current, ``·`` upcoming, ``!`` blocking issues.
    """

    DEFAULT_CSS = """
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
        height: 1;
        min-width: 0;
        content-align: left middle;
        text-align: left;
        padding: 0 1;
        margin: 0;
        border: none;
        background: transparent;
        color: #6b7480;
    }

    .stage-button:hover {
        background: #1e2229;
    }

    .stage-button:focus {
        text-style: none;
        background: #1e2229;
    }

    .stage-selected {
        background: #2e3440;
        color: #d8dee9;
    }

    .stage-current {
        color: #88c0d0;
        text-style: bold;
    }

    .stage-done {
        color: #a3be8c;
    }

    .stage-blocked {
        color: #bf616a;
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
    def _count_issues(state: AppState) -> dict[str, dict[str, int]]:
        """Count blocking and warning issues per phase."""
        if state.snapshot is None or state.snapshot.validation is None:
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
        hint = self.query_one("#project_hint", Static)
        hint.styles.display = "none" if self._current_phase else "block"

        current_index = (
            self._phase_order.index(self._current_phase)
            if self._current_phase in self._phase_order
            else -1
        )
        for index, stage in enumerate(self._phase_order):
            self._refresh_stage_button(stage, index, current_index)

    def _refresh_stage_button(self, stage: str, index: int, current_index: int) -> None:
        """Re-render one stage row's status classes and glyph."""
        button = self.query_one(f"#stage_{stage}", Button)
        done = 0 <= index < current_index
        current = stage == self._current_phase
        blocked = bool(self._issue_counts.get(stage, {}).get("blocking", 0))

        classes = set(button.classes)
        classes.discard("stage-selected")
        classes.discard("stage-current")
        classes.discard("stage-done")
        classes.discard("stage-blocked")
        if stage == self._selected_stage:
            classes.add("stage-selected")
        if current:
            classes.add("stage-current")
        elif done:
            classes.add("stage-done")
        if blocked:
            classes.add("stage-blocked")
        button.classes = classes

        glyph = self._stage_glyph(done=done, current=current, blocked=blocked)
        button.label = f"{glyph} {_STAGE_LABELS.get(stage, stage)}"

    @staticmethod
    def _stage_glyph(*, done: bool, current: bool, blocked: bool) -> str:
        if blocked:
            return "!"
        if current:
            return "▸"
        if done:
            return "✔"
        return "·"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if not button_id.startswith("stage_"):
            return
        stage = button_id.removeprefix("stage_")
        from film_pipeline.tui.app import FilmStudioApp

        if isinstance(self.app, FilmStudioApp):
            self.app.set_selected_stage(stage)
