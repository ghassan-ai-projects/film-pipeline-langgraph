"""Regression coverage for the authoritative three-act shot-bible contract."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from film_pipeline.app.mock_responses import default_mock_responses
from film_pipeline.graph.nodes import shot_bible_node
from film_pipeline.graph.nodes._shared import _SERVICES_CTX
from film_pipeline.graph.orchestrator_validators import validate_shot_structure
from film_pipeline.graph.services import SERVICES_KEY, GraphServices
from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.schemas.execution_brief import ExecutionBrief
from film_pipeline.schemas.matrix import MasterFilmMatrix
from film_pipeline.schemas.script import Script, ScriptScene


def _script() -> Script:
    return Script(
        project_id="third-interval",
        title="The Third Interval",
        scenes=[
            ScriptScene(
                scene_id=f"sc_{number:03d}",
                scene_heading=f"INT. TEST LOCATION {number} - DAY",
                action_lines=["A quiet image establishes the scene."],
                dialogue=[],
                intent_ref=f"s_{number:03d}",
            )
            for number in range(1, 6)
        ],
        total_scenes=5,
        total_dialogue_lines=0,
    )


def _brief() -> dict[str, Any]:
    return {
        "project_id": "third-interval",
        "target_runtime_seconds": 600,
        "movements": [
            {
                "movement_id": "act_1",
                "shot_count": 22,
                "duration_range_seconds": [8, 10],
                "description": "Setup",
            },
            {
                "movement_id": "act_2",
                "shot_count": 22,
                "duration_range_seconds": [8, 10],
                "description": "Confrontation",
            },
            {
                "movement_id": "act_3",
                "shot_count": 23,
                "duration_range_seconds": [8, 10],
                "description": "Resolution",
            },
        ],
        "mandatory_anchors": [],
        "environment_progression": [],
        "pacing_style": "slow_cinema",
    }


def _rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scene_ids = [f"sc_{number:03d}" for number in range(1, 6)]
    sequence = 0
    for act_id, count in (("act_1", 22), ("act_2", 22), ("act_3", 23)):
        for _offset in range(count):
            sequence += 1
            rows.append(
                {
                    "shot_id": f"shot_{sequence:03d}",
                    "act_id": act_id,
                    "sequence_id": f"seq_{sequence:03d}",
                    "scene_id": scene_ids[(sequence - 1) % len(scene_ids)],
                    "scene_intent_ref": "",
                    "duration_seconds": 8 if sequence <= 3 else 9,
                    "camera_profile": "locked_wide",
                    "environment": "interval",
                    "characters": [],
                    "prompt_ref": "",
                    "generation_order": sequence - 1,
                    "chaining": {},
                }
            )
    return rows


def test_five_scene_film_shot_matrix_conforms_to_three_act_brief(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """A five-scene script is covered without turning scenes into extra acts."""
    responses = default_mock_responses()
    responses["structure-extractor-agent"] = {"execution_brief": _brief()}
    responses["shot-design-agent"] = {
        "shot_matrix": {"project_id": "third-interval", "rows": _rows(), "coverage_groups": []}
    }
    services = GraphServices.for_mock_runtime(
        artifacts_root=str(tmp_path / "artifacts"), mock_responses=responses
    )
    script_meta = ArtifactMetadata(
        artifact_id="script",
        artifact_type=ArtifactType.SCRIPT,
        project_id="third-interval",
        phase=FilmPhase("script"),
        version=1,
        status=ArtifactStatus.CANDIDATE,
        created_by="test",
        created_at=datetime.now(UTC),
    )
    services.artifact_store.save(_script(), script_meta)
    brief_meta = ArtifactMetadata(
        artifact_id="execution_brief",
        artifact_type=ArtifactType.SHOT_BIBLE,
        project_id="third-interval",
        phase=FilmPhase("shot_bible"),
        version=1,
        status=ArtifactStatus.CANDIDATE,
        created_by="test",
        created_at=datetime.now(UTC),
    )
    services.artifact_store.save(ExecutionBrief(**_brief()), brief_meta)

    shot_tasks: list[str] = []
    agent_calls: list[str] = []
    original_runner = services.prompt_runner.run_from_template

    def capture_runner(*args: Any, **kwargs: Any) -> Any:
        template = args[0]
        agent_calls.append(template.agent_id)
        if template.agent_id == "shot-design-agent":
            shot_tasks.append(str(args[2]))
        return original_runner(*args, **kwargs)

    monkeypatch.setattr(services.prompt_runner, "run_from_template", capture_runner)
    state: dict[str, Any] = {
        "project_id": "third-interval",
        "current_phase": "shot_bible",
        "target_runtime_seconds": 600,
        "target_scene_count": 5,
        # Deliberately conflicting legacy scope hints reproduce the project shape.
        "target_shot_count": 55,
        "constraints": {"target_shot_count": 55, "max_shot_count": 55},
        "script_ref": "artifact:script:v1",
        "artifact_refs": ["artifact:script:v1"],
        "resolved_config": {"studio": {"require_human_approval": False}},
        "_orchestrator__execution_brief": None,
        SERVICES_KEY: services,
    }

    token = _SERVICES_CTX.set(services)
    try:
        updates = shot_bible_node(state)
    finally:
        _SERVICES_CTX.reset(token)

    matrix = MasterFilmMatrix(
        **services.artifact_store.load("third-interval", FilmPhase("shot_bible"), "shot_matrix", 1)
    )
    brief = ExecutionBrief(**updates["_orchestrator__execution_brief"])

    assert len(matrix.rows) == 67
    assert Counter(row.act_id for row in matrix.rows) == {
        "act_1": 22,
        "act_2": 22,
        "act_3": 23,
    }
    assert {row.scene_id for row in matrix.rows} == {
        "sc_001",
        "sc_002",
        "sc_003",
        "sc_004",
        "sc_005",
    }
    assert validate_shot_structure({}, brief, matrix) == []
    assert updates["execution_brief_ref"] == "artifact:execution_brief:v1"
    assert "structure-extractor-agent" not in agent_calls
    assert shot_tasks
    assert "Total rows: exactly 67" in shot_tasks[0]
    assert "act_1: exactly 22" in shot_tasks[0]
    assert "act_2: exactly 22" in shot_tasks[0]
    assert "act_3: exactly 23" in shot_tasks[0]
    assert "never turned into additional acts" in shot_tasks[0]
