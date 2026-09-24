"""Tests for StudioRuntime checkpoint and graph-state behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.app.safety import ProductionDataError
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.graph.orchestrator_state import set_candidate_ref
from film_pipeline.graph.services import GraphServices
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
    assert cp.graph_state_ref.startswith("artifact:intake:graph_state:v")
    assert cp.artifact_versions.get("script") == "artifact:script:v1"

    assert rt.services is not None
    store = rt.services.artifact_store
    metas = store.list_artifacts("p5", FilmPhase("intake"))
    assert len(metas) == 1
    assert metas[0].artifact_type == ArtifactType.CHECKPOINT


def test_delete_project_removes_state_and_directories(tmp_path: Path) -> None:
    rt = StudioRuntime(
        server_mode="mock",
        runtime_root=tmp_path / "runtime",
        services=GraphServices(artifact_store=ArtifactStore(root=tmp_path / "projects")),
    )
    assert rt.services is not None
    rt.create_project("p-delete", title="Delete Me")
    rt.set_active("p-delete")
    project_root = rt.project_roots["p-delete"]
    artifact_dir = rt.services.artifact_store.root / "p-delete"

    deleted = rt.delete_project("p-delete")

    assert deleted is True
    assert rt.get_project("p-delete") is None
    assert "p-delete" not in rt.project_roots
    assert "p-delete" not in rt.checkpoint_managers
    assert rt.active_project_id == ""
    assert not project_root.exists()
    assert not artifact_dir.exists()


def test_delete_project_returns_false_when_missing(tmp_path: Path) -> None:
    rt = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
    assert rt.delete_project("missing-project") is False


def test_delete_project_clears_active_project_only_when_matching(tmp_path: Path) -> None:
    rt = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
    rt.create_project("p-active", title="Active")
    rt.create_project("p-other", title="Other")
    rt.set_active("p-active")

    rt.delete_project("p-other")

    assert rt.active_project_id == "p-active"
    assert rt.get_project("p-active") is not None


def test_delete_project_archives_to_trash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    persist = tmp_path / "persist"
    monkeypatch.setenv("FILM_PIPELINE_STORAGE_ROOT", str(persist / "projects"))
    rt = StudioRuntime(
        server_mode="mock",
        runtime_root=tmp_path / "runtime",
        services=GraphServices(artifact_store=ArtifactStore(root=tmp_path / "projects")),
    )
    assert rt.services is not None
    rt.create_project("p-trash", title="Trash Me")
    rt.set_active("p-trash")
    project_root = rt.project_roots["p-trash"]
    artifact_dir = rt.services.artifact_store.root / "p-trash"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (project_root / "state.json").write_text("{}")
    (artifact_dir / "idea.json").write_text("{}")

    deleted = rt.delete_project("p-trash")

    assert deleted is True
    assert not project_root.exists()
    assert not artifact_dir.exists()
    trash_root = persist / "trash"
    assert any(trash_root.glob("runtime-p-trash-*"))
    assert any(trash_root.glob("artifacts-p-trash-*"))


def test_delete_project_blocks_production_by_default(tmp_path: Path) -> None:
    rt = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
    rt.create_project("p-prod", title="Prod")
    rt.projects["p-prod"]["project_kind"] = "production"
    rt.set_active("p-prod")

    with pytest.raises(ProductionDataError):
        rt.delete_project("p-prod")


def test_delete_project_allows_production_with_force(tmp_path: Path) -> None:
    rt = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
    rt.create_project("p-prod", title="Prod")
    rt.projects["p-prod"]["project_kind"] = "production"
    rt.set_active("p-prod")

    assert rt.delete_project("p-prod", force=True) is True
    assert rt.get_project("p-prod") is None


def test_load_persistent_projects_reloads_runtime_and_discovered_projects(
    tmp_path: Path,
) -> None:
    from film_pipeline.artifacts.store import ArtifactStore

    projects_root = tmp_path / "projects"
    rt = StudioRuntime(
        server_mode="mock",
        runtime_root=tmp_path / "runtime",
        services=GraphServices(artifact_store=ArtifactStore(root=projects_root)),
    )

    rt.create_project("persisted", title="Persisted Project")
    rt._persist_project_state("persisted")

    discovered_root = projects_root / "discovered"
    (discovered_root / "intake").mkdir(parents=True)
    (discovered_root / "intake" / "idea.v001.json").write_text("{}")

    fresh = StudioRuntime(
        server_mode="mock",
        runtime_root=tmp_path / "runtime",
        services=GraphServices(artifact_store=ArtifactStore(root=projects_root)),
    )
    fresh.load_persisted_projects()

    assert "persisted" in fresh.projects
    assert fresh.projects["persisted"]["title"] == "Persisted Project"
    assert "discovered" in fresh.projects
    assert fresh.projects["discovered"]["current_phase"] == "intake"
    assert fresh.project_roots["discovered"].exists()


def test_load_persistent_projects_skips_empty_runtime_root(tmp_path: Path) -> None:
    rt = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
    rt.load_persisted_projects()
    assert rt.projects == {}
