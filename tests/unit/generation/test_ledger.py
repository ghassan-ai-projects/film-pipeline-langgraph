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

    def test_update_row_found(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        ledger = mgr.plan_batch("proj-11", ["S001"], "p", "m")
        gen_id = ledger.rows[0].generation_id
        updated = mgr.update_row(
            "proj-11",
            gen_id,
            status=GenerationStatus.RUNNING,
            poll_count=5,
        )
        assert updated is not None
        assert updated.status == GenerationStatus.RUNNING
        assert updated.poll_count == 5
        # Verify persistence
        row = mgr.get_row("proj-11", gen_id)
        assert row is not None
        assert row.status == GenerationStatus.RUNNING

    def test_update_row_not_found(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        updated = mgr.update_row("proj-12", "nonexistent", status=GenerationStatus.FAILED)
        assert updated is None

    def test_approve_spend_idempotent(self, tmp_path: Path) -> None:
        """Already-submitted rows stay submitted."""
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.plan_batch("proj-13", ["S001"], "p", "m")
        mgr.approve_spend("proj-13")
        # Second approve should be a no-op for submitted rows
        ledger = mgr.approve_spend("proj-13")
        assert ledger.rows[0].status == GenerationStatus.SUBMITTED

    def test_get_row_empty_ledger(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.create("proj-14")
        row = mgr.get_row("proj-14", "any")
        assert row is None

    def test_approve_spend_budget_gate_rejects(self, tmp_path: Path) -> None:
        """Budget gate: reject if total cost exceeds max_cost_usd."""
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.plan_batch("proj-budget", ["S001", "S002"], "p", "m")
        # Set estimated costs
        ledger = mgr.load("proj-budget")
        for row in ledger.rows:
            mgr.update_row("proj-budget", row.generation_id, estimated_cost_usd=50.0)
        # Budget of 60 should reject (total is 100)
        raised = False
        try:
            mgr.approve_spend("proj-budget", max_cost_usd=60.0)
        except ValueError:
            raised = True
        assert raised

    def test_approve_spend_budget_gate_passes(self, tmp_path: Path) -> None:
        """Budget gate: passes when total cost is within limit."""
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.plan_batch("proj-budget-ok", ["S001"], "p", "m")
        ledger = mgr.load("proj-budget-ok")
        mgr.update_row("proj-budget-ok", ledger.rows[0].generation_id, estimated_cost_usd=25.0)
        ledger = mgr.approve_spend("proj-budget-ok", max_cost_usd=100.0)
        assert ledger.rows[0].status == GenerationStatus.SUBMITTED

    def test_approve_spend_no_budget_limit(self, tmp_path: Path) -> None:
        """No budget limit: max_cost_usd=-1 passes everything."""
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.plan_batch("proj-no-limit", ["S001"], "p", "m")
        ledger = mgr.load("proj-no-limit")
        mgr.update_row("proj-no-limit", ledger.rows[0].generation_id, estimated_cost_usd=9999.0)
        ledger = mgr.approve_spend("proj-no-limit")
        assert ledger.rows[0].status == GenerationStatus.SUBMITTED

    def test_estimate_total_cost(self, tmp_path: Path) -> None:
        """Estimate total cost of non-terminal rows."""
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.plan_batch("proj-cost", ["S001", "S002"], "p", "m")
        ledger = mgr.load("proj-cost")
        mgr.update_row("proj-cost", ledger.rows[0].generation_id, estimated_cost_usd=10.0)
        mgr.update_row("proj-cost", ledger.rows[1].generation_id, estimated_cost_usd=20.0)
        total = mgr.estimate_total_cost("proj-cost")
        assert total == 30.0

    def test_approve_spend_skips_already_submitted(self, tmp_path: Path) -> None:
        """Duplicate-prevention: already-SUBMITTED rows stay as-is."""
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.plan_batch("proj-dup", ["S001", "S002"], "p", "m")
        # First approve: both go to SUBMITTED
        mgr.approve_spend("proj-dup")
        # Add a new PREPARED row
        mgr.plan_batch("proj-dup", ["S003"], "p", "m")
        # Second approve: only S003 transitions, S001/S002 stay
        ledger = mgr.approve_spend("proj-dup")
        submitted = sum(1 for r in ledger.rows if r.status == GenerationStatus.SUBMITTED)
        assert submitted == 3  # All 3 are now SUBMITTED
        # S001 should not have a double-submitted_at
        s001 = next(r for r in ledger.rows if r.shot_id == "S001")
        assert s001.status == GenerationStatus.SUBMITTED
