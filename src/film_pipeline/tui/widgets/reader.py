"""Full-height scrollable reader pane for scenes, artifacts, and assets."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from film_pipeline.tui.view_models.helpers import compact_dict


class Reader(VerticalScroll):
    """Read the selected scene, artifact, or asset without leaving the TUI.

    When nothing is selected it shows the project overview (idea, current
    phase, next action), so the pane is never blank.
    """

    DEFAULT_CSS = """
    Reader {
        height: 1fr;
        padding: 0 1;
        scrollbar-background: #1e2229;
        scrollbar-color: #4c566a;
    }

    Reader:focus {
        border: solid #88c0d0;
    }

    #reader_title {
        color: #88c0d0;
        text-style: bold;
        height: auto;
    }

    #reader_subtitle {
        color: #6b7480;
        height: auto;
        margin: 0 0 1 0;
    }

    #reader_body {
        height: auto;
        color: #d8dee9;
    }

    #reader_extras {
        height: auto;
        color: #6b7480;
        margin: 1 0 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Reader", id="reader_title")
        yield Static("", id="reader_subtitle")
        yield Static("Open a project to start reading.", id="reader_body")
        yield Static("", id="reader_extras")

    def update_state(self, app_state: object) -> None:
        """Refresh the reader from parent app state."""
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        if state is None:
            self._show("Reader", "", "Open a project to start reading.", "")
            return

        if state.reader is not None:
            reader = state.reader
            extras: list[str] = []
            if reader.metadata:
                extras.append(compact_dict(reader.metadata))
            if reader.linked_comments:
                extras.append("")
                extras.append("Comments")
                extras.extend(
                    f"- {comment.target_id}: {comment.body}"
                    for comment in reader.linked_comments[:8]
                )
            if reader.linked_validation:
                extras.append("")
                extras.append("Validation")
                extras.extend(
                    f"- {issue.get('severity', '')}: {issue.get('message', '')}"
                    for issue in reader.linked_validation[:8]
                )
            self._show(reader.title, reader.subtitle, reader.body, "\n".join(extras))
            self.scroll_home(animate=False)
            return

        if state.selected_target is not None:
            target = state.selected_target
            self._show(
                f"{target.target_type}: {target.target_id}",
                target.phase or "",
                compact_dict(dict(target.detail)),
                "",
            )
            self.scroll_home(animate=False)
            return

        if state.snapshot is not None and (
            state.snapshot.generation is not None or state.snapshot.prompts
        ):
            phase = state.dashboard.current_phase if state.dashboard is not None else "generation"
            self._show("Generation", phase, self._format_generation(state), "")
            return

        if state.dashboard is not None:
            from film_pipeline.tui.view_models.builders_reader import build_overview_reader

            blocking = (
                len(state.snapshot.validation.blocking_issues)
                if state.snapshot and state.snapshot.validation
                else 0
            )
            overview = build_overview_reader(state.dashboard, blocking_issues=blocking)
            self._show(
                overview.title, overview.subtitle, overview.body, compact_dict(overview.metadata)
            )
            return

        self._show(
            "Reader",
            "",
            "Select a scene, artifact, or asset to read it here.",
            "",
        )

    def _show(self, title: str, subtitle: str, body: str, extras: str) -> None:
        self.query_one("#reader_title", Static).update(title)
        self.query_one("#reader_subtitle", Static).update(subtitle)
        self.query_one("#reader_body", Static).update(body)
        self.query_one("#reader_extras", Static).update(extras)

    @staticmethod
    def _format_generation(state: object) -> str:
        from film_pipeline.tui.app import AppState

        if not isinstance(state, AppState) or state.snapshot is None:
            return ""
        snapshot = state.snapshot
        lines: list[str] = []
        if snapshot.generation is not None:
            gen = snapshot.generation
            lines.append("Batch status")
            lines.append(
                f"  planned={gen.planned} submitted={gen.submitted} "
                f"running={gen.running} completed={gen.completed} failed={gen.failed}"
            )
            if gen.estimated_cost_usd:
                lines.append(f"  estimated cost: ${gen.estimated_cost_usd:.4f}")
            if gen.next_step:
                lines.append(f"  next step: {gen.next_step}")
        if snapshot.prompts:
            lines.append("")
            lines.append("Prompts")
            for prompt in snapshot.prompts[:10]:
                shot_id = prompt.get("shot_id", "")
                duration = prompt.get("duration_seconds", "")
                text = prompt.get("prompt", "")
                lines.append(f"  {shot_id} ({duration}s):")
                lines.append(f"    {text[:200]}")
        return "\n".join(lines)
