"""Scene browser: every scene in the film, readable in one click."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.widgets import DataTable

from film_pipeline.tui.view_models.helpers import artifact_scenes, render_scene

if TYPE_CHECKING:
    from film_pipeline.tui.app import AppState


class SceneBrowser(DataTable[str]):
    """Browse scenes; selecting one opens it in the reader pane."""

    DEFAULT_CSS = """
    SceneBrowser {
        height: 1fr;
    }
    """

    # Artifacts that carry the scenes worth reading, in merge order:
    # later entries win, so the script's scene data takes precedence.
    _SCENE_ARTIFACT_TYPES: ClassVar[tuple[str, ...]] = ("scene_list", "script")

    def __init__(self, *, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        self._rows: list[dict[str, object]] = []
        self._scenes: dict[str, dict[str, object]] = {}
        self._body_cache: dict[tuple[str, str, str, str], dict[str, object]] = {}

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
        artifacts = list(state.snapshot.artifacts) if state.snapshot else []

        def merge_rank(artifact: dict[str, object]) -> int:
            kind = str(artifact.get("artifact_type", artifact.get("artifact_id", "")))
            if kind in self._SCENE_ARTIFACT_TYPES:
                return self._SCENE_ARTIFACT_TYPES.index(kind)
            return -1

        for artifact in sorted(artifacts, key=merge_rank):
            body = artifact.get("body")
            if not isinstance(body, dict):
                body = self._fetch_body(state, artifact)
            if not isinstance(body, dict):
                continue
            for scene in artifact_scenes(body):
                scene_id = str(scene.get("scene_id", ""))
                if not scene_id:
                    continue
                existing = scenes.setdefault(scene_id, {"scene_id": scene_id})
                existing.update({k: v for k, v in scene.items() if v is not None})
                existing["source_artifact"] = str(artifact.get("artifact_id", ""))
        return scenes

    def _fetch_body(self, state: AppState, artifact: dict[str, object]) -> dict[str, object] | None:
        """Load the body of a scene-bearing artifact, cached per version.

        Artifact list rows are summaries without bodies, so the browser pulls
        the full artifact for the few types that contain scenes.
        """
        kind = str(artifact.get("artifact_type", artifact.get("artifact_id", "")))
        if kind not in self._SCENE_ARTIFACT_TYPES:
            return None
        if state.dashboard is None:
            return None
        from film_pipeline.tui.app import FilmStudioApp

        if not isinstance(self.app, FilmStudioApp):
            return None
        artifact_id = str(artifact.get("artifact_id", ""))
        phase = str(artifact.get("phase", ""))
        version = str(artifact.get("version", 1))
        key = (state.dashboard.project_id, artifact_id, phase, version)
        if key in self._body_cache:
            return self._body_cache[key]
        try:
            detail = self.app.gateway.inspect_artifact(
                artifact_id,
                phase,
                int(version) if version.isdigit() else 1,
                state.dashboard.project_id,
            )
        except Exception:
            return None
        self._body_cache[key] = detail.body
        return detail.body

    def _refresh_view(self) -> None:
        self.clear(columns=True)
        self.add_columns("Scene", "Heading", "Duration", "Location")
        if not self._rows:
            self.add_row("—", "No scenes yet — they appear once the script exists.", "", "")
            return
        for scene in self._rows:
            scene_id = str(scene.get("scene_id", ""))
            heading = str(scene.get("scene_heading", scene.get("dramatic_function", "")))
            duration = str(scene.get("duration_seconds", scene.get("estimated_seconds", "")))
            location = str(scene.get("environment", scene.get("environment_zone", "")))
            self.add_row(scene_id, heading, duration, location)

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

        # Build a reader view from the merged scene data.
        from film_pipeline.tui.view_models.models import ReaderView, TargetSelection

        state.selected_target = TargetSelection(
            target_type="scene",
            target_id=scene_id,
            phase=str(scene.get("source_artifact", "")),
            source="scene_browser",
            detail=dict(scene),
        )
        rendered_keys = {"scene_id", "scene_heading", "action_lines", "dialogue", "schema_version"}
        state.reader = ReaderView(
            title=f"Scene {scene_id}",
            subtitle=str(scene.get("scene_heading", "")),
            outline=[],
            body=render_scene(scene),
            metadata={k: v for k, v in scene.items() if k not in rendered_keys},
            linked_comments=[
                c
                for c in (state.snapshot.comments if state.snapshot else [])
                if c.target_id == scene_id
            ],
            linked_validation=[],
        )
        state.selected_artifact = None
        self.app.set_status(f"Reading scene {scene_id}")
        self.app._propagate_state()
