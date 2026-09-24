"""P6 migration round-trip tests on a committed legacy-layout fixture."""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from film_pipeline.artifacts.migration import (
    MigrationError,
    discover_legacy_projects,
    migrate,
    plan_migration,
    storage_verify,
)

FIXTURE = Path(__file__).parents[2] / "fixtures" / "legacy_project"


def _make_source(tmp_path: Path) -> Path:
    """One legacy root containing a copy of the committed fixture project."""
    source = tmp_path / "legacy-root"
    source.mkdir()
    shutil.copytree(FIXTURE, source / "legacy-p")
    return source


class TestDetection:
    def test_detects_legacy_project(self, tmp_path: Path) -> None:
        source = _make_source(tmp_path)
        found = discover_legacy_projects(source)
        assert [(f.project_id, f.kind) for f in found] == [("legacy-p", "runtime-state")]

    def test_ignores_already_migrated_and_quarantined(self, tmp_path: Path) -> None:
        source = _make_source(tmp_path)
        shutil.copytree(source / "legacy-p", source / "legacy-p.migrated-20260924")
        upgraded = source / "already-v2"
        upgraded.mkdir()
        (upgraded / "project.json").write_text("{}\n")
        assert [f.project_id for f in discover_legacy_projects(source)] == ["legacy-p"]


class TestMigrationRoundTrip:
    def test_full_round_trip(self, tmp_path: Path) -> None:
        source = _make_source(tmp_path)
        target = tmp_path / "storage"

        plan = plan_migration([source], target)
        assert plan.projects[0].file_count > 0
        assert not target.exists()

        result = migrate([source], target, confirmed=True)
        assert result.migrated == ["legacy-p"]
        assert result.verified is True
        assert result.files_copied > 0
        assert result.quarantined[0].startswith("legacy-p.migrated-")

        # The source was quarantined (renamed), not deleted.
        assert not (source / "legacy-p").exists()
        quarantined = next(source.glob("legacy-p.migrated-*"))
        assert quarantined.is_dir()

        # Conversions on the copy.
        migrated = target / "legacy-p"
        record = json.loads((migrated / "project.json").read_text())
        assert record["project_id"] == "legacy-p"
        assert record["schema_version"] == 1
        # Path-shaped refs (pre-rewrite save() Paths) are blanked and their
        # originals recorded for the operator (plan D8 normalization).
        assert record["budget_state_ref"] == ""
        assert record["migrated_dead_refs"]["budget_state_ref"] == (
            "projects/legacy-p/06-generation-plan/budget_state.json"
        )

        # Colon-id directory renamed; legacy phase dirs re-layouted under
        # artifacts/.
        artifact_dirs = {
            p.name for p in (migrated / "artifacts" / "intake").iterdir() if p.is_dir()
        }
        assert "profile_change_proposal__abc123" in artifact_dirs
        assert not any(":" in name for name in artifact_dirs)
        assert not (migrated / "intake").exists()

        # P2-era versioned ledger became the mutable single file (its legacy
        # root-level phase dir re-layouted under artifacts/).
        ledger_dir = migrated / "artifacts" / "07-generated-assets" / "generation_ledger"
        assert (ledger_dir / "generation_ledger.json").exists()
        ledger = json.loads((ledger_dir / "generation_ledger.json").read_text())
        assert ledger["revision"] == 1

        # Gitignore upgraded in place.
        assert "media/" in (migrated / ".gitignore").read_text().splitlines()

        # Legacy media under a phase dir survives re-layout byte-for-byte at
        # its new artifacts/ location (regression: verify used to fail with
        # "missing 07-generated-assets/scenes/...").
        legacy_media = migrated / (
            "artifacts/07-generated-assets/scenes/SC_001/shot_0001/shot_0001.mp4"
        )
        assert legacy_media.exists()
        assert legacy_media.read_bytes() == b"legacy-clip-bytes"

        # The heart of the migration: the legacy artifact became a real v2
        # artifact — typed pointer, envelope with checksum, human view, and
        # no legacy leftovers.
        artifact_dir = migrated / "artifacts" / "01-vision" / "film_constitution"
        meta_file = json.loads((artifact_dir / "meta.json").read_text())
        assert meta_file["current_version"] == 1
        assert meta_file["status"] == "candidate"
        envelope = json.loads((artifact_dir / "versions" / "v001.json").read_text())
        assert envelope["kind"] == "film.studio/film-constitution"
        assert envelope["payload"] == {
            "project_id": "legacy-p",
            "theme": "legacy",
            "tone": "quiet",
        }
        from film_pipeline.artifacts.envelope import payload_checksum

        assert envelope["checksum"] == payload_checksum(envelope["payload"])
        assert (artifact_dir / "current.md").exists()
        assert not (artifact_dir / "current.json").exists()
        assert not (artifact_dir / "current.meta.json").exists()

        # Migration ledger (sibling of the storage root) records both events.
        log_lines = (target.parent / "migration-log.jsonl").read_text().splitlines()
        events = [json.loads(line)["event"] for line in log_lines]
        assert events == ["migrated", "quarantined"]

        # Layout verification passes.
        assert storage_verify(target)["ok"] is True

        # Dry-run after migration reports nothing to do and writes nothing.
        before = sorted(str(p) for p in source.rglob("*"))
        after = plan_migration([source], target)
        assert all(p.skip_reason == "already migrated" for p in after.projects)
        assert sorted(str(p) for p in source.rglob("*")) == before

    def test_rerun_is_a_noop(self, tmp_path: Path) -> None:
        source = _make_source(tmp_path)
        target = tmp_path / "storage"
        migrate([source], target, confirmed=True)
        quarantined = next(source.glob("legacy-p.migrated-*"))
        quarantined.rename(source / "legacy-p")  # simulate an operator restoring
        result = migrate([source], target, confirmed=True)
        assert result.migrated == []
        assert result.skipped == ["legacy-p"]

    def test_refused_without_confirmation(self, tmp_path: Path) -> None:
        source = _make_source(tmp_path)
        target = tmp_path / "storage"
        with pytest.raises(MigrationError, match="requires confirmation"):
            migrate([source], target, confirmed=False)
        assert not target.exists()

    def test_verify_rejects_unmarked_root(self, tmp_path: Path) -> None:
        with pytest.raises(MigrationError, match="marker"):
            storage_verify(tmp_path / "nowhere")


