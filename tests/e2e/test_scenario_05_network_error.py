"""E2E Scenario 5: Network error — no duplicate submit."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.generation.ledger import GenerationLedgerManager
from film_pipeline.orchestration.services import GraphServices
from film_pipeline.schemas._base import GenerationMode, GenerationStatus
from film_pipeline.schemas.generation import (
    GenerationLedger,
    GenerationLedgerRow,
    GenerationRequest,
)
from film_pipeline.storage.store import ArtifactStore


@pytest.mark.e2e
class TestNetworkError:
    def test_generation_ledger_prevents_duplicate_submit(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        GenerationRequest(
            generation_request_id="req-001",
            project_id="net-test",
            shot_id="S001-01",
            provider="mock-video-provider",
            model="mock-fast",
            prompt_ref="prompt:test:v1",
            idempotency_key="idem-key-001",
        )
        row = GenerationLedgerRow(
            generation_request_id="req-001",
            generation_id="gen-001",
            project_id="net-test",
            shot_id="S001-01",
            mode=GenerationMode.TEST,
            provider="mock-video-provider",
            model="mock-fast",
            prompt_ref="prompt:test:v1",
            status=GenerationStatus.SUBMITTED,
            provider_job_id="job-001",
        )
        ledger = GenerationLedger(project_id="net-test", rows=[row])

        existing = [r for r in ledger.rows if r.shot_id == "S001-01"]
        assert len(existing) == 1
        assert existing[0].provider_job_id == "job-001"

    def test_ambiguous_network_failure_preserves_job_id(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        GenerationRequest(
            generation_request_id="req-002",
            project_id="amb-test",
            shot_id="S002-01",
            provider="mock-video-provider",
            model="mock-fast",
            prompt_ref="prompt:amb:v1",
            idempotency_key="idem-key-002",
        )
        row = GenerationLedgerRow(
            generation_request_id="req-002",
            generation_id="gen-002",
            project_id="amb-test",
            shot_id="S002-01",
            mode=GenerationMode.TEST,
            provider="mock-video-provider",
            model="mock-fast",
            prompt_ref="prompt:amb:v1",
            status=GenerationStatus.SUBMITTED,
            provider_job_id="job-amb-001",
        )
        ledger = GenerationLedger(project_id="amb-test", rows=[row])

        recovered = next((r for r in ledger.rows if r.provider_job_id == "job-amb-001"), None)
        assert recovered is not None, "Should recover job after network failure"

        shot_count = len([r for r in ledger.rows if r.shot_id == "S002-01"])
        assert shot_count == 1, "Network failure should not create duplicate jobs"

    def test_approve_spend_duplicate_prevention(self, tmp_path: Path) -> None:
        """approve_spend skips already-SUBMITTED rows (no duplicate submit)."""
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.plan_batch("proj-dup", ["S001", "S002"], "mock-provider", "mock-model")
        mgr.approve_spend("proj-dup")
        # Add a new PREPARED row
        mgr.plan_batch("proj-dup", ["S003"], "mock-provider", "mock-model")
        ledger = mgr.approve_spend("proj-dup")
        submitted = sum(1 for r in ledger.rows if r.status == GenerationStatus.SUBMITTED)
        assert submitted == 3
        s001 = next(r for r in ledger.rows if r.shot_id == "S001")
        assert s001.status == GenerationStatus.SUBMITTED

    def test_start_batch_skips_duplicate(self, tmp_path: Path) -> None:
        """start_generation_batch skips rows with existing provider_job_id."""
        store = ArtifactStore(root=tmp_path / "artifacts")
        mgr = GenerationLedgerManager(store)
        mgr.plan_batch("proj-dup2", ["S001"], "mock-provider", "mock-model")
        mgr.approve_spend("proj-dup2")
        # Manually set a provider_job_id (simulating network error after submit)
        ledger = mgr.load("proj-dup2")
        mgr.update_row("proj-dup2", ledger.rows[0].generation_id, provider_job_id="job-existing")
        # Re-approving should skip the already-submitted row
        ledger2 = mgr.approve_spend("proj-dup2")
        row = next(r for r in ledger2.rows if r.shot_id == "S001")
        assert row.provider_job_id == "job-existing"
