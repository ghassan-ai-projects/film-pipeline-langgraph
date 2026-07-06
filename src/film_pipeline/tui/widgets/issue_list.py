"""Validation issue list widget for the active stage."""

from __future__ import annotations

from textual.widgets import DataTable

from film_pipeline.tui.view_models.builders_reader import validation_issue_rows


class IssueList(DataTable[str]):
    """Lists validation issues for the selected stage."""

    DEFAULT_CSS = """
    IssueList {
        height: 1fr;
    }
    """

    def __init__(self, *, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        self._rows: list[dict[str, object]] = []

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_state(self, app_state: object) -> None:
        """Refresh issues from parent app state."""
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        if state is None or state.snapshot is None or state.snapshot.validation is None:
            self._rows = []
        else:
            stage = state.selected_stage or (
                state.dashboard.current_phase if state.dashboard else ""
            )
            self._rows = [
                row
                for row in validation_issue_rows(state.snapshot.validation)
                if stage == "" or str(row.get("phase", stage)) == stage
            ]
        self._refresh_view()

    def _refresh_view(self) -> None:
        self.clear(columns=True)
        self.add_columns("Severity", "Validator", "Target", "Message")
        if not self._rows:
            self.add_row("—", "", "", "No issues for this stage.")
            return
        for row in self._rows:
            self.add_row(
                str(row.get("severity", "")),
                str(row.get("validator", "")),
                str(row.get("target", "")),
                str(row.get("message", "")),
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table is not self:
            return
        if event.cursor_row < 0 or event.cursor_row >= len(self._rows):
            return
        row = self._rows[event.cursor_row]
        target_id = str(row.get("target", ""))
        from film_pipeline.tui.app import FilmStudioApp
        from film_pipeline.tui.view_models.models import TargetSelection

        if not isinstance(self.app, FilmStudioApp):
            return
        state = self.app.state
        state.selected_target = TargetSelection(
            target_type="issue",
            target_id=target_id or str(row.get("validator", "")),
            phase=state.selected_stage
            or (state.dashboard.current_phase if state.dashboard else ""),
            source="issue_list",
            detail=dict(row),
        )
        self.app.set_status(f"Issue selected: {row.get('message', '')}")
        self.app._propagate_state()