class TestStorageMigrateTool:
    def test_dry_run_and_confirmation_gate(self, tmp_path: Path) -> None:

        from film_pipeline.mcp.tools.storage import storage_migrate

        source = _make_source(tmp_path)
        target = tmp_path / "storage"

        plan = asyncio.run(
            storage_migrate({"sources": [str(source)], "target": str(target), "dry_run": True})
        )
        assert plan["ok"] is True
        projects = cast(list[dict[str, object]], plan["projects"])
        assert projects[0]["project_id"] == "legacy-p"
        assert not target.exists()

        refused = asyncio.run(storage_migrate({"sources": [str(source)], "target": str(target)}))
        assert refused["ok"] is False
        assert "requires confirmation" in cast(str, refused["error"])
        assert refused["requires_confirmation"] is True
        assert not target.exists()

    def test_confirmed_run_migrates_and_verifies(self, tmp_path: Path) -> None:

        from film_pipeline.mcp.tools.storage import storage_migrate

        source = _make_source(tmp_path)
        target = tmp_path / "storage"
        result = asyncio.run(
            storage_migrate(
                {
                    "sources": [str(source)],
                    "target": str(target),
                    "confirmed": True,
                }
            )
        )
        assert result["ok"] is True
        assert result["migrated"] == ["legacy-p"]
        assert result["verified"] is True
        verification = cast(dict[str, object], result["verification"])
        assert verification["ok"] is True
        assert cast(int, verification["projects"]) >= 1


