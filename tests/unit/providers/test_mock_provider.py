"""Tests for mock video provider."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from film_pipeline.providers.mock_provider import (
    MockVideoProvider,
    ScenarioStep,
)
from film_pipeline.schemas.registries.provider_registry import (
    CostProfile,
    ProviderCapabilities,
    ProviderRegistryEntry,
)


@pytest.fixture
def entry() -> ProviderRegistryEntry:
    return ProviderRegistryEntry(
        provider_id="mock-video-provider",
        provider_type="video",
        models=["mock-fast"],
        capabilities=ProviderCapabilities(
            text_to_video=True,
            image_to_video=True,
            return_last_frame=True,
            max_duration_seconds=30,
            aspect_ratios=["16:9", "9:16"],
            supports_audio=True,
            supports_seed=True,
        ),
        cost_profile=CostProfile(unit="second", estimated_rate_usd=0.0),
        failure_modes=[
            "timeout",
            "quota",
            "auth",
            "moderation",
            "download_failure",
            "corrupt_asset",
        ],
    )


class TestMockVideoProvider:
    def test_build_payload(self, entry: ProviderRegistryEntry) -> None:
        provider = MockVideoProvider(entry=entry)
        payload = provider.build_payload("test prompt", duration=8.0)
        assert payload["prompt"] == "test prompt"
        assert payload["duration"] == 8.0
        assert payload["aspect_ratio"] == "16:9"

    def test_submit_and_poll_happy_path(self, entry: ProviderRegistryEntry) -> None:
        provider = MockVideoProvider(entry=entry)
        payload = provider.build_payload("test")
        job = provider.submit(payload, "S001-01")
        assert job.status == "submitted"
        assert job.job_id.startswith("mock-job-")

        job = provider.poll(job)
        assert job.status == "completed"

    def test_download_creates_files(self, entry: ProviderRegistryEntry) -> None:
        provider = MockVideoProvider(entry=entry)
        payload = provider.build_payload("test")
        job = provider.submit(payload, "S001-01")
        provider.poll(job)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = provider.download(job, tmpdir)
            assert Path(path).exists()
            assert Path(path).suffix == ".mp4"
            # Check companion files
            meta = Path(tmpdir) / "S001-01_metadata.json"
            assert meta.exists()
            png = Path(tmpdir) / "S001-01_last.png"
            assert png.exists()

    def test_extract_metadata(self, entry: ProviderRegistryEntry) -> None:
        provider = MockVideoProvider(entry=entry)
        payload = provider.build_payload("test")
        job = provider.submit(payload, "S001-01")
        provider.poll(job)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = provider.download(job, tmpdir)
            meta = provider.extract_metadata(path)
            assert meta["shot_id"] == "S001-01"
            assert meta["resolution"] == "1280x720"

    def test_estimate_cost_zero(self, entry: ProviderRegistryEntry) -> None:
        provider = MockVideoProvider(entry=entry)
        assert provider.estimate_cost(10.0) == 0.0
        assert provider.estimate_cost(60.0) == 0.0

    def test_cancel(self, entry: ProviderRegistryEntry) -> None:
        provider = MockVideoProvider(entry=entry)
        job = provider.submit(provider.build_payload("test"), "S001-01")
        result = provider.cancel(job)
        assert result is True
        assert job.status == "cancelled"

    def test_scenario_submit_error(self, entry: ProviderRegistryEntry) -> None:
        provider = MockVideoProvider(
            entry=entry,
            scenario_steps=[
                ScenarioStep(
                    shot_id="S001-01",
                    submit="error",
                    error_code="quota_exhausted",
                )
            ],
        )
        payload = provider.build_payload("test")
        with pytest.raises(RuntimeError, match="quota_exhausted"):
            provider.submit(payload, "S001-01")

    def test_scenario_slow_poll(self, entry: ProviderRegistryEntry) -> None:
        provider = MockVideoProvider(
            entry=entry,
            scenario_steps=[ScenarioStep(shot_id="S001-01", polls_before_complete=5)],
        )
        payload = provider.build_payload("test")
        job = provider.submit(payload, "S001-01")

        for _ in range(4):
            job = provider.poll(job)
            assert job.status == "processing"

        job = provider.poll(job)
        assert job.status == "completed"

    def test_scenario_corrupt_output(self, entry: ProviderRegistryEntry) -> None:
        provider = MockVideoProvider(
            entry=entry,
            scenario_steps=[
                ScenarioStep(
                    shot_id="S001-01",
                    submit="success",
                    polls_before_complete=1,
                    output="corrupt",
                )
            ],
        )
        payload = provider.build_payload("test")
        job = provider.submit(payload, "S001-01")
        provider.poll(job)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = provider.download(job, tmpdir)
            data = Path(path).read_bytes()
            assert data == b"CORRUPT_DATA"

    def test_scenario_sequential_chain(self, entry: ProviderRegistryEntry) -> None:
        provider = MockVideoProvider(
            entry=entry,
            scenario_steps=[
                ScenarioStep(shot_id="S001-01", polls_before_complete=2),
                ScenarioStep(shot_id="S001-02", polls_before_complete=1),
                ScenarioStep(shot_id="S001-03", polls_before_complete=3),
            ],
        )
        for sid in ["S001-01", "S001-02", "S001-03"]:
            job = provider.submit(provider.build_payload("test"), sid)
            while job.status != "completed":
                job = provider.poll(job)
            assert job.status == "completed"

    def test_frame_extraction_failure(self, entry: ProviderRegistryEntry) -> None:
        provider = MockVideoProvider(
            entry=entry,
            scenario_steps=[
                ScenarioStep(
                    shot_id="S001-01",
                    polls_before_complete=1,
                    last_frame="failed",
                    mid_frame="failed",
                )
            ],
        )
        payload = provider.build_payload("test")
        job = provider.submit(payload, "S001-01")
        provider.poll(job)

        with tempfile.TemporaryDirectory() as tmpdir:
            provider.download(job, tmpdir)
            # Frame files should NOT exist
            assert not (Path(tmpdir) / "S001-01_last.png").exists()
            assert not (Path(tmpdir) / "S001-01_mid.png").exists()
