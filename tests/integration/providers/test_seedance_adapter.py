"""Integration test: Seedance adapter contract compliance with mocked HTTP."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

import pytest
from tests._helpers import _mock_opener

from film_pipeline.providers.adapters.seedance_openrouter import (
    SeedanceOpenRouterProvider,
)
from film_pipeline.schemas.registries.provider_registry import (
    CostProfile,
    ProviderCapabilities,
    ProviderRegistryEntry,
)


@pytest.fixture
def entry() -> ProviderRegistryEntry:
    return ProviderRegistryEntry(
        provider_id="seedance-openrouter",
        provider_type="video",
        models=["bytedance/seedance-2.0"],
        capabilities=ProviderCapabilities(
            text_to_video=True,
            image_to_video=True,
            return_last_frame=True,
            max_duration_seconds=15,
            aspect_ratios=["16:9", "9:16"],
        ),
        cost_profile=CostProfile(unit="second", estimated_rate_usd=0.18),
        failure_modes=["timeout", "quota", "moderation", "download_failure"],
    )


@pytest.mark.integration
class TestSeedanceAdapter:
    def test_build_payload(self, entry: ProviderRegistryEntry) -> None:
        provider = _make_provider(entry)
        payload = provider.build_payload("test prompt", duration=8.0)
        assert payload["model"] == "bytedance/seedance-2.0"
        assert payload["messages"][0]["content"] == "test prompt"

    def test_build_payload_with_references(self, entry: ProviderRegistryEntry) -> None:
        provider = _make_provider(entry)
        payload = provider.build_payload("test", references=["ref1.png", "ref2.png"])
        assert payload["images"] == ["ref1.png", "ref2.png"]

    def test_estimate_cost(self, entry: ProviderRegistryEntry) -> None:
        provider = _make_provider(entry)
        cost = provider.estimate_cost(10.0)
        assert cost == pytest.approx(1.80)

    def test_extract_metadata(self, entry: ProviderRegistryEntry) -> None:
        provider = _make_provider(entry)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.mp4"
            path.write_bytes(b"data")
            meta = provider.extract_metadata(str(path))
            assert meta["size_bytes"] == 4

    def test_extract_metadata_missing(self, entry: ProviderRegistryEntry) -> None:
        provider = _make_provider(entry)
        meta = provider.extract_metadata("/nonexistent/file.mp4")
        assert meta["error"] == "file_not_found"

    def test_submit_with_mocked_http(self, entry: ProviderRegistryEntry) -> None:
        provider = _make_provider(entry)
        provider._http_opener = _mock_opener({"id": "job-123"})
        # Patch sleep to avoid 20s delay
        with mock.patch("time.sleep"):
            job = provider.submit(provider.build_payload("test"), "S001")
        assert job.job_id == "job-123"
        assert job.status == "submitted"

    def test_cancel(self, entry: ProviderRegistryEntry) -> None:
        provider = _make_provider(entry)
        provider._http_opener = _mock_opener({"ok": True})
        with mock.patch("time.sleep"):
            job = provider.submit(provider.build_payload("test"), "S001")
            assert provider.cancel(job) is True
            assert job.status == "cancelled"

    def test_cancel_failure(self, entry: ProviderRegistryEntry) -> None:
        """HTTP 500 on submit raises RuntimeError."""
        provider = _make_provider(entry)
        provider._http_opener = _mock_opener({}, code=500)
        with mock.patch("time.sleep"), pytest.raises(RuntimeError, match="OpenRouter"):
            provider.submit(provider.build_payload("test"), "S001")

    def test_download(self, entry: ProviderRegistryEntry) -> None:
        provider = _make_provider(entry)
        provider._http_opener = _mock_opener({"url": "https://example.com/video.mp4"})
        with mock.patch("time.sleep"):
            job = provider.submit(provider.build_payload("test"), "S001")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = provider.download(job, tmpdir)
            assert Path(path).exists()

    def test_full_lifecycle(self, entry: ProviderRegistryEntry) -> None:
        """Build → submit → poll → download → metadata."""
        provider = _make_provider(entry)
        # Mock the submit POST
        provider._http_opener = _mock_opener({"id": "job-full"})

        with mock.patch("time.sleep"):
            payload = provider.build_payload("full test")
            job = provider.submit(payload, "S001")
            assert job.status == "submitted"

            job = provider.poll(job)
            assert job.status == "completed"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = provider.download(job, tmpdir)
            meta = provider.extract_metadata(path)
            assert meta["provider"] == "seedance-openrouter"


def _make_provider(entry: ProviderRegistryEntry) -> SeedanceOpenRouterProvider:
    """Create a provider without real API key (bypasses credential check)."""
    with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-test-key"}):
        return SeedanceOpenRouterProvider(entry=entry)
