"""Tests for StudioRuntime checkpoint and graph-state behavior."""

from __future__ import annotations

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.graph.orchestrator_state import set_candidate_ref
from film_pipeline.schemas._base import ArtifactType, FilmPhase


def test_auto_checkpoint_creates_checkpoint_and_graph_state_artifact() -> None:
    rt = StudioRuntime(server_mode="mock")
    rt.create_project("p5", title="Test")
    state = rt.get_project("p5")
    assert state is not None
    state["current_phase"] = "script"
    set_candidate_ref(state, "script", "artifact:script:v1")

    rt._auto_checkpoint(state)

    checkpoints = rt.list_checkpoints("p5")
    assert len(checkpoints) == 1
    cp = checkpoints[0]
    assert cp.phase.value == "script"
    assert cp.reason == "auto: graph step completed"
    assert cp.graph_state_ref.startswith("artifact:graph_state:v")
    assert cp.artifact_versions.get("script") == "artifact:script:v1"

    assert rt.services is not None
    store = rt.services.artifact_store
    metas = store.list_artifacts("p5", FilmPhase("intake"))
    assert len(metas) == 1
    assert metas[0].artifact_type == ArtifactType.CHECKPOINT
