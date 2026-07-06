"""Generated media asset browser (clips, images, deliveries)."""

from __future__ import annotations

from typing import ClassVar

from textual.binding import Binding
from textual.widgets import DataTable

from film_pipeline.tui.system_open import open_path


class AssetBrowser(DataTable[str]):
    """Browse generated media; ``enter`` reads details, ``o`` opens the file."""

    DEFAULT_CSS = """
    AssetBrowser {
        height: 1fr;
    }
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("o", "open_asset", "Open file"),
    ]

    def __init__(self, *, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        self._rows: list[dict[str, object]] = []

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_state(self, app_state: object) -> None:
        """Refresh assets from parent app state."""
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        if state is None or state.snapshot is None or state.dashboard is None:
            self._rows = []
        else:
            self._rows = [dict(asset) for asset in state.snapshot.assets]
        self._refresh_view()

    def _refresh_view(self) -> None:
        self.clear(columns=True)
        self.add_columns("Asset", "Kind", "Scene", "Shot")
        if not self._rows:
            self.add_row("—", "No media yet — run Generate to create clips.", "", "")
            return
        for row in self._rows:
            self.add_row(
                str(row.get("asset_id", "")),
                str(row.get("kind", "")),
                str(row.get("scene_id", "") or "—"),
                str(row.get("shot_id", "") or "—"),
            )

    def _selected_row(self) -> dict[str, object] | None:
        row_index = self.cursor_coordinate.row
        if row_index < 0 or row_index >= len(self._rows):
            return None
        return self._rows[row_index]

    def action_open_asset(self) -> None:
        """Open the selected asset with the system default application."""
        from film_pipeline.tui.app import FilmStudioApp

        if not isinstance(self.app, FilmStudioApp):
            return
        app = self.app
        row = self._selected_row()
        if row is None:
            return
        path = str(row.get("path", ""))
        if not path:
            app.set_status("Selected asset has no file path.")
            return
        try:
            open_path(path)
        except Exception as exc:
            app.set_status(f"Could not open asset: {exc}")
            return
        app.set_status(f"Opened {path}")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table is not self:
            return
        if event.cursor_row < 0 or event.cursor_row >= len(self._rows):
            return
        row = self._rows[event.cursor_row]
        from film_pipeline.tui.app import FilmStudioApp
        from film_pipeline.tui.view_models.models import TargetSelection

        if not isinstance(self.app, FilmStudioApp):
            return
        state = self.app.state
        if state.dashboard is None:
            return
        asset_id = str(row.get("asset_id", ""))
        state.selected_target = TargetSelection(
            target_type="asset",
            target_id=asset_id,
            phase=str(row.get("scene_id", "")),
            source="asset_browser",
            detail=dict(row),
        )
        state.reader = None
        state.selected_artifact = None
        self.app.set_status(f"Selected asset {asset_id} — press 'o' to open the file.")
        self.app._propagate_state()
