"""Asset gallery / viewer screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static


class AssetViewerScreen(Screen[None]):
    """Inspect generated and reference assets."""

    CSS = """
    #asset_container {
        padding: 2 4;
        height: 1fr;
    }

    #asset_title {
        color: #88c0d0;
        text-style: bold;
        height: auto;
    }

    #asset_table {
        height: 1fr;
        border: solid #3b4252;
        margin: 1 0;
    }

    #asset_detail {
        height: auto;
        color: #6b7480;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="asset_container"):
            yield Static("Assets", id="asset_title")
            yield DataTable(id="asset_table")
            yield Static("Select an asset to see its path.", id="asset_detail")
            yield Button("Back", id="asset_back")

    def on_mount(self) -> None:
        table = self.query_one("#asset_table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        self._refresh_view()

    def _refresh_view(self) -> None:
        from film_pipeline.tui.app import AppState, FilmStudioApp

        table = self.query_one("#asset_table", DataTable)
        if not isinstance(self.app, FilmStudioApp):
            return
        state = self.app.state if isinstance(self.app.state, AppState) else None
        assets = state.snapshot.assets if state and state.snapshot else []
        table.clear(columns=True)
        table.add_columns("Asset", "Kind", "Scene", "Shot", "Path")
        for asset in assets:
            table.add_row(
                str(asset.get("asset_id", "")),
                str(asset.get("kind", "")),
                str(asset.get("scene_id", "") or "—"),
                str(asset.get("shot_id", "") or "—"),
                str(asset.get("path", "")),
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "asset_back" and hasattr(self.app, "pop_screen"):
            self.app.pop_screen()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "asset_table":
            return
        detail = self.query_one("#asset_detail", Static)
        from film_pipeline.tui.app import AppState, FilmStudioApp

        if not isinstance(self.app, FilmStudioApp):
            return
        state = self.app.state if isinstance(self.app.state, AppState) else None
        assets = state.snapshot.assets if state and state.snapshot else []
        if event.cursor_row < 0 or event.cursor_row >= len(assets):
            return
        asset = assets[event.cursor_row]
        detail.update(
            f"{asset.get('asset_id', '')}\n"
            f"kind: {asset.get('kind', '')}\n"
            f"scene: {asset.get('scene_id', '') or '—'}\n"
            f"shot: {asset.get('shot_id', '') or '—'}\n"
            f"path: {asset.get('path', '')}"
        )
