"""Tests for artifact store, paths, versioning, manifest, and index."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

from film_pipeline.artifacts.index import ArtifactIndex
from film_pipeline.artifacts.manifest import AssetEntry, AssetManifest
from film_pipeline.artifacts.paths import (
    artifact_path,
    generated_asset_dir,
    phase_dir,
    project_dir,
    reference_dir,
)
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.artifacts.versioning import approve, create_version, supersede
from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.schemas.artifact import ArtifactMetadata


def _meta(**kw: object) -> ArtifactMetadata:
    defaults = {
        "artifact_id": "artifact:test:v1",
        "artifact_type": ArtifactType.TREATMENT,
        "project_id": "test-project",
        "phase": FilmPhase.DEVELOPMENT,
        "version": 1,
        "created_by": "test-agent",
        "created_at": datetime.now(UTC),
    }
    defaults.update({k: v for k, v in kw.items() if v is not None})
    return ArtifactMetadata(**defaults)  # type: ignore[arg-type]


class TestPaths:
    def test_project_dir(self) -> None:
        assert project_dir("slug") == Path("projects") / "slug"

    def test_phase_dir_mapping(self) -> None:
        p = phase_dir("slug", "script")
        assert p.parts[-2:] == ("slug", "03-script")

    def test_phase_dir_fallback(self) -> None:
        p = phase_dir("slug", "unknown_phase")
        assert p.parts[-1] == "unknown_phase"

    def test_artifact_path(self) -> None:
        p = artifact_path("slug", "script", "artifact:scene:S001", 3)
        assert p.name == "artifact_scene_S001.v3.json"

    def test_generated_asset_dir(self) -> None:
        p = generated_asset_dir("slug", "S001-01")
        assert "shots" in p.parts
        assert p.name == "S001-01"

    def test_reference_dir(self) -> None:
        p = reference_dir("slug", "characters")
        assert "references" in p.parts
        assert p.name == "characters"


class TestVersioning:
    def test_create_version_defaults(self) -> None:
        v = create_version("artifact:script:S001", "p", "screenwriter-agent")
        assert v.version_id.endswith(":v1")
        assert v.status == ArtifactStatus.CANDIDATE

    def test_create_version_increments_parent(self) -> None:
        parent = create_version("artifact:script:S001", "p", "screenwriter-agent")
        child = create_version("artifact:script:S001", "p", "screenwriter-agent", parent=parent)
        assert child.version_id.endswith(":v2")
        assert child.parent_version_id == parent.version_id

    def test_approve_transitions_status(self) -> None:
        v = create_version("artifact:script:S001", "p", "agent")
        approved = approve(v)
        assert approved.status == ArtifactStatus.APPROVED

    def test_supersede_transitions_status(self) -> None:
        v = create_version("artifact:script:S001", "p", "agent")
        superseded = supersede(v)
        assert superseded.status == ArtifactStatus.SUPERSEDED


class TestArtifactStore:
    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ArtifactStore(root=Path(tmp))
            from film_pipeline.schemas.project import ProjectIdentity

            art = ProjectIdentity(project_id="p1", slug="s", title="T")
            meta = _meta(
                project_id="p1", phase=FilmPhase.INTAKE, artifact_type=ArtifactType.PROJECT_CONFIG
            )
            p = store.save(art, meta)
            assert p.exists()

            loaded = store.load("p1", FilmPhase.INTAKE, "artifact:test:v1", 1)
            assert loaded["project_id"] == "p1"

    def test_list_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ArtifactStore(root=Path(tmp))
            from film_pipeline.schemas.project import ProjectIdentity

            art = ProjectIdentity(project_id="p1", slug="s", title="T")
            m1 = _meta(
                artifact_id="artifact:a",
                project_id="p1",
                phase=FilmPhase.SCRIPT,
                artifact_type=ArtifactType.SCRIPT,
            )
            m2 = _meta(
                artifact_id="artifact:b",
                project_id="p1",
                phase=FilmPhase.SCRIPT,
                artifact_type=ArtifactType.SCRIPT,
            )
            store.save(art, m1)
            store.save(art, m2)
            results = store.list_artifacts("p1", FilmPhase.SCRIPT)
            assert len(results) == 2

    def test_list_artifacts_no_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ArtifactStore(root=Path(tmp))
            from film_pipeline.schemas.project import ProjectIdentity

            art = ProjectIdentity(project_id="p1", slug="s", title="T")
            store.save(
                art,
                _meta(project_id="p1", phase=FilmPhase.SCRIPT, artifact_type=ArtifactType.SCRIPT),
            )
            store.save(
                art,
                _meta(
                    project_id="p1",
                    phase=FilmPhase.CONSTITUTION,
                    artifact_type=ArtifactType.FILM_CONSTITUTION,
                ),
            )
            results = store.list_artifacts("p1")
            assert len(results) == 2


class TestManifest:
    def test_asset_entry(self) -> None:
        e = AssetEntry(asset_id="a", path="p.png", kind="reference_sheet")
        assert e.take == 1
        assert e.active is True

    def test_add_and_active_take(self) -> None:
        m = AssetManifest(project_id="p")
        m.add(AssetEntry(asset_id="a1", path="t1.mp4", kind="generated_clip", shot_id="S001"))
        m.add(
            AssetEntry(
                asset_id="a2", path="t2.mp4", kind="generated_clip", shot_id="S001", active=False
            )
        )
        active = m.active_take("S001")
        assert active is not None
        assert active.asset_id == "a1"

    def test_list_by_kind(self) -> None:
        m = AssetManifest(project_id="p")
        m.add(AssetEntry(asset_id="a", path="p.png", kind="reference_sheet"))
        m.add(AssetEntry(asset_id="b", path="c.mp4", kind="generated_clip"))
        assert len(m.list_by_kind("reference_sheet")) == 1


class TestArtifactIndex:
    def test_add_and_query_by_type(self) -> None:
        idx = ArtifactIndex()
        idx.add(_meta(artifact_type=ArtifactType.SCRIPT))
        idx.add(_meta(artifact_type=ArtifactType.TREATMENT))
        assert len(idx.by_type("script")) == 1
        assert len(idx.by_type("treatment")) == 1

    def test_query_by_phase(self) -> None:
        idx = ArtifactIndex()
        idx.add(_meta(phase=FilmPhase.SCRIPT))
        idx.add(_meta(phase=FilmPhase.GENERATION))
        assert len(idx.by_phase("script")) == 1

    def test_query_by_status(self) -> None:
        idx = ArtifactIndex()
        m = _meta()
        idx.add(m)
        assert len(idx.by_status("candidate")) == 1

    def test_latest(self) -> None:
        idx = ArtifactIndex()
        idx.add(_meta(artifact_id="artifact:script:S001", version=1))
        idx.add(_meta(artifact_id="artifact:script:S001", version=2))
        idx.add(_meta(artifact_id="artifact:script:S001", version=3))
        latest = idx.latest("artifact:script:S001")
        assert latest is not None
        assert latest.version == 3
