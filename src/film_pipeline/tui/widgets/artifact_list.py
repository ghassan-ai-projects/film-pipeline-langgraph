"""Artifact list widget for the active stage."""

from __future__ import annotations

from typing import Any

from textual.widgets import DataTable

from film_pipeline.app.services.errors import ServiceError
from film_pipeline.app.services.models import ArtifactDetail
from film_pipeline.tui.view_models.builders_reader import build_artifact_reader


class ArtifactList(DataTable[str]):
    """Lists artifacts for the selected stage with one-click inspection."""

    CSS = """
    ArtifactList {
        height: 1fr;
        border: solid #3b4252;
    }
    """

    def __init__(self, *, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        self._rows: list[dict[str, object]] = []

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_state(self, app_state: object) -> None:
        """Refresh artifacts from parent app state."""
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        if state is None or state.snapshot is None or state.dashboard is None:
            self._rows = []
        else:
            stage = state.selected_stage or state.dashboard.current_phase or ""
            self._rows = [
                dict(row) for row in state.snapshot.artifacts if str(row.get("phase", "")) == stage
            ]
        self._refresh_view()

    def _refresh_view(self) -> None:
        self.clear(columns=True)
        if not self._rows:
            self.add_columns("Artifact", "Type", "Version", "Status")
            self.add_row("—", "—", "—", "No artifacts for this stage.")
            return
        self.add_columns("Artifact", "Type", "Version", "Status")
        for row in self._rows:
            self.add_row(
                str(row.get("artifact_id", "")),
                str(row.get("artifact_type", "")),
                str(row.get("version", "")),
                str(row.get("status", "")),
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table is not self:
            return
        if event.cursor_row < 0 or event.cursor_row >= len(self._rows):
            return
        row = self._rows[event.cursor_row]
        artifact_id = str(row.get("artifact_id", ""))
        phase = str(row.get("phase", ""))
        version_value = row.get("version", 1)
        version = version_value if isinstance(version_value, int) else int(str(version_value))
        from film_pipeline.tui.app import FilmStudioApp

        if not isinstance(self.app, FilmStudioApp):
            return
        state = self.app.state
        if state.dashboard is None:
            return
        try:
            detail = self.app.gateway.inspect_artifact(
                artifact_id, phase, version, state.dashboard.project_id
            )
        except (ServiceError, ValueError, FileNotFoundError) as exc:
            self.app.set_status(f"Could not open {artifact_id}: {exc}")
            return
        reader = build_artifact_reader(
            detail,
            comments=state.snapshot.comments if state.snapshot else [],
            validation=state.snapshot.validation if state.snapshot else None,
        )
        state.selected_artifact = detail
        state.reader = reader
        state.selected_target = _target_for_artifact(detail)
        self.app.set_status(f"Inspecting {artifact_id}")
        self.app._propagate_state()


def _target_for_artifact(detail: ArtifactDetail) -> Any:
    from film_pipeline.tui.view_models.models import TargetSelection

    return TargetSelection(
        target_type="artifact",
        target_id=detail.artifact_id,
        phase=detail.phase,
        source="artifact_list",
        detail={
            "artifact_id": detail.artifact_id,
            "artifact_type": detail.artifact_type,
            "phase": detail.phase,
            "version": detail.version,
            "status": detail.status,
        },
    )
