"""Tests for artifact store, paths, versioning, manifest, and index."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef
from film_pipeline.schemas.base import ArtifactStatus, ArtifactType, FilmPhase, SchemaBase
from film_pipeline.storage.manifest import AssetEntry, AssetManifest
from film_pipeline.storage.paths import phase_dir, project_dir
from film_pipeline.storage.registry import KindNotRegisteredError
from film_pipeline.storage.store import ArtifactStore


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
        assert project_dir("slug", Path("/store")) == Path("/store") / "slug"

    def test_phase_dir_mapping(self) -> None:
        p = phase_dir("slug", "script", Path("/store"))
        assert p.parts[-2:] == ("slug", "03-script")

    def test_phase_dir_fallback(self) -> None:
        p = phase_dir("slug", "unknown_phase", Path("/store"))
        assert p.parts[-1] == "unknown_phase"


class TestArtifactStore:
    def test_save_and_load(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")
        from film_pipeline.schemas.project import ProjectIdentity

        art = ProjectIdentity(project_id="p1", slug="s", title="T")
        meta = _meta(
            artifact_id="project_profile",
            project_id="p1",
            phase=FilmPhase.INTAKE,
            artifact_type=ArtifactType.PROJECT_CONFIG,
        )
        ref = store.save(art, meta)
        assert isinstance(ref, ArtifactRef)
        assert ref.to_string() == "artifact:intake:project_profile:v1"
        artifact_dir = tmp_path / "store" / "p1" / "artifacts" / "intake" / "project_profile"
        assert (artifact_dir / "meta.json").exists()
        assert (artifact_dir / "current.md").exists()
        assert (artifact_dir / "versions" / "v001.json").exists()
        envelope_file = artifact_dir / "versions" / "v001.json"
        envelope = json.loads(envelope_file.read_text())
        assert envelope["kind"] == "film.studio/project-profile"
        assert envelope["schema_version"] == 1
        assert envelope["payload"]["project_id"] == "p1"
        assert envelope["checksum"].startswith("sha256:")

        loaded = store.load("p1", FilmPhase.INTAKE, "project_profile", 1)
        assert loaded["project_id"] == "p1"
        markdown = (artifact_dir / "current.md").read_text()
        assert "# project_profile" in markdown
        assert "- version: 1" in markdown

    def test_list_artifacts(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")
        from film_pipeline.schemas.project import ProjectIdentity

        art = ProjectIdentity(project_id="p1", slug="s", title="T")
        m1 = _meta(
            artifact_id="script",
            project_id="p1",
            phase=FilmPhase.SCRIPT,
            artifact_type=ArtifactType.SCRIPT,
        )
        m2 = _meta(
            artifact_id="dialogue_pass",
            project_id="p1",
            phase=FilmPhase.SCRIPT,
            artifact_type=ArtifactType.SCRIPT,
        )
        store.save(art, m1)
        store.save(art, m2)
        results = store.list_artifacts("p1", FilmPhase.SCRIPT)
        assert len(results) == 2
        assert sorted(result.artifact_id for result in results) == ["dialogue_pass", "script"]

    def test_list_artifacts_no_filter(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")
        from film_pipeline.schemas.project import ProjectIdentity

        art = ProjectIdentity(project_id="p1", slug="s", title="T")
        store.save(
            art,
            _meta(
                artifact_id="script",
                project_id="p1",
                phase=FilmPhase.SCRIPT,
                artifact_type=ArtifactType.SCRIPT,
            ),
        )
        store.save(
            art,
            _meta(
                artifact_id="film_constitution",
                project_id="p1",
                phase=FilmPhase.CONSTITUTION,
                artifact_type=ArtifactType.FILM_CONSTITUTION,
            ),
        )
        results = store.list_artifacts("p1")
        assert len(results) == 2

    def test_next_version_uses_versions_directory(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")
        from film_pipeline.schemas.project import ProjectIdentity

        art = ProjectIdentity(project_id="p1", slug="s", title="T")
        meta = _meta(
            artifact_id="script",
            project_id="p1",
            phase=FilmPhase.SCRIPT,
            artifact_type=ArtifactType.SCRIPT,
        )
        store.save(art, meta)

        assert store.next_version("p1", "script", "script") == 2

    def test_next_version_returns_one_for_empty_versions_directory(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")
        version_dir = tmp_path / "store" / "p1" / "03-script" / "script" / "versions"
        version_dir.mkdir(parents=True)

        assert store.next_version("p1", "script", "script") == 1

    def test_approve_updates_status_and_approval_ref(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")
        from film_pipeline.schemas.project import ProjectIdentity

        art = ProjectIdentity(project_id="p1", slug="s", title="T")
        meta = _meta(
            artifact_id="script",
            project_id="p1",
            phase=FilmPhase.SCRIPT,
            artifact_type=ArtifactType.SCRIPT,
            status=ArtifactStatus.CANDIDATE,
        )
        store.save(art, meta)
        updated = store.approve("p1", "script", "script", 1, approval_ref="approval-123")
        assert updated.status == ArtifactStatus.APPROVED
        assert updated.approval_ref == "approval-123"
        reloaded = store.load_metadata("p1", "script", "script", 1)
        assert reloaded.status == ArtifactStatus.APPROVED
        assert reloaded.approval_ref == "approval-123"

    def test_approve_rejects_non_candidate(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")
        from film_pipeline.schemas.project import ProjectIdentity

        art = ProjectIdentity(project_id="p1", slug="s", title="T")
        meta = _meta(
            artifact_id="script",
            project_id="p1",
            phase=FilmPhase.SCRIPT,
            artifact_type=ArtifactType.SCRIPT,
            status=ArtifactStatus.CANDIDATE,
        )
        store.save(art, meta)
        store.approve("p1", "script", "script", 1, approval_ref="approval-123")
        with pytest.raises(ValueError, match="expected candidate"):
            store.approve("p1", "script", "script", 1, approval_ref="approval-456")

    def test_save_honors_preapproved_status(self, tmp_path: Path) -> None:
        """Callers may write an already-approved artifact (e.g. config snapshots)."""
        store = ArtifactStore(root=tmp_path / "store")
        from film_pipeline.schemas.project import ProjectIdentity

        art = ProjectIdentity(project_id="p1", slug="s", title="T")
        meta = _meta(
            artifact_id="script",
            project_id="p1",
            phase=FilmPhase.SCRIPT,
            artifact_type=ArtifactType.SCRIPT,
            status=ArtifactStatus.APPROVED,
            approval_ref="approval-123",
        )
        store.save(art, meta)
        listed = store.list_artifacts("p1", FilmPhase.SCRIPT)
        assert listed[0].status == ArtifactStatus.APPROVED
        assert listed[0].approval_ref == "approval-123"

    def test_supersede_updates_status(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")
        from film_pipeline.schemas.project import ProjectIdentity

        art = ProjectIdentity(project_id="p1", slug="s", title="T")
        meta = _meta(
            artifact_id="script",
            project_id="p1",
            phase=FilmPhase.SCRIPT,
            artifact_type=ArtifactType.SCRIPT,
            status=ArtifactStatus.CANDIDATE,
        )
        store.save(art, meta)
        store.approve("p1", "script", "script", 1, approval_ref="approval-123")
        updated = store.supersede("p1", "script", "script", 1)
        assert updated.status == ArtifactStatus.SUPERSEDED
        reloaded = store.load_metadata("p1", "script", "script", 1)
        assert reloaded.status == ArtifactStatus.SUPERSEDED

    def test_supersede_rejects_non_approved(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")
        from film_pipeline.schemas.project import ProjectIdentity

        art = ProjectIdentity(project_id="p1", slug="s", title="T")
        meta = _meta(
            artifact_id="script",
            project_id="p1",
            phase=FilmPhase.SCRIPT,
            artifact_type=ArtifactType.SCRIPT,
            status=ArtifactStatus.CANDIDATE,
        )
        store.save(art, meta)
        with pytest.raises(ValueError, match="expected approved"):
            store.supersede("p1", "script", "script", 1)

    def test_approve_updates_current_meta_sidecar(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")
        from film_pipeline.schemas.project import ProjectIdentity

        art = ProjectIdentity(project_id="p1", slug="s", title="T")
        meta = _meta(
            artifact_id="script",
            project_id="p1",
            phase=FilmPhase.SCRIPT,
            artifact_type=ArtifactType.SCRIPT,
            status=ArtifactStatus.CANDIDATE,
        )
        store.save(art, meta)
        store.approve("p1", "script", "script", 1, approval_ref="approval-123")
        listed = store.list_artifacts("p1", FilmPhase.SCRIPT)
        assert len(listed) == 1
        assert listed[0].status == ArtifactStatus.APPROVED
        assert listed[0].approval_ref == "approval-123"

    def test_save_writes_scene_markdown_for_filesystem_review(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")

        class _ShotMatrix(SchemaBase):
            artifact_id: str
            rows: list[dict[str, Any]]

        store.save(
            _ShotMatrix(
                artifact_id="shot_matrix",
                rows=[
                    {
                        "scene_id": "SC_001",
                        "shot_id": "shot_001",
                        "story_function": "Reveal the message.",
                        "environment": "empty platform",
                        "camera_profile": "slow push-in",
                        "camera_movement": "dolly from wide to close",
                        "action_lines": ["Mara opens the note."],
                        "dialogue": [
                            {
                                "character_id": "MARA",
                                "direction": "whispering",
                                "line": "It came early.",
                            }
                        ],
                        "asset_refs": ["note_ref"],
                        "reference_refs": ["platform_ref"],
                    }
                ],
            ),
            _meta(
                artifact_id="shot_matrix",
                project_id="p1",
                phase=FilmPhase.SHOT_BIBLE,
                artifact_type=ArtifactType.MASTER_FILM_MATRIX,
            ),
        )

        artifact_dir = tmp_path / "store" / "p1" / "artifacts" / "05-shot-bible" / "shot_matrix"
        markdown = (artifact_dir / "current.md").read_text()

        # The typed matrix renderer emits a table plus per-shot story functions.
        assert "## Shot Matrix" in markdown
        assert "| Shot | Scene | Act | Duration | Camera | Status |" in markdown
        assert "| shot_001 | SC_001 |" in markdown
        assert "slow push-in" in markdown  # camera_profile column
        assert "**shot_001**: Reveal the message." in markdown

    def test_rejects_invalid_artifact_id(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")
        from film_pipeline.schemas.project import ProjectIdentity

        art = ProjectIdentity(project_id="p1", slug="s", title="T")
        with pytest.raises(ValueError, match="Invalid artifact id"):
            store.save(
                art,
                _meta(
                    artifact_id="script:v2",
                    project_id="p1",
                    phase=FilmPhase.SCRIPT,
                    artifact_type=ArtifactType.SCRIPT,
                ),
            )

    def test_rejects_unregistered_kind(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "store")
        from film_pipeline.schemas.project import ProjectIdentity

        art = ProjectIdentity(project_id="p1", slug="s", title="T")
        with pytest.raises(KindNotRegisteredError):
            store.save(
                art,
                _meta(
                    artifact_id="mystery_box",
                    project_id="p1",
                    phase=FilmPhase.SCRIPT,
                    artifact_type=ArtifactType.SCRIPT,
                ),
            )


class TestManifest:
    def test_asset_entry(self) -> None:
        e = AssetEntry(asset_id="a", path="p.png", kind="reference_sheet", scene_id="SC_001")
        assert e.scene_id == "SC_001"
        assert e.take == 1
        assert e.active is True

    def test_add_and_active_take(self) -> None:
        m = AssetManifest(project_id="p")
        m.add_take(AssetEntry(asset_id="a1", path="t1.mp4", kind="generated_clip", shot_id="S001"))
        m.add_take(
            AssetEntry(
                asset_id="a2", path="t2.mp4", kind="generated_clip", shot_id="S001", active=False
            )
        )
        active = m.active_take("S001")
        assert active is not None
        assert active.asset_id == "a1"

    def test_list_by_kind(self) -> None:
        m = AssetManifest(project_id="p")
        m.add_take(AssetEntry(asset_id="a", path="p.png", kind="reference_sheet"))
        m.add_take(AssetEntry(asset_id="b", path="c.mp4", kind="generated_clip"))
        assert len(m.list_by_kind("reference_sheet")) == 1

    def test_list_by_scene_and_shot(self) -> None:
        m = AssetManifest(project_id="p")
        m.add_take(
            AssetEntry(
                asset_id="a",
                path="p.mp4",
                kind="generated_clip",
                scene_id="SC_001",
                shot_id="shot_001",
            )
        )
        m.add_take(
            AssetEntry(
                asset_id="b",
                path="p.mp4",
                kind="generated_clip",
                scene_id="SC_002",
                shot_id="shot_002",
            )
        )

        assert [entry.asset_id for entry in m.list_by_scene("SC_001")] == ["a"]
        assert [entry.asset_id for entry in m.list_by_shot("shot_002")] == ["b"]
