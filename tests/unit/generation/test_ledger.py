"""Tests for generation ledger manager."""

from __future__ import annotations

from pathlib import Path

from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.generation.ledger import GenerationLedgerManager
from film_pipeline.schemas._base import GenerationMode, GenerationStatus


class TestGenerationLedgerManager:
    def test_create_ledger(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        ledger = mgr.create("proj-1")
        assert ledger.project_id == "proj-1"
        assert ledger.rows == []

    def test_load_creates_if_missing(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        ledger = mgr.load("proj-new")
        assert ledger.project_id == "proj-new"
        assert ledger.rows == []

    def test_load_returns_persisted(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.create("proj-2")
        # load should return the same ledger
        ledger = mgr.load("proj-2")
        assert ledger.project_id == "proj-2"

    def test_plan_batch_adds_rows(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        ledger = mgr.plan_batch(
            project_id="proj-3",
            shot_ids=["S001", "S002", "S003"],
            provider="mock-video-provider",
            model="mock-fast",
            prompt_ref="prompt:test:v1",
        )
        assert len(ledger.rows) == 3
        assert ledger.rows[0].shot_id == "S001"
        assert ledger.rows[0].status == GenerationStatus.PREPARED
        assert ledger.rows[0].next_action == "submit"

    def test_plan_batch_is_idempotent(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.plan_batch("proj-4", ["S001"], "p", "m")
        ledger = mgr.plan_batch("proj-4", ["S001", "S002"], "p", "m")
        # S001 should not be duplicated
        assert len(ledger.rows) == 2
        s001_rows = [r for r in ledger.rows if r.shot_id == "S001"]
        assert len(s001_rows) == 1

    def test_approve_spend_transitions_rows(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.plan_batch("proj-5", ["S001", "S002"], "p", "m")
        ledger = mgr.approve_spend("proj-5")
        for row in ledger.rows:
            assert row.status == GenerationStatus.SUBMITTED
            assert row.submitted_at is not None
            assert row.next_action == "poll"

    def test_list_rows_all(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.plan_batch("proj-6", ["S001", "S002"], "p", "m")
        rows = mgr.list_rows("proj-6")
        assert len(rows) == 2

    def test_list_rows_by_status(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.plan_batch("proj-7", ["S001", "S002"], "p", "m")
        mgr.approve_spend("proj-7")
        prepared = mgr.list_rows("proj-7", GenerationStatus.PREPARED)
        submitted = mgr.list_rows("proj-7", GenerationStatus.SUBMITTED)
        assert len(prepared) == 0
        assert len(submitted) == 2

    def test_get_row_found(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        ledger = mgr.plan_batch("proj-8", ["S001"], "p", "m")
        gen_id = ledger.rows[0].generation_id
        row = mgr.get_row("proj-8", gen_id)
        assert row is not None
        assert row.shot_id == "S001"

    def test_get_row_not_found(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        row = mgr.get_row("proj-9", "nonexistent")
        assert row is None

    def test_plan_batch_respects_mode(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        ledger = mgr.plan_batch("proj-10", ["S001"], "p", "m", mode=GenerationMode.PRODUCTION)
        assert ledger.rows[0].mode == GenerationMode.PRODUCTION
