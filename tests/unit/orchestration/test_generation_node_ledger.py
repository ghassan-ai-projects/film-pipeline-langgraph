"""Tests for ledger-backed generation_node with prompt resolution."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from film_pipeline.orchestration.nodes import generation_node
from film_pipeline.orchestration.services import SERVICES_KEY, GraphServices
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.schemas.base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.schemas.film_constitution import FilmConstitution
from film_pipeline.schemas.matrix import MasterFilmMatrix, MasterFilmMatrixRow
from film_pipeline.storage.store import ArtifactStore
from film_pipeline.studio.mock_responses import default_mock_responses


def _services(tmp_path: Path) -> GraphServices:
    return GraphServices.for_mock_runtime(
        artifacts_root=str(tmp_path / "artifacts"), mock_responses=default_mock_responses()
    )


def _save_matrix(store: ArtifactStore, project_id: str) -> str:
    matrix = MasterFilmMatrix(
        project_id=project_id,
        rows=[
            MasterFilmMatrixRow(
                shot_id="shot_0001",
                act_id="act1",
                sequence_id="seq_001",
                scene_id="sc_001",
                scene_intent_ref="intent_001",
                duration_seconds=8,
                story_function="inciting image",
                characters=["mara"],
                environment="wasteland",
                camera_profile="wide_establishing",
            ),
        ],
    )
    meta = ArtifactMetadata(
        artifact_id="shot_matrix",
        artifact_type=ArtifactType.MASTER_FILM_MATRIX,
        project_id=project_id,
        phase=FilmPhase("shot_bible"),
        version=1,
        status=ArtifactStatus.CANDIDATE,
        created_by="test",
        created_at=datetime.now(UTC),
    )
    store.save(matrix, meta)
    return "artifact:shot_bible:shot_matrix:v1"


def _save_constitution(store: ArtifactStore, project_id: str) -> str:
    constitution = FilmConstitution(
        project_id=project_id,
        theme="Hope",
        tone="grounded sci-fi",
        emotional_promise="Inspiration",
        visual_language="desaturated palette with neon accents",
        camera_philosophy="handheld intimacy",
        quality_bar="high",
    )
    meta = ArtifactMetadata(
        artifact_id="film_constitution",
        artifact_type=ArtifactType.FILM_CONSTITUTION,
        project_id=project_id,
        phase=FilmPhase("constitution"),
        version=1,
        status=ArtifactStatus.CANDIDATE,
        created_by="test",
        created_at=datetime.now(UTC),
    )
    store.save(constitution, meta)
    return "artifact:constitution:film_constitution:v1"


def test_generation_node_creates_ledger_and_resolves_prompts(tmp_path: Path) -> None:
    services = _services(tmp_path)
    project_id = "p1"
    shot_matrix_ref = _save_matrix(services.artifact_store, project_id)
    constitution_ref = _save_constitution(services.artifact_store, project_id)

    state: dict[str, object] = {
        "project_id": project_id,
        "shot_matrix_ref": shot_matrix_ref,
        "constitution_ref": constitution_ref,
        "current_phase": "gen_planning",
        "generation_requests": [
            {
                "shot_id": "shot_0001",
                "provider": "seedance-openrouter",
                "model": "seedance-2.0",
                "mode": "test",
                "prompt_ref": "",
            }
        ],
        SERVICES_KEY: services,
    }

    updates = generation_node(state)

    assert updates.get("generation_ledger_ref")
    assert updates.get("generation_patch_ref")
    assert updates.get("artifact_refs")

    # Prompt was resolved from the matrix row + constitution.
    requests = updates.get("generation_requests")
    assert isinstance(requests, list) and len(requests) == 1
    payload = requests[0].get("prompt_payload", {})
    resolved = payload.get("resolved_prompt", "")
    assert "handheld intimacy" in resolved
    assert "wide_establishing" in resolved.lower()

    # No dispatch-readiness blocking issues.
    issues = updates.get("issues", [])
    assert not any(i.get("code") == "undispatchable_requests" for i in issues)

    from film_pipeline.generation.ledger import GenerationLedgerManager

    ledger = GenerationLedgerManager(services.artifact_store).load(project_id)
    assert ledger.rows[0].estimated_cost_usd == 1.44


def test_generation_node_falls_back_without_services(tmp_path: Path) -> None:
    state: dict[str, object] = {
        "project_id": "p1",
        "shot_matrix_ref": "artifact:shot_bible:shot_matrix:v1",
        "current_phase": "gen_planning",
        "generation_requests": [{"shot_id": "shot_0001", "provider": "seedance", "model": "2.0"}],
    }
    updates = generation_node(state)
    assert updates.get("current_phase") == "generation"
    # No ledger without services, but node still returns.
    assert "generation_ledger_ref" not in updates
