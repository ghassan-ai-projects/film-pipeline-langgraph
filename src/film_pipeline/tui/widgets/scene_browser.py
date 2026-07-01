"""Scene browser for the simplified studio view."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import DataTable

from film_pipeline.tui.view_models.helpers import _artifact_scenes, _render_scene

if TYPE_CHECKING:
    from film_pipeline.tui.app import AppState


class SceneBrowser(DataTable[str]):
    """Browse scenes with script, camera, and meta information."""

    CSS = """
    SceneBrowser {
        height: 1fr;
        border: solid #3b4252;
    }
    """

    def __init__(self, *, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        self._rows: list[dict[str, object]] = []
        self._scenes: dict[str, dict[str, object]] = {}

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_state(self, app_state: object) -> None:
        """Refresh scenes from parent app state."""
        from film_pipeline.tui.app import AppState

        state = app_state if isinstance(app_state, AppState) else None
        if state is None or state.snapshot is None or state.dashboard is None:
            self._rows = []
            self._scenes = {}
        else:
            self._scenes = self._collect_scenes(state)
            self._rows = sorted(self._scenes.values(), key=lambda s: str(s.get("scene_id", "")))
        self._refresh_view()

    def _collect_scenes(self, state: AppState) -> dict[str, dict[str, object]]:
        scenes: dict[str, dict[str, object]] = {}
        for artifact in state.snapshot.artifacts if state.snapshot else []:
            body = artifact.get("body")
            if not isinstance(body, dict):
                continue
            for scene in _artifact_scenes(body):
                scene_id = str(scene.get("scene_id", ""))
                if not scene_id:
                    continue
                existing = scenes.setdefault(scene_id, {"scene_id": scene_id})
                existing.update({k: v for k, v in scene.items() if v is not None})
                existing.setdefault("source_artifact", str(artifact.get("artifact_id", "")))
        return scenes

    def _refresh_view(self) -> None:
        self.clear(columns=True)
        self.add_columns("Scene", "Heading", "Duration", "Characters", "Location", "Camera")
        if not self._rows:
            self.add_row("—", "—", "—", "—", "—", "No scenes yet.")
            return
        for scene in self._rows:
            scene_id = str(scene.get("scene_id", ""))
            heading = str(scene.get("scene_heading", scene.get("dramatic_function", "")))
            duration = str(scene.get("duration_seconds", scene.get("estimated_seconds", "")))
            characters = self._join_list(scene.get("characters"))
            location = str(scene.get("environment", scene.get("environment_zone", "")))
            camera = str(scene.get("camera_profile", scene.get("camera_movement", "")))
            self.add_row(scene_id, heading, duration, characters, location, camera)

    @staticmethod
    def _join_list(value: object) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        if isinstance(value, str):
            return value
        return ""

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table is not self:
            return
        if event.cursor_row < 0 or event.cursor_row >= len(self._rows):
            return
        scene = self._rows[event.cursor_row]
        scene_id = str(scene.get("scene_id", ""))
        from film_pipeline.tui.app import FilmStudioApp

        if not isinstance(self.app, FilmStudioApp):
            return
        state = self.app.state
        if state.dashboard is None:
            return

        # Build a simple reader from the merged scene data.
        from film_pipeline.tui.view_models.models import ReaderView, TargetSelection

        state.selected_target = TargetSelection(
            target_type="scene",
            target_id=scene_id,
            phase=str(scene.get("source_artifact", "")),
            source="scene_browser",
            detail=dict(scene),
        )
        state.reader = ReaderView(
            title=f"Scene {scene_id}",
            subtitle=str(scene.get("scene_heading", "")),
            outline=[],
            body=_render_scene(scene),
            metadata={k: v for k, v in scene.items() if k not in {"scene_id", "scene_heading"}},
            linked_comments=[
                c
                for c in (state.snapshot.comments if state.snapshot else [])
                if c.target_id == scene_id
            ],
            linked_validation=[],
        )
        state.selected_artifact = None
        self.app.set_status(f"Inspecting scene {scene_id}")
        self.app._propagate_state()
