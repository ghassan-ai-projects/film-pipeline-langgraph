"""Tests for app-owned provider adapter construction."""

from __future__ import annotations

import pytest

from film_pipeline.providers import MockImageProvider, MockVideoProvider
from film_pipeline.providers.adapters import (
    Imagen4GeminiProvider,
    SeedanceOpenRouterProvider,
    VeoFastProvider,
    imagen4_gemini,
    seedance_openrouter,
)
from film_pipeline.providers.base import BaseProviderAdapter
from film_pipeline.schemas.registries.provider_registry import ProviderCapabilities
from film_pipeline.studio._provider_factory import build_provider_adapter


@pytest.fixture(autouse=True)
def isolate_adapter_credential_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep factory construction tests independent of local credentials."""
    monkeypatch.setattr(seedance_openrouter, "lookup", lambda _provider_id: None)
    monkeypatch.setattr(imagen4_gemini, "lookup", lambda _provider_id: None)


@pytest.mark.parametrize(
    (
        "provider_id",
        "provider_type",
        "adapter_type",
        "default_model",
        "cost_unit",
        "estimated_rate_usd",
        "capabilities",
    ),
    [
        pytest.param(
            "seedance-openrouter",
            "video",
            SeedanceOpenRouterProvider,
            "bytedance/seedance-2.0",
            "second",
            0.18,
            ProviderCapabilities(
                text_to_video=True,
                image_to_video=True,
                return_last_frame=True,
                max_duration_seconds=15,
                aspect_ratios=["16:9", "9:16"],
                supported_resolutions=["480p", "720p", "1080p"],
            ),
            id="seedance",
        ),
        pytest.param(
            "veo-fast",
            "video",
            VeoFastProvider,
            "veo-3.1-fast",
            "second",
            0.10,
            ProviderCapabilities(
                text_to_video=True,
                image_to_video=True,
                return_last_frame=True,
                max_duration_seconds=15,
                aspect_ratios=["16:9", "9:16"],
                supported_resolutions=["720p", "1080p"],
            ),
            id="veo-fast",
        ),
        pytest.param(
            "veo-3.1-fast",
            "video",
            VeoFastProvider,
            "veo-3.1-fast",
            "second",
            0.10,
            ProviderCapabilities(
                text_to_video=True,
                image_to_video=True,
                return_last_frame=True,
                max_duration_seconds=15,
                aspect_ratios=["16:9", "9:16"],
                supported_resolutions=["720p", "1080p"],
            ),
            id="veo-alias",
        ),
        pytest.param(
            "gemini-imagen-4",
            "image",
            Imagen4GeminiProvider,
            "imagen-4.0-fast-generate-001",
            "image",
            0.05,
            ProviderCapabilities(
                text_to_image=True,
                image_to_image=True,
                supports_seed=True,
                max_duration_seconds=1,
                aspect_ratios=["16:9", "9:16", "1:1", "4:3", "3:4"],
                supported_resolutions=[
                    "1024x1024",
                    "1536x1024",
                    "1024x1536",
                    "2048x2048",
                ],
            ),
            id="imagen",
        ),
        pytest.param(
            "imagen-4",
            "image",
            Imagen4GeminiProvider,
            "imagen-4.0-fast-generate-001",
            "image",
            0.05,
            ProviderCapabilities(
                text_to_image=True,
                image_to_image=True,
                supports_seed=True,
                max_duration_seconds=1,
                aspect_ratios=["16:9", "9:16", "1:1", "4:3", "3:4"],
                supported_resolutions=[
                    "1024x1024",
                    "1536x1024",
                    "1024x1536",
                    "2048x2048",
                ],
            ),
            id="imagen-alias",
        ),
        pytest.param(
            "mock-video-provider",
            "video",
            MockVideoProvider,
            "mock-fast",
            "second",
            0.0,
            ProviderCapabilities(
                text_to_video=True,
                image_to_video=True,
                return_last_frame=True,
                max_duration_seconds=30,
                aspect_ratios=["16:9"],
                supported_resolutions=["480p", "720p"],
            ),
            id="mock-video",
        ),
        pytest.param(
            "mock-image-provider",
            "image",
            MockImageProvider,
            "mock-fast",
            "image",
            0.0,
            ProviderCapabilities(
                text_to_image=True,
                image_to_image=True,
                supports_seed=True,
                max_duration_seconds=1,
                aspect_ratios=["16:9", "1:1"],
                supported_resolutions=["1024x1024"],
            ),
            id="mock-image",
        ),
    ],
)
def test_build_provider_adapter_uses_default_catalog_entry(
    provider_id: str,
    provider_type: str,
    adapter_type: type[BaseProviderAdapter],
    default_model: str,
    cost_unit: str,
    estimated_rate_usd: float,
    capabilities: ProviderCapabilities,
) -> None:
    adapter = build_provider_adapter(provider_id, provider_type=provider_type)

    assert type(adapter) is adapter_type
    assert adapter.entry.provider_id == provider_id
    assert adapter.entry.provider_type == provider_type
    assert adapter.entry.models == [default_model]
    assert adapter.entry.cost_profile.unit == cost_unit
    assert adapter.entry.cost_profile.estimated_rate_usd == estimated_rate_usd
    assert adapter.entry.capabilities == capabilities


def test_build_provider_adapter_uses_default_provider_type() -> None:
    adapter = build_provider_adapter("mock-video-provider")

    assert adapter.entry.provider_type == "video"


def test_build_provider_adapter_uses_a_copy_of_explicit_models() -> None:
    models = ["custom-model"]

    adapter = build_provider_adapter(
        "seedance-openrouter",
        provider_type="video",
        models=models,
    )
    models.append("later-change")

    assert adapter.entry.models == ["custom-model"]


def test_build_provider_adapter_uses_default_models_for_empty_profile_models() -> None:
    adapter = build_provider_adapter("mock-video-provider", models=[])

    assert adapter.entry.models == ["mock-fast"]


def test_build_provider_adapter_rejects_unknown_provider_id() -> None:
    with pytest.raises(ValueError, match="Unsupported provider_id: unknown-provider"):
        build_provider_adapter("unknown-provider")
