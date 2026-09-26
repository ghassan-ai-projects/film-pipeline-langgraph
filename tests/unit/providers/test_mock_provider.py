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

    def test_poll_with_error_code(self, entry: ProviderRegistryEntry) -> None:
        """Poll with error_code triggers failure when polls exceed threshold."""
        provider = MockVideoProvider(
            entry=entry,
            scenario_steps=[
                ScenarioStep(
                    shot_id="S001-01",
                    submit="success",
                    polls_before_complete=0,
                    error_code="network_error",
                )
            ],
        )
        payload = provider.build_payload("test")
        job = provider.submit(payload, "S001-01")
        # First poll: polls_before_complete=0, error_code set, count=1 > 0 → failure
        job = provider.poll(job)
        assert job.status == "failed"
        assert job.metadata == {"error": "network_error"}

    def test_extract_metadata_no_json_fallback(self, entry: ProviderRegistryEntry) -> None:
        """Metadata extraction fallback when no companion JSON exists."""
        provider = MockVideoProvider(entry=entry)
        payload = provider.build_payload("test")
        job = provider.submit(payload, "S001-01")
        provider.poll(job)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = provider.download(job, tmpdir)
            # Remove the metadata JSON to test fallback
            meta_json = Path(tmpdir) / "S001-01_metadata.json"
            if meta_json.exists():
                meta_json.unlink()
            meta = provider.extract_metadata(path)
            assert meta.get("placeholder") is True


class TestMockImageProvider:
    @pytest.fixture
    def img_entry(self) -> ProviderRegistryEntry:
        return ProviderRegistryEntry(
            provider_id="mock-image-provider",
            provider_type="image",
            models=["mock-fast"],
            capabilities=ProviderCapabilities(text_to_image=True),
            cost_profile=CostProfile(unit="image", estimated_rate_usd=0.0),
        )

    def test_build_payload(self, img_entry: ProviderRegistryEntry) -> None:
        from film_pipeline.providers.mock_image_provider import MockImageProvider

        provider = MockImageProvider(entry=img_entry)
        payload = provider.build_payload("a cat", aspect_ratio="1:1", seed=42)
        assert payload["prompt"] == "a cat"
        assert payload["aspect_ratio"] == "1:1"
        assert payload["seed"] == 42

    def test_submit_immediately_complete(self, img_entry: ProviderRegistryEntry) -> None:
        from film_pipeline.providers.mock_image_provider import MockImageProvider

        provider = MockImageProvider(entry=img_entry)
        job = provider.submit({"prompt": "test"}, "REF-01")
        assert job.status == "completed"
        assert job.job_id.startswith("mock-img-")

    def test_poll_noop(self, img_entry: ProviderRegistryEntry) -> None:
        from film_pipeline.providers.mock_image_provider import MockImageProvider

        provider = MockImageProvider(entry=img_entry)
        job = provider.submit({"prompt": "test"}, "REF-01")
        job = provider.poll(job)
        assert job.status == "completed"

    def test_download_creates_png(self, img_entry: ProviderRegistryEntry) -> None:
        from film_pipeline.providers.mock_image_provider import MockImageProvider

        provider = MockImageProvider(entry=img_entry)
        job = provider.submit({"prompt": "test"}, "REF-01")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = provider.download(job, tmpdir)
            assert Path(path).suffix == ".png"
            assert Path(path).exists()

    def test_extract_metadata(self, img_entry: ProviderRegistryEntry) -> None:
        from film_pipeline.providers.mock_image_provider import MockImageProvider

        provider = MockImageProvider(entry=img_entry)
        job = provider.submit({"prompt": "test"}, "REF-01")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = provider.download(job, tmpdir)
            meta = provider.extract_metadata(path)
            assert meta["placeholder"] is True
            assert meta["size_bytes"] > 0

    def test_extract_metadata_missing_file(self, img_entry: ProviderRegistryEntry) -> None:
        from film_pipeline.providers.mock_image_provider import MockImageProvider

        provider = MockImageProvider(entry=img_entry)
        meta = provider.extract_metadata("/nonexistent/path.png")
        assert meta["size_bytes"] == 0
