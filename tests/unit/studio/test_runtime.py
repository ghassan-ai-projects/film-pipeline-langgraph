"""Tests for StudioRuntime checkpoint and graph-state behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from film_pipeline.orchestration.orchestrator_state import set_candidate_ref
from film_pipeline.orchestration.services import GraphServices
from film_pipeline.schemas._base import FilmPhase
from film_pipeline.storage.store import ArtifactStore
from film_pipeline.studio.runtime import StudioRuntime
from film_pipeline.studio.safety import ProductionDataError


def test_auto_checkpoint_references_state_snapshot_and_appends_jsonl() -> None:
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
    # The snapshot lives at state/graph-state.json; checkpoints reference it.
    assert cp.graph_state_ref == "state/graph-state.json"
    assert cp.artifact_versions.get("script") == "artifact:script:v1"

    # The state snapshot was written and carries the step state.
    project_root = rt.project_roots["p5"]
    snapshot_file = project_root / "state" / "graph-state.json"
    assert snapshot_file.exists()
    snapshot = json.loads(snapshot_file.read_text())
    assert snapshot["schema_version"] == 1
    assert snapshot["state"]["current_phase"] == "script"

    # No graph_state artifact is written anymore.
    assert rt.services is not None
    assert rt.services.artifact_store.list_artifacts("p5", FilmPhase("intake")) == []

    # Checkpoint metadata is append-only JSONL.
    log_file = project_root / "checkpoints" / "checkpoints.jsonl"
    assert log_file.exists()
    lines = [line for line in log_file.read_text().splitlines() if line]
    assert len(lines) == 1


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
    # One folder holds state AND artifacts (plan §1/D3), so the project root
    # and the artifact directory are the same path.
    project_root = rt.project_roots["p-trash"]
    artifact_dir = rt.services.artifact_store.root / "p-trash"
    assert project_root == artifact_dir
    (project_root / "index").mkdir(parents=True, exist_ok=True)
    (project_root / "index" / "artifacts.json").write_text("{}")

    deleted = rt.delete_project("p-trash")

    assert deleted is True
    assert not project_root.exists()
    # Exactly one archive, because the project was exactly one directory.
    trash_root = persist / "trash"
    archived = list(trash_root.glob("project-p-trash-*"))
    assert len(archived) == 1
    assert (archived[0] / "index" / "artifacts.json").exists()


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
    from film_pipeline.storage.store import ArtifactStore

    projects_root = tmp_path / "projects"
    rt = StudioRuntime(
        server_mode="mock",
        runtime_root=tmp_path / "runtime",
        services=GraphServices(artifact_store=ArtifactStore(root=projects_root)),
    )

    rt.create_project("persisted", title="Persisted Project")
    rt._persist_project_state("persisted")

    discovered_root = projects_root / "discovered" / "artifacts" / "intake"
    discovered_root.mkdir(parents=True)
    (discovered_root / "idea").mkdir()
    (discovered_root / "idea" / "meta.json").write_text("{}")

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
