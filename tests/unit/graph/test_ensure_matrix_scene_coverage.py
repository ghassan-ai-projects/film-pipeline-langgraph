"""Tests for the deterministic shot-matrix scene-coverage back-fill."""

from __future__ import annotations

from typing import Any

from film_pipeline.graph.nodes import _ensure_matrix_scene_coverage
from film_pipeline.graph.services import SERVICES_KEY, GraphServices
from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.schemas.matrix import MasterFilmMatrix, MasterFilmMatrixRow
from film_pipeline.schemas.script import ScriptScene
from film_pipeline.storage.store import ArtifactStore


def _make_services(tmp_path: Any) -> GraphServices:
    return GraphServices(artifact_store=ArtifactStore(root=tmp_path / "artifacts"))


def _save_script(services: GraphServices, project_id: str, scenes: list[ScriptScene]) -> str:
    from datetime import UTC, datetime

    from film_pipeline.schemas.artifact import ArtifactMetadata
    from film_pipeline.schemas.script import Script

    script = Script(project_id=project_id, scenes=scenes, total_scenes=len(scenes))
    store = services.artifact_store
    version = store.next_version(project_id, FilmPhase("script"), "script")
    meta = ArtifactMetadata(
        artifact_id="script",
        artifact_type=ArtifactType.SCRIPT,
        project_id=project_id,
        phase=FilmPhase("script"),
        version=version,
        status=ArtifactStatus.CANDIDATE,
        created_by="test",
        created_at=datetime.now(UTC),
    )
    ref = store.save(script, meta)
    return ref.to_string()


def test_backfill_adds_missing_scenes_for_dict_matrix(tmp_path: Any) -> None:
    services = _make_services(tmp_path)
    scenes = [ScriptScene(scene_id=f"sc_{i:03d}", scene_heading=f"SCENE {i}") for i in range(1, 4)]
    ref = _save_script(services, "p1", scenes)

    matrix: dict[str, Any] = {
        "project_id": "p1",
        "rows": [
            {
                "shot_id": "s_001",
                "scene_id": "sc_001",
                "act_id": "act_1",
                "sequence_id": "seq_001",
                "scene_intent_ref": "",
                "duration_seconds": 5,
            },
            {
                "shot_id": "s_002",
                "scene_id": "sc_002",
                "act_id": "act_1",
                "sequence_id": "seq_002",
                "scene_intent_ref": "",
                "duration_seconds": 5,
            },
        ],
    }
    state = {"project_id": "p1", "script_ref": ref, SERVICES_KEY: services}
    result = _ensure_matrix_scene_coverage(state, matrix)

    assert result is matrix

    def _sid(row: Any) -> str:
        return row["scene_id"] if isinstance(row, dict) else str(row.scene_id)

    def _auto(row: Any) -> bool:
        return bool(
            row.get("auto_filled") if isinstance(row, dict) else getattr(row, "auto_filled", False)
        )

    scene_ids = {_sid(row) for row in matrix["rows"]}
    assert scene_ids == {"sc_001", "sc_002", "sc_003"}
    auto = [r for r in matrix["rows"] if _auto(r)]
    assert len(auto) == 1
    assert _sid(auto[0]) == "sc_003"


def test_backfill_adds_missing_scenes_for_pydantic_matrix(tmp_path: Any) -> None:
    services = _make_services(tmp_path)
    scenes = [ScriptScene(scene_id=f"sc_{i:03d}", scene_heading=f"SCENE {i}") for i in range(1, 4)]
    ref = _save_script(services, "p2", scenes)

    matrix = MasterFilmMatrix(
        project_id="p2",
        rows=[
            MasterFilmMatrixRow(
                shot_id="s_001",
                act_id="act_1",
                sequence_id="seq_001",
                scene_id="sc_001",
                scene_intent_ref="",
                duration_seconds=5,
            ),
        ],
    )
    state = {"project_id": "p2", "script_ref": ref, SERVICES_KEY: services}
    result = _ensure_matrix_scene_coverage(state, matrix)

    assert isinstance(result, MasterFilmMatrix)
    scene_ids = {row.scene_id for row in result.rows}
    assert scene_ids == {"sc_001", "sc_002", "sc_003"}


def test_no_change_when_all_scenes_covered(tmp_path: Any) -> None:
    services = _make_services(tmp_path)
    scenes = [ScriptScene(scene_id="sc_001", scene_heading="SCENE 1")]
    ref = _save_script(services, "p3", scenes)

    matrix = {
        "project_id": "p3",
        "rows": [{"shot_id": "s_001", "scene_id": "sc_001", "act_id": "act_1"}],
    }
    state = {"project_id": "p3", "script_ref": ref, SERVICES_KEY: services}
    result = _ensure_matrix_scene_coverage(state, matrix)

    assert len(result["rows"]) == 1
    assert not result["rows"][0].get("auto_filled")


def test_no_op_without_script_ref() -> None:
    matrix: dict[str, Any] = {"rows": []}
    result = _ensure_matrix_scene_coverage({}, matrix)
    assert result == matrix


def test_no_op_when_services_missing(tmp_path: Any) -> None:
    matrix: dict[str, Any] = {
        "rows": [{"shot_id": "s_001", "scene_id": "sc_001", "act_id": "act_1"}]
    }
    state = {"project_id": "p4", "script_ref": "artifact:script:script:v1"}
    result = _ensure_matrix_scene_coverage(state, matrix)
    assert result == matrix
