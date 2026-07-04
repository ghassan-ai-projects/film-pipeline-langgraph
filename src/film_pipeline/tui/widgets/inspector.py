"""Right-hand inspector panel for selected artifacts, issues, and assets."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from film_pipeline.tui.formatting import pretty


class Inspector(Vertical):
    """Contextual inspector for the currently selected item."""

    CSS = """
    Inspector {
        height: 1fr;
        padding: 1 0;
    }

    #inspector_title {
        color: #88c0d0;
        text-style: bold;
        margin: 0 0 1 0;
    }

    #inspector_subtitle {
        color: #6b7480;
        margin: 0 0 1 0;
    }

    #inspector_body {
        height: 1fr;
        border: solid #3b4252;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    #inspector_actions {
        height: auto;
    }

    #inspector_actions Button {
        margin: 0 1 0 0;
    }

    .empty-hint {
        color: #6b7480;
        content-align: center middle;
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Inspector", id="inspector_title")
        yield Static("Select an artifact or issue to inspect.", id="inspector_subtitle")
        yield Static("", id="inspector_body")
        yield Static("", id="inspector_actions")

    def update_state(self, app_state: object) -> None:
        """Refresh inspector from parent app state."""
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        if state is None:
            self._show_empty()
            return

        title = self.query_one("#inspector_title", Static)
        subtitle = self.query_one("#inspector_subtitle", Static)
        body = self.query_one("#inspector_body", Static)
        actions = self.query_one("#inspector_actions", Static)

        if state.reader is not None:
            title.update(state.reader.title)
            subtitle.update(state.reader.subtitle)
            body.update(self._format_reader(state.reader))
            actions.update("Actions: comment, approve, revise")
        elif state.selected_target is not None:
            title.update(f"{state.selected_target.target_type}: {state.selected_target.target_id}")
            subtitle.update(state.selected_target.phase or "")
            body.update(pretty(state.selected_target.detail))
            actions.update("")
        elif state.snapshot is not None and (
            state.snapshot.generation is not None or state.snapshot.prompts
        ):
            title.update("Generation")
            subtitle.update(
                state.dashboard.current_phase if state.dashboard is not None else "generation"
            )
            body.update(self._format_generation(state.snapshot))
            actions.update("Actions: generate")
        else:
            self._show_empty()

    def _show_empty(self) -> None:
        self.query_one("#inspector_title", Static).update("Inspector")
        self.query_one("#inspector_subtitle", Static).update(
            "Select an artifact or issue to inspect."
        )
        self.query_one("#inspector_body", Static).update("")
        self.query_one("#inspector_actions", Static).update("")

    @staticmethod
    def _format_reader(reader: object) -> str:
        from film_pipeline.tui.view_models.models import ReaderView

        if not isinstance(reader, ReaderView):
            return ""
        lines: list[str] = []
        if reader.outline:
            lines.append("Outline")
            lines.extend(f"  {line}" for line in reader.outline[:20])
        if reader.body:
            lines.append("")
            lines.append("Body")
            lines.append(reader.body[:2000])
        if reader.metadata:
            lines.append("")
            lines.append("Metadata")
            lines.append(pretty(reader.metadata))
        if reader.linked_comments:
            lines.append("")
            lines.append("Comments")
            for comment in reader.linked_comments[:8]:
                lines.append(f"- {comment.target_id}: {comment.body}")
        if reader.linked_validation:
            lines.append("")
            lines.append("Validation")
            for issue in reader.linked_validation[:8]:
                lines.append(f"- {issue.get('severity', '')}: {issue.get('message', '')}")
        return "\n".join(lines)

    @staticmethod
    def _format_generation(snapshot: object) -> str:
        from film_pipeline.tui.view_models.models import CockpitSnapshot

        if not isinstance(snapshot, CockpitSnapshot):
            return ""
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
