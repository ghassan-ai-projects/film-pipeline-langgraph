"""Provider adapter factory for runtime registration from config/profile data."""

from __future__ import annotations

from film_pipeline.providers.adapters.imagen4_gemini import Imagen4GeminiProvider
from film_pipeline.providers.adapters.seedance_openrouter import SeedanceOpenRouterProvider
from film_pipeline.providers.adapters.veo_fast import VeoFastProvider
from film_pipeline.providers.mock_image_provider import MockImageProvider
from film_pipeline.providers.mock_provider import MockVideoProvider
from film_pipeline.schemas.registries.provider_registry import (
    CostProfile,
    ProviderCapabilities,
    ProviderRegistryEntry,
)


def build_provider_adapter(
    provider_id: str,
    *,
    provider_type: str = "video",
    models: list[str] | None = None,
) -> object:
    """Build a provider adapter with sensible defaults for the known providers."""
    model_list = list(models or _default_models(provider_id))
    entry = ProviderRegistryEntry(
        provider_id=provider_id,
        provider_type=provider_type,
        models=model_list,
        capabilities=_default_capabilities(provider_id, provider_type),
        cost_profile=_default_cost_profile(provider_id),
    )

    if provider_id == "seedance-openrouter":
        return SeedanceOpenRouterProvider(entry=entry)
    if provider_id in {"veo-fast", "veo-3.1-fast"}:
        return VeoFastProvider(entry=entry)
    if provider_id in {"gemini-imagen-4", "imagen-4"}:
        return Imagen4GeminiProvider(entry=entry)
    if provider_id == "mock-video-provider":
        return MockVideoProvider(entry=entry)
    if provider_id == "mock-image-provider":
        return MockImageProvider(entry=entry)
    raise ValueError(f"Unsupported provider_id: {provider_id}")


def _default_models(provider_id: str) -> list[str]:
    return {
        "seedance-openrouter": ["bytedance/seedance-2.0"],
        "veo-fast": ["veo-3.1-fast"],
        "veo-3.1-fast": ["veo-3.1-fast"],
        "gemini-imagen-4": ["imagen-4.0-fast-generate-001"],
        "imagen-4": ["imagen-4.0-fast-generate-001"],
        "mock-video-provider": ["mock-fast"],
        "mock-image-provider": ["mock-fast"],
    }.get(provider_id, [])


def _default_capabilities(provider_id: str, provider_type: str) -> ProviderCapabilities:
    if provider_id == "seedance-openrouter":
        return ProviderCapabilities(
            text_to_video=True,
            image_to_video=True,
            return_last_frame=True,
            max_duration_seconds=15,
            aspect_ratios=["16:9", "9:16"],
            supported_resolutions=["480p", "720p", "1080p"],
        )
    if provider_id in {"veo-fast", "veo-3.1-fast"}:
        return ProviderCapabilities(
            text_to_video=True,
            image_to_video=True,
            return_last_frame=True,
            max_duration_seconds=15,
            aspect_ratios=["16:9", "9:16"],
            supported_resolutions=["720p", "1080p"],
        )
    if provider_id in {"gemini-imagen-4", "imagen-4"}:
        return ProviderCapabilities(
            text_to_image=True,
            image_to_image=True,
            supports_seed=True,
            max_duration_seconds=1,
            aspect_ratios=["16:9", "9:16", "1:1", "4:3", "3:4"],
            supported_resolutions=["1024x1024", "1536x1024", "1024x1536", "2048x2048"],
        )
    if provider_type == "image":
        return ProviderCapabilities(
            text_to_image=True,
            image_to_image=True,
            supports_seed=True,
            max_duration_seconds=1,
            aspect_ratios=["16:9", "1:1"],
            supported_resolutions=["1024x1024"],
        )
    return ProviderCapabilities(
        text_to_video=True,
        image_to_video=True,
        return_last_frame=True,
        max_duration_seconds=30,
        aspect_ratios=["16:9"],
        supported_resolutions=["480p", "720p"],
    )


def _default_cost_profile(provider_id: str) -> CostProfile:
    from film_pipeline.providers.pricing import PROVIDER_PRICING, rate_for, unit_for

    if provider_id in PROVIDER_PRICING:
        return CostProfile(unit=unit_for(provider_id), estimated_rate_usd=rate_for(provider_id))
    return CostProfile(unit="second", estimated_rate_usd=0.0)
