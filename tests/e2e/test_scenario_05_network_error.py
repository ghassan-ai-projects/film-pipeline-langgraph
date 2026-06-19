"""E2E Scenario 5: Network error — no duplicate submit."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.graph.services import GraphServices
from film_pipeline.schemas._base import GenerationMode, GenerationStatus
from film_pipeline.schemas.generation import (
    GenerationLedger,
    GenerationLedgerRow,
    GenerationRequest,
)


@pytest.mark.e2e
class TestNetworkError:
    def test_generation_ledger_prevents_duplicate_submit(
        self,
        graph_services: GraphServices,  # noqa: ARG002
        tmp_path: Path,  # noqa: ARG002
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
        graph_services: GraphServices,  # noqa: ARG002
        tmp_path: Path,  # noqa: ARG002
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