class TestIsolationAndEdgeCases:
    def _write_legacy_artifact(
        self, project_dir: Path, phase_dir: str, artifact_id: str, *, sidecar: bool = True
    ) -> None:
        artifact = project_dir / phase_dir / artifact_id
        artifact.mkdir(parents=True, exist_ok=True)
        body = json.dumps({"project_id": project_dir.name, "data": artifact_id}) + "\n"
        (artifact / "current.json").write_text(body)
        (artifact / "versions").mkdir(exist_ok=True)
        (artifact / "versions" / "v001.json").write_text(body)
        if sidecar:
            meta = {
                "schema_version": "v1",
                "artifact_id": artifact_id,
                "artifact_type": "treatment",
                "project_id": project_dir.name,
                "phase": "development",
                "version": 1,
                "status": "candidate",
                "parents": [],
                "created_by": "test",
                "reviewed_by": [],
                "validation_refs": [],
                "approval_ref": None,
                "kb_context_ref": None,
                "created_at": "2026-06-01T12:00:00Z",
                "built_from": {},
                "change_summary": "",
            }
            (artifact / "current.meta.json").write_text(json.dumps(meta, indent=2) + "\n")
            (artifact / "versions" / "v001.meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    def test_corrupt_project_does_not_block_healthy_one(self, tmp_path: Path) -> None:
        """Per-project isolation: one bad project fails, the rest migrate."""
        source = tmp_path / "legacy-root"
        source.mkdir()
        bad = source / "bad-p"
        bad.mkdir()
        (bad / "project-state.json").write_text("{}\n")
        # Malformed sidecar inside an artifact: conversion must fail for THIS
        # project only.
        self._write_legacy_artifact(bad, "02-development", "treatment")
        (bad / "02-development" / "treatment" / "current.meta.json").write_text("{broken")
        good = source / "good-p"
        good.mkdir()
        (good / "project-state.json").write_text("{}\n")
        self._write_legacy_artifact(good, "02-development", "treatment")

        target = tmp_path / "storage"
        result = migrate([source], target, confirmed=True)

        assert [entry.split(":")[0] for entry in result.failed] == ["bad-p"]
        assert result.migrated == ["good-p"]
        assert result.verified is False
        assert (target / "good-p" / "project.json").exists()
        assert not (target / "bad-p").exists()

    def test_sidecar_less_artifact_outside_intake_synthesizes_phase(self, tmp_path: Path) -> None:
        """Regression: dir→phase mapping must run through PHASE_DIR_MAP."""
        source = tmp_path / "legacy-root"
        source.mkdir()
        project = source / "nosidecar-p"
        project.mkdir()
        (project / "project-state.json").write_text("{}\n")
        self._write_legacy_artifact(project, "01-vision", "nosidecar_art", sidecar=False)

        target = tmp_path / "storage"
        result = migrate([source], target, confirmed=True)

        assert result.migrated == ["nosidecar-p"]
        artifact_dir = target / "nosidecar-p" / "artifacts" / "01-vision" / "nosidecar_art"
        meta = json.loads((artifact_dir / "meta.json").read_text())
        assert meta["phase"] == "constitution"

    def test_artifact_tree_rerun_skips_via_ledger(self, tmp_path: Path) -> None:
        """Artifact-tree projects (no project-state.json) skip via the ledger."""
        source = tmp_path / "legacy-root"
        source.mkdir()
        project = source / "tree-p"
        self._write_legacy_artifact(project, "02-development", "treatment")

        target = tmp_path / "storage"
        first = migrate([source], target, confirmed=True)
        assert first.migrated == ["tree-p"]
        quarantined = next(source.glob("tree-p.migrated-*"))
        quarantined.rename(source / "tree-p")  # operator restores the source

        second = migrate([source], target, confirmed=True)
        assert second.migrated == []
        assert second.skipped == ["tree-p"]
