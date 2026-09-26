"""Tests for checkpoint system — git backend, manager, resume, invalidation, rollback."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from film_pipeline.checkpoints.branches import BranchManager
from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.checkpoints.invalidation import InvalidationEngine
from film_pipeline.checkpoints.manager import CheckpointManager
from film_pipeline.checkpoints.resume import ResumeManager
from film_pipeline.checkpoints.rollback import RollbackManager
from film_pipeline.schemas.base import FilmPhase


class TestGitBackend:
    def test_init_temp(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            assert git.is_clean()
            assert git.current_branch() == "main"

    def test_commit_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "test.txt").write_text("hello")
            h = git.commit("first", ["test.txt"])
            assert len(h) == 40
            log = git.log()
            assert len(log) == 1

    def test_tag(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "f.txt").write_text("x")
            commit = git.commit("msg", ["f.txt"])
            git.tag("v1.0", "test tag")
            # An annotated tag points at the commit and carries its message.
            assert git._run("rev-parse", "v1.0^{commit}") == commit
            assert git._run("tag", "-l", "-n1", "v1.0").endswith("test tag")

    def test_branch(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "f.txt").write_text("x")
            commit = git.commit("msg", ["f.txt"])
            git.branch("experiment")
            # The branch exists and points at the commit it was created from.
            assert git._run("rev-parse", "experiment") == commit
            assert "experiment" in git._run("branch", "--list", "experiment")

    def test_branch_from_explicit_base(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "f.txt").write_text("x")
            first = git.commit("first", ["f.txt"])
            (Path(d) / "f.txt").write_text("y")
            git.commit("second", ["f.txt"])
            git.branch("from-first", base=first)
            assert git._run("rev-parse", "from-first") == first


class TestCheckpointManager:
    def test_create_and_get(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "f.txt").write_text("data")
            git.commit("init", ["f.txt"])
            mgr = CheckpointManager(git)
            cp = mgr.create(
                project_id="p1",
                phase=FilmPhase.SCRIPT,
                reason="Script approved",
                artifact_versions={"script": "v3"},
                approval_refs=["approval:1"],
                budget_state_ref="budget:v1",
            )
            assert cp.project_id == "p1"
            assert cp.phase == FilmPhase.SCRIPT
            assert cp.artifact_versions == {"script": "v3"}
            assert len(cp.git_commit) == 40
            assert cp.git_tag.startswith("checkpoint/")
            assert mgr.get(cp.checkpoint_id) is cp

    def test_list_for_project(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "f.txt").write_text("x")
            git.commit("init", ["f.txt"])
            mgr = CheckpointManager(git)
            mgr.create("p1", FilmPhase.INTAKE, "start")
            mgr.create("p1", FilmPhase.SCRIPT, "mid")
            mgr.create("p2", FilmPhase.INTAKE, "other")
            assert len(mgr.list_for_project("p1")) == 2
            assert len(mgr.list_for_project("p2")) == 1

    def test_list_all(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "f.txt").write_text("x")
            git.commit("init", ["f.txt"])
            mgr = CheckpointManager(git)
            mgr.create("p1", FilmPhase.INTAKE, "a")
            mgr.create("p1", FilmPhase.SCRIPT, "b")
            assert len(mgr) == 2
            assert len(mgr.list_all()) == 2


class TestResumeManager:
    def test_create_and_find_latest(self) -> None:
        mgr = ResumeManager()
        mgr.create("gen-1", "submit_node", provider_job_id="job-1", last_safe_step="submitted")
        mgr.create("gen-1", "poll_node", last_safe_step="polled")
        latest = mgr.find_latest("gen-1")
        assert latest is not None
        assert latest.last_safe_step == "polled"

    def test_find_all(self) -> None:
        mgr = ResumeManager()
        mgr.create("gen-1", "submit")
        mgr.create("gen-1", "poll")
        mgr.create("gen-2", "submit")
        assert len(mgr.find_all("gen-1")) == 2
        assert len(mgr.find_all("gen-2")) == 1

    def test_clear(self) -> None:
        mgr = ResumeManager()
        mgr.create("gen-1", "submit")
        mgr.clear("gen-1")
        assert mgr.find_latest("gen-1") is None

    def test_resume_returns_state(self) -> None:
        mgr = ResumeManager()
        snap = mgr.create("gen-1", "submit", state={"phase": "generation"})
        state = mgr.resume(snap)
        assert state == {"phase": "generation"}

    def test_no_snapshots(self) -> None:
        mgr = ResumeManager()
        assert mgr.find_latest("nonexistent") is None
        assert mgr.find_all("nonexistent") == []


class TestInvalidation:
    def test_single_artifact(self) -> None:
        engine = InvalidationEngine()
        report = engine.report("script:v3", artifact_types=["script"])
        assert "script" in report.will_revert
        assert len(report.will_invalidate) > 0  # scene_intents, shot_bible, etc.

    def test_constitution_deps(self) -> None:
        engine = InvalidationEngine()
        deps = engine.dependencies_of("film_constitution")
        assert "treatment" in deps
        assert "script" in deps

    def test_requires_human_confirmation(self) -> None:
        engine = InvalidationEngine()
        report = engine.report("shot_bible:v2", artifact_types=["shot_bible"])
        assert report.requires_human_confirmation is True

    def test_empty_types(self) -> None:
        engine = InvalidationEngine()
        report = engine.report("none", artifact_types=[])
        assert report.will_revert == []
        assert report.will_invalidate == []


class TestRollbackManager:
    def test_rollback_to_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "f.txt").write_text("v1")
            git.commit("v1", ["f.txt"])
            mgr = CheckpointManager(git)
            cp = mgr.create("p1", FilmPhase.SCRIPT, "approved", artifact_versions={"script": "v1"})
            # Change file
            (Path(d) / "f.txt").write_text("v2")
            git.commit("v2", ["f.txt"])
            # Rollback
            rm = RollbackManager(checkpoint_manager=mgr, git=git)
            record, report = rm.rollback_to_checkpoint(cp.checkpoint_id)
            assert record.outcome == "success"
            assert report.will_revert == ["script"]

    def test_rollback_missing_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "f.txt").write_text("x")
            git.commit("init", ["f.txt"])
            mgr = CheckpointManager(git)
            rm = RollbackManager(checkpoint_manager=mgr, git=git)
            try:
                rm.rollback_to_checkpoint("nonexistent")
                raise AssertionError("Expected ValueError")
            except ValueError:
                pass

    def test_rollback_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "f.txt").write_text("v1")
            commit1 = git.commit("v1", ["f.txt"])
            (Path(d) / "f.txt").write_text("v2")
            git.commit("v2", ["f.txt"])
            mgr = CheckpointManager(git)
            rm = RollbackManager(checkpoint_manager=mgr, git=git)
            # Rollback single artifact to v1
            rm.rollback_artifact("f.txt", commit1, performed_by="test")
            assert (Path(d) / "f.txt").read_text() == "v1"

    def test_rollback_artifact_resolves_layout_nested_paths(self) -> None:
        """Artifact ids are not git paths: nested layout files must be resolved."""
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            nested = Path(d) / "artifacts" / "03-script" / "script" / "versions"
            nested.mkdir(parents=True)
            (nested / "v001.json").write_text("v1")
            commit1 = git.commit("v1", ["artifacts/03-script/script/versions/v001.json"])
            (nested / "v001.json").write_text("v2")
            git.commit("v2", ["artifacts/03-script/script/versions/v001.json"])
            mgr = CheckpointManager(git)
            rm = RollbackManager(checkpoint_manager=mgr, git=git)
            # The raw id is NOT a tracked path; rollback must map it to the
            # nested layout files before restoring.
            rm.rollback_artifact("script", commit1, performed_by="test")
            assert (nested / "v001.json").read_text() == "v1"

    def test_rollback_artifact_unknown_id_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "f.txt").write_text("v1")
            commit1 = git.commit("v1", ["f.txt"])
            mgr = CheckpointManager(git)
            rm = RollbackManager(checkpoint_manager=mgr, git=git)
            with pytest.raises(ValueError, match="no tracked files"):
                rm.rollback_artifact("missing_artifact", commit1, performed_by="test")


class TestBranches:
    def test_create_branch(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "f.txt").write_text("x")
            git.commit("init", ["f.txt"])
            bm = BranchManager(git)
            branch = bm.create("p1", "cp:1", "alternate ending")
            assert branch.project_id == "p1"
            assert branch.purpose == "alternate ending"
            assert branch.active is True

    def test_list_active(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            git = GitBackend.init_temp(Path(d))
            (Path(d) / "f.txt").write_text("x")
            git.commit("init", ["f.txt"])
            bm = BranchManager(git)
            bm.create("p1", "cp:1", "experiment 1")
            bm.create("p1", "cp:2", "experiment 2")
            assert len(bm.list_active()) == 2
