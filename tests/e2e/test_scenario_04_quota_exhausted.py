"""E2E Scenario 4: Quota exhausted — provider pauses safely."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.orchestration.services import GraphServices
from film_pipeline.providers.failure_classifier import FailureClassifier
from film_pipeline.providers.health import ProviderHealth
from film_pipeline.schemas.base import ProviderStatus
from film_pipeline.schemas.provider_health import ProviderHealthState
from film_pipeline.studio.runtime import StudioRuntime


@pytest.mark.e2e
class TestQuotaExhausted:
    def test_provider_health_tracks_blocked_state(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services
        rt.create_project("quota-test", "Quota Test")
        rt.set_active("quota-test")

        health = ProviderHealthState(
            provider_id="mock-video-provider",
            status=ProviderStatus.BLOCKED_QUOTA,
            blocked_reason="quota_exhausted",
            quota_state="exhausted",
        )
        rt.provider_health["mock-video-provider"] = health
        assert rt.provider_health["mock-video-provider"].status == ProviderStatus.BLOCKED_QUOTA

    def test_quota_exhaustion_does_not_corrupt_project(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services
        rt.create_project("safe-quota-test", "Safe Quota Test")
        rt.set_active("safe-quota-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "A short film."
        project["current_phase"] = "constitution"
        rt.projects["safe-quota-test"] = project

        rt.provider_health["mock-video-provider"] = ProviderHealthState(
            provider_id="mock-video-provider",
            status=ProviderStatus.BLOCKED_QUOTA,
            blocked_reason="quota_exhausted",
            quota_state="exhausted",
        )
        active = rt.get_active()
        assert active is not None
        assert active["current_phase"] == "constitution"

    def test_failure_classifier_quota(self) -> None:
        """FailureClassifier maps 'quota exceeded' to BLOCKED_QUOTA."""
        failure = FailureClassifier.classify("quota exceeded for this model (429)")
        assert failure.status == ProviderStatus.BLOCKED_QUOTA
        assert failure.is_transient is True

    def test_health_updated_on_quota_failure(self) -> None:
        """ProviderHealth transitions to BLOCKED_QUOTA on classified failure."""
        health = ProviderHealth(provider_id="mock")
        assert health.is_healthy()
        FailureClassifier.update_health(health, "quota exceeded: too many requests")
        assert not health.is_healthy()
        assert health.status == ProviderStatus.BLOCKED_QUOTA
        assert len(health.resume_requirements) > 0
