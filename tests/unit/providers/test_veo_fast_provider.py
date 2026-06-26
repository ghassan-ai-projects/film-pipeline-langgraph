"""Tests for the Veo Fast provider adapter contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.providers.adapters.veo_fast import VeoFastProvider
from film_pipeline.schemas.registries.provider_registry import (
    CostProfile,
    ProviderCapabilities,
    ProviderRegistryEntry,
)


@pytest.fixture
def entry() -> ProviderRegistryEntry:
    return ProviderRegistryEntry(
        provider_id="veo-fast",
        provider_type="video",
        models=["veo-3.1-fast"],
        capabilities=ProviderCapabilities(
            text_to_video=True,
            image_to_video=True,
            max_duration_seconds=8,
            aspect_ratios=["16:9", "9:16"],
        ),
        cost_profile=CostProfile(unit="second", estimated_rate_usd=0.10),
    )


def test_api_key_requires_google_key(
    entry: ProviderRegistryEntry, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("film_pipeline.providers.adapters.veo_fast.lookup", lambda _id: "")
    provider = VeoFastProvider(entry)

    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY is not set"):
        provider._api_key()


def test_build_payload_uses_prompt_duration_and_aspect_ratio(entry: ProviderRegistryEntry) -> None:
    provider = VeoFastProvider(entry)

    payload = provider.build_payload(
        "A quiet room at dawn.",
        references=["ignored-ref"],
        duration=6.5,
        aspect_ratio="9:16",
        seed=42,
    )

    assert payload == {
        "prompt": "A quiet room at dawn.",
        "duration": 6.5,
        "aspect_ratio": "9:16",
    }


def test_submit_poll_download_metadata_and_cost(
    entry: ProviderRegistryEntry, tmp_path: Path
) -> None:
    provider = VeoFastProvider(entry)
    payload = provider.build_payload("A shot.", duration=4.0)

    job = provider.submit(payload, "shot_001")

    assert job.job_id.startswith("veo-")
    assert job.shot_id == "shot_001"
    assert job.provider_id == "veo-fast"
    assert job.model == "veo-3.1-fast"
    assert job.payload == payload
    assert job.status == "submitted"

    completed = provider.poll(job)
    assert completed is job
    assert completed.status == "completed"

    path = Path(provider.download(job, str(tmp_path)))
    assert path.name == "shot_001.mp4"
    assert path.read_bytes() == b"PLACEHOLDER"
    assert provider.extract_metadata(str(path)) == {
        "file": str(path),
        "size_bytes": len(b"PLACEHOLDER"),
    }
    assert provider.extract_metadata(str(tmp_path / "missing.mp4")) == {
        "file": str(tmp_path / "missing.mp4"),
        "size_bytes": 0,
    }
    assert provider.estimate_cost(12.5, model="ignored") == 1.25


def test_submit_uses_default_model_when_entry_has_no_models() -> None:
    provider = VeoFastProvider(
        ProviderRegistryEntry(
            provider_id="veo-fast",
            provider_type="video",
            models=[],
        )
    )

    job = provider.submit({"prompt": "x"}, "shot_002")

    assert job.model == "veo-3.1-fast"
