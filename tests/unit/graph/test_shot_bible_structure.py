"""Regression coverage for the authoritative three-act shot-bible contract."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from film_pipeline.app.mock_responses import default_mock_responses
from film_pipeline.graph.nodes import shot_bible_node
from film_pipeline.graph.nodes._shared import _SERVICES_CTX
from film_pipeline.graph.nodes.visual import _reconcile_shot_matrix_to_brief
from film_pipeline.graph.orchestrator_validators import validate_shot_structure
from film_pipeline.graph.services import SERVICES_KEY, GraphServices
from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.schemas.execution_brief import ExecutionBrief
from film_pipeline.schemas.matrix import MasterFilmMatrix, MasterFilmMatrixRow
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


def _nonconforming_rows() -> list[dict[str, Any]]:
    """Return a deliberately under-sized, five-scene-incomplete matrix."""
    rows: list[dict[str, Any]] = []
    scene_ids = ["sc_001", "sc_002"]
    sequence = 0
    for act_id, count in (("act_1", 17), ("act_2", 16), ("act_3", 15), ("act_4", 7)):
        for _offset in range(count):
            sequence += 1
            rows.append(
                {
                    "shot_id": f"shot_{sequence:03d}",
                    "act_id": act_id,
                    "sequence_id": f"seq_{sequence:03d}",
                    "scene_id": scene_ids[(sequence - 1) % len(scene_ids)],
                    "scene_intent_ref": "",
                    "duration_seconds": 5,
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
    source_rows = _nonconforming_rows()
    responses["shot-design-agent"] = {
        "shot_matrix": {
            "project_id": "third-interval",
            "rows": source_rows,
            "coverage_groups": [],
        }
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
    assert Counter(row["act_id"] for row in source_rows) == {
        "act_1": 17,
        "act_2": 16,
        "act_3": 15,
        "act_4": 7,
    }
    assert sum(row["duration_seconds"] for row in source_rows) == 275

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
        "script_ref": "artifact:script:script:v1",
        "artifact_refs": ["artifact:script:script:v1"],
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
    assert all(8 <= row.duration_seconds <= 10 for row in matrix.rows)
    assert abs(sum(row.duration_seconds for row in matrix.rows) - 600) <= 60
    assert validate_shot_structure({}, brief, matrix) == []
    assert updates["execution_brief_ref"] == "artifact:shot_bible:execution_brief:v1"
    assert "structure-extractor-agent" not in agent_calls
    assert shot_tasks
    assert "Total rows: exactly 67" in shot_tasks[0]
    assert "act_1: exactly 22" in shot_tasks[0]
    assert "act_2: exactly 22" in shot_tasks[0]
    assert "act_3: exactly 23" in shot_tasks[0]
    assert "never turned into additional acts" in shot_tasks[0]


def test_reconcile_forces_brief_contract_on_nonconforming_matrix() -> None:
    """A broken LLM matrix is deterministically reshaped to the brief's exact
    contract: 67 rows, correct per-act counts, no extra acts, existing scenes
    preserved, durations clamped to range, total runtime within 10% of target,
    and validate_shot_structure passes."""
    brief = ExecutionBrief(**_brief())
    matrix_in = {
        "project_id": "third-interval",
        "rows": _nonconforming_rows(),
        "coverage_groups": [],
    }

    reconciled = _reconcile_shot_matrix_to_brief(matrix_in, brief)

    assert isinstance(reconciled, dict)
    rows = reconciled["rows"]
    assert len(rows) == 67
    assert Counter(r["act_id"] for r in rows) == {"act_1": 22, "act_2": 22, "act_3": 23}
    # Extra act_4 must be gone entirely.
    assert not any(r["act_id"] == "act_4" for r in rows)
    # Reconciling must never drop a scene that was already present.
    assert {r["scene_id"] for r in rows} >= {"sc_001", "sc_002"}
    # Shot ids and generation_order are re-sequenced uniquely and densely.
    assert [r["shot_id"] for r in rows] == [f"shot_{n:04d}" for n in range(1, 68)]
    assert [r["sequence_id"] for r in rows] == [f"seq_{n:03d}" for n in range(1, 68)]
    assert sorted(r["generation_order"] for r in rows) == list(range(67))
    # Durations: every row within [8, 10], total within 10% of 600s.
    for r in rows:
        assert 8 <= r["duration_seconds"] <= 10
    total_duration = sum(r["duration_seconds"] for r in rows)
    assert abs(total_duration - 600) <= 60
    # The validator pass is the authoritative guarantee.
    assert validate_shot_structure({}, brief, reconciled) == []


def test_reconcile_preserves_model_shape_and_pads_empty_act() -> None:
    """A Pydantic matrix stays a model, and an act with zero rows is seeded
    without losing scene coverage."""
    brief = ExecutionBrief(**_brief())
    rows: list[dict[str, Any]] = [
        {
            "shot_id": f"shot_{n:03d}",
            "act_id": "act_1",
            "sequence_id": f"seq_{n:03d}",
            "scene_id": f"sc_{n:03d}",
            "scene_intent_ref": "",
            "duration_seconds": 9,
            "generation_order": n - 1,
            "chaining": {},
        }
        for n in range(1, 6)
    ]
    matrix_in = MasterFilmMatrix(
        project_id="third-interval",
        rows=[MasterFilmMatrixRow(**row) for row in rows],
    )

    reconciled = _reconcile_shot_matrix_to_brief(matrix_in, brief)

    assert isinstance(reconciled, MasterFilmMatrix)
    assert len(reconciled.rows) == 67
    assert Counter(r.act_id for r in reconciled.rows) == {"act_1": 22, "act_2": 22, "act_3": 23}
    assert {r.scene_id for r in reconciled.rows} == {
        "sc_001",
        "sc_002",
        "sc_003",
        "sc_004",
        "sc_005",
    }
    assert validate_shot_structure({}, brief, reconciled) == []
