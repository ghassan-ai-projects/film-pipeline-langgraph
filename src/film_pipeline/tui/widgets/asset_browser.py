"""Categorized asset browser for the simplified studio view."""

from __future__ import annotations

from typing import Any, ClassVar

from textual.binding import Binding
from textual.widgets import DataTable

from film_pipeline.app.services.errors import ServiceError
from film_pipeline.app.services.models import ArtifactDetail
from film_pipeline.tui.system_open import open_path
from film_pipeline.tui.view_models.builders_reader import build_artifact_reader

_CATEGORIES: tuple[str, ...] = (
    "Character",
    "Environment",
    "Reference",
    "Prompt / Plan",
    "Scene",
    "Camera",
    "Generated Asset",
    "Text-Only Delivery",
    "Other",
)


def _category_for_artifact(artifact: dict[str, object]) -> str:
    artifact_type = str(artifact.get("artifact_type", "")).lower()
    artifact_id = str(artifact.get("artifact_id", "")).lower()
    if "character" in artifact_type or "character" in artifact_id:
        return "Character"
    if "environment" in artifact_type or "environment" in artifact_id:
        return "Environment"
    if "reference" in artifact_type or "reference" in artifact_id:
        return "Reference"
    if any(key in artifact_type for key in ("prompt", "plan", "constitution", "bible", "story")):
        return "Prompt / Plan"
    if any(key in artifact_type for key in ("script", "scene", "treatment")):
        return "Scene"
    if any(key in artifact_type for key in ("shot", "camera")):
        return "Camera"
    return "Other"


def _category_for_asset(asset: dict[str, object]) -> str:
    kind = str(asset.get("kind", "")).lower()
    if kind == "text_only_delivery":
        return "Text-Only Delivery"
    if kind in {"generated_clip", "video", "render"}:
        return "Generated Asset"
    if kind in {"reference_sheet", "image", "reference"}:
        return "Reference"
    return "Generated Asset"


class AssetBrowser(DataTable[str]):
    """Browse characters, environments, references, prompts, and rendered assets."""

    CSS = """
    AssetBrowser {
        height: 1fr;
        border: solid #3b4252;
    }
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("o", "open_asset", "Open selected"),
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
            self._rows = list(state.snapshot.assets)
            for artifact in state.snapshot.artifacts:
                row = dict(artifact)
                row["_category"] = _category_for_artifact(row)
                row["_source"] = "artifact"
                self._rows.append(row)
        self._refresh_view()

    def _refresh_view(self) -> None:
        self.clear(columns=True)
        self.add_columns("Name", "Type", "Category", "Phase", "Status")
        if not self._rows:
            self.add_row("—", "—", "—", "—", "No assets yet.")
            return
        for row in self._rows:
            asset_id = str(row.get("asset_id", ""))
            artifact_id = str(row.get("artifact_id", ""))
            name = asset_id or artifact_id or "unknown"
            source = row.get("_source", "")
            item_type = "Artifact" if source == "artifact" else "Generated Media"
            category = str(row.get("_category", _category_for_asset(row)))
            phase = str(row.get("phase", row.get("scene_id", "")))
            status = str(row.get("status", row.get("active", "")))
            self.add_row(name, item_type, category, phase, status)

    def _selected_row(self) -> dict[str, object] | None:
        cursor = self.cursor_coordinate
        row_index = cursor.row
        if row_index < 0 or row_index >= len(self._rows):
            return None
        return self._rows[row_index]

    def action_open_asset(self) -> None:
        """Open the selected generated asset with the system default application."""
        from film_pipeline.tui.app import FilmStudioApp

        if not isinstance(self.app, FilmStudioApp):
            return
        app = self.app
        row = self._selected_row()
        if row is None:
            return
        source = row.get("_source", "")
        if source == "artifact":
            app.set_status("Open is only available for generated media assets.")
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

        if not isinstance(self.app, FilmStudioApp):
            return
        state = self.app.state
        if state.dashboard is None:
            return

        source = row.get("_source", "")
        if source == "artifact":
            artifact_id = str(row.get("artifact_id", ""))
            phase = str(row.get("phase", ""))
            version_value = row.get("version", 1)
            version = version_value if isinstance(version_value, int) else int(str(version_value))
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
        else:
            asset_id = str(row.get("asset_id", ""))
            state.selected_target = _target_for_asset(row)
            state.reader = None
            state.selected_artifact = None
            self.app.set_status(f"Inspecting asset {asset_id}")
        self.app._propagate_state()


def _target_for_artifact(detail: ArtifactDetail) -> Any:
    from film_pipeline.tui.view_models.models import TargetSelection

    return TargetSelection(
        target_type="artifact",
        target_id=detail.artifact_id,
        phase=detail.phase,
        source="asset_browser",
        detail={
            "artifact_id": detail.artifact_id,
            "artifact_type": detail.artifact_type,
            "phase": detail.phase,
            "version": detail.version,
            "status": detail.status,
        },
    )


def _target_for_asset(row: dict[str, object]) -> Any:
    from film_pipeline.tui.view_models.models import TargetSelection

    return TargetSelection(
        target_type="asset",
        target_id=str(row.get("asset_id", "")),
        phase=str(row.get("scene_id", "")),
        source="asset_browser",
        detail=dict(row),
    )
