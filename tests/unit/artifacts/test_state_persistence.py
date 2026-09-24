"""P4 behavior tests: state persistence collapse, JSONL logs, flock safety."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from film_pipeline.testing.storage import make_store


class TestConcurrentWrites:
    def test_concurrent_saves_produce_distinct_versions_and_valid_json(
        self, tmp_path: Path
    ) -> None:
        """Two threads saving one artifact cannot collide or tear files."""
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactType, FilmPhase
        from film_pipeline.schemas.artifact import ArtifactMetadata
        from film_pipeline.schemas.project import ProjectIdentity

        store = make_store(tmp_path / "store")
        errors: list[Exception] = []

        def _save(n: int) -> None:
            try:
                for _ in range(5):
                    meta = ArtifactMetadata(
                        artifact_id="project_profile",
                        artifact_type=ArtifactType.PROJECT_CONFIG,
                        project_id="p1",
                        phase=FilmPhase.INTAKE,
                        version=1,  # store-owned; advisory
                        created_by=f"thread-{n}",
                        created_at=datetime.now(UTC),
                    )
                    store.save(ProjectIdentity(project_id="p1", slug="s", title=f"T{n}"), meta)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_save, args=(n,)) for n in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        versions_dir = tmp_path / "store/p1/artifacts/intake/project_profile/versions"
        files = sorted(p.name for p in versions_dir.glob("v*.json"))
        # 2 threads x 5 saves: every write lands in its own version file.
        assert files == [f"v{n:03}.json" for n in range(1, 11)]
        # No torn files: every version parses.
        for path in versions_dir.glob("v*.json"):
            envelope = json.loads(path.read_text())
            assert envelope["artifact_id"] == "project_profile"

    def test_concurrent_mutable_saves_keep_a_contiguous_revision_chain(
        self, tmp_path: Path
    ) -> None:
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactType, FilmPhase
        from film_pipeline.schemas.artifact import ArtifactMetadata
        from film_pipeline.schemas.generation import GenerationLedger

        store = make_store(tmp_path / "store")
        errors: list[Exception] = []
        revisions: list[int] = []

        def _save(n: int) -> None:
            try:
                for _ in range(5):
                    meta = ArtifactMetadata(
                        artifact_id="generation_ledger",
                        artifact_type=ArtifactType.GENERATION_LEDGER,
                        project_id="p1",
                        phase=FilmPhase.GENERATION,
                        version=1,
                        created_by=f"thread-{n}",
                        created_at=datetime.now(UTC),
                    )
                    ref = store.save_mutable(GenerationLedger(project_id="p1", rows=[]), meta)
                    revisions.append(ref.version)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_save, args=(n,)) for n in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        # The revision chain never repeats or skips, and the file holds the max.
        assert sorted(revisions) == list(range(1, 11))
        envelope_file = (
            tmp_path
            / "store/p1/artifacts/07-generated-assets/generation_ledger/generation_ledger.json"
        )
        envelope = json.loads(envelope_file.read_text())
        assert envelope["revision"] == 10


class TestProjectRecord:
    def test_project_json_round_trips_typed_and_extra_fields(self, tmp_path: Path) -> None:
        from film_pipeline.app.runtime import StudioRuntime

        rt = StudioRuntime(
            server_mode="mock",
            runtime_root=tmp_path / "runtime",
        )
        rt.create_project("p1", title="Round Trip")
        rt.set_active("p1")
        project_file = rt.project_roots["p1"] / "project.json"
        assert project_file.exists()
        record = json.loads(project_file.read_text())
        assert record["schema_version"] == 1
        assert record["project_id"] == "p1"
        assert record["title"] == "Round Trip"
        # Runtime-only extras survive the typed round trip.
        state = rt.get_project("p1")
        assert state is not None
        state["custom_key"] = "kept"
        rt._persist_project_state("p1")
        reloaded = json.loads(project_file.read_text())
        assert reloaded["custom_key"] == "kept"

    def test_legacy_project_state_still_restores(self, tmp_path: Path) -> None:
        from film_pipeline.app.runtime import StudioRuntime

        runtime_root = tmp_path / "runtime"
        legacy_dir = runtime_root / "legacy-p"
        legacy_dir.mkdir(parents=True)
        (legacy_dir / "project-state.json").write_text(
            json.dumps({"project_id": "legacy-p", "title": "Legacy", "extra": 1})
        )

        rt = StudioRuntime(server_mode="mock", runtime_root=runtime_root)
        assert rt.get_project("legacy-p") is not None
        # First persistence upgrades the file to the typed record.
        rt._persist_project_state("legacy-p")
        assert (legacy_dir / "project.json").exists()

    def test_typed_record_wins_when_both_files_exist(self, tmp_path: Path) -> None:
        """A stale legacy file must never shadow the newer typed record."""
        from film_pipeline.app.runtime import StudioRuntime

        runtime_root = tmp_path / "runtime"
        project_dir = runtime_root / "p1"
        project_dir.mkdir(parents=True)
        (project_dir / "project.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project_id": "p1",
                    "title": "New Record",
                    "current_phase": "delivery",
                    "approved": True,
                }
            )
        )
        (project_dir / "project-state.json").write_text(
            json.dumps({"project_id": "p1", "title": "Old", "current_phase": "intake"})
        )

        rt = StudioRuntime(server_mode="mock", runtime_root=runtime_root)
        state = rt.get_project("p1")
        assert state is not None
        assert state["title"] == "New Record"
        assert state["current_phase"] == "delivery"
        assert state["approved"] is True


class TestJsonlLogs:
    def test_checkpoint_jsonl_appends_without_duplicates(self, tmp_path: Path) -> None:
        from film_pipeline.app.runtime import StudioRuntime

        rt = StudioRuntime(
            server_mode="mock",
            runtime_root=tmp_path / "runtime",
        )
        rt.create_project("p1", title="Log")
        rt.set_active("p1")
        rt.create_checkpoint("p1", "intake", "first")
        rt.create_checkpoint("p1", "constitution", "second")
        # Re-persisting must not duplicate already-logged entries.
        rt._persist_checkpoints("p1")

        log_file = rt.project_roots["p1"] / "checkpoints" / "checkpoints.jsonl"
        lines = [line for line in log_file.read_text().splitlines() if line]
        ids = [json.loads(line)["checkpoint_id"] for line in lines]
        assert len(ids) == len(set(ids)) == 2

    def test_audit_jsonl_appends(self, tmp_path: Path) -> None:
        from film_pipeline.app.runtime import StudioRuntime

        rt = StudioRuntime(
            server_mode="mock",
            runtime_root=tmp_path / "runtime",
        )
        rt.create_project("p1", title="Audit")
        rt._record_audit("system", "custom_event", project_id="p1")
        rt._record_audit("system", "custom_event_two", project_id="p1")
        rt._persist_audit_events("p1")
        rt._persist_audit_events("p1")

        log_file = rt.project_roots["p1"] / "audit" / "audit-log.jsonl"
        lines = [line for line in log_file.read_text().splitlines() if line]
        ids = [json.loads(line)["event_id"] for line in lines]
        # create_project's own audit event + the two custom events.
        assert len(ids) == len(set(ids)) == 3


class TestStateSnapshot:
    def test_graph_state_snapshot_written_per_mutation(self, tmp_path: Path) -> None:
        from film_pipeline.app.runtime import StudioRuntime

        rt = StudioRuntime(
            server_mode="mock",
            runtime_root=tmp_path / "runtime",
        )
        rt.create_project("p1", title="Snapshot")
        rt.set_active("p1")
        state = dict(rt.get_active() or {})
        state["current_phase"] = "constitution"
        rt._auto_checkpoint(state)

        snapshot_file = rt.project_roots["p1"] / "state" / "graph-state.json"
        snapshot = json.loads(snapshot_file.read_text())
        assert snapshot["schema_version"] == 1
        assert snapshot["state"]["current_phase"] == "constitution"
        # No graph_state artifact, no legacy dotfile.
        assert not (rt.project_roots["p1"] / ".graph_state.json").exists()


class TestResumeAcrossRestart:
    def test_gate_survives_runtime_restart(self, tmp_path: Path) -> None:
        """Run to a human gate, rebuild the runtime on the same root, resume.

        This is the P4 bar's persistence-after-every-mutation proof: the
        typed record, snapshot, and JSONL checkpoints written before the
        restart must fully restore the runtime, and the documented manual
        advance must take over from the lost in-memory checkpointer thread.
        """
        from film_pipeline.app.runtime import StudioRuntime

        runtime_root = tmp_path / "runtime"

        rt = StudioRuntime(server_mode="mock", runtime_root=runtime_root)
        rt.create_project("resume-p", title="Resume")
        rt.set_active("resume-p")
        state = rt._run_phase_node(dict(rt.get_active() or {}), "intake")
        rt.projects["resume-p"].update({k: v for k, v in state.items() if k != "_services"})
        rt._persist_project_state("resume-p")
        rt._auto_checkpoint(state)  # snapshot + checkpoint + JSONL append
        at_gate = rt.projects["resume-p"]
        assert at_gate.get("human_approval_required") is True
        assert at_gate.get("current_phase") == "intake"
        phase_before_restart = at_gate.get("current_phase")

        # Rebuild the runtime on the same root: everything restores from disk.
        rt2 = StudioRuntime(server_mode="mock", runtime_root=runtime_root)
        restored = rt2.get_project("resume-p")
        assert restored is not None
        assert restored.get("current_phase") == phase_before_restart
        assert restored.get("human_approval_required") is True
        assert rt2.list_checkpoints("resume-p"), "checkpoints must survive restart"

        # The approval path executes after the restart (active-project is
        # session state; the manual advance takes over for the in-memory
        # checkpointer thread that died with rt).
        rt2.set_active("resume-p")
        result = rt2.approve_phase()
        assert result.get("ok") is not False


class TestOperatorFreshness:
    def test_freshness_prefers_typed_record(self, tmp_path: Path) -> None:
        from film_pipeline.app.runtime import StudioRuntime
        from film_pipeline.app.services.operator import OperatorService

        runtime_root = tmp_path / "runtime"
        rt = StudioRuntime(server_mode="mock", runtime_root=runtime_root)
        rt.create_project("p1", title="Fresh")
        svc = OperatorService(runtime=rt)

        project_dir = rt.project_roots["p1"]
        (project_dir / "project-state.json").write_text("{}")
        (project_dir / "project.json").write_text(json.dumps({"project_id": "p1"}))
        # Both present: the typed record's mtime is the reported freshness,
        # and a missing file yields "" rather than a fake timestamp.
        reported = svc._last_updated_at("p1")
        assert reported != ""
        expected = datetime.fromtimestamp(
            (project_dir / "project.json").stat().st_mtime, tz=UTC
        ).isoformat()
        assert reported == expected

    def test_freshness_falls_back_to_legacy_file(self, tmp_path: Path) -> None:
        from film_pipeline.app.runtime import StudioRuntime
        from film_pipeline.app.services.operator import OperatorService

        runtime_root = tmp_path / "runtime"
        rt = StudioRuntime(server_mode="mock", runtime_root=runtime_root)
        rt.create_project("p1", title="Fresh")
        svc = OperatorService(runtime=rt)

        project_dir = rt.project_roots["p1"]
        (project_dir / "project.json").unlink()
        (project_dir / "project-state.json").write_text("{}")
        reported = svc._last_updated_at("p1")
        assert reported != ""
        assert (
            reported
            == datetime.fromtimestamp(
                (project_dir / "project-state.json").stat().st_mtime, tz=UTC
            ).isoformat()
        )
