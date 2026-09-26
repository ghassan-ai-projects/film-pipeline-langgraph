"""Provider registry entry schema."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas.base import SchemaBase


class ProviderCapabilities(SchemaBase):
    """What a provider can do."""

    text_to_video: bool = False
    image_to_video: bool = False
    text_to_image: bool = False
    image_to_image: bool = False
    return_last_frame: bool = False
    return_mid_frame: bool = False
    supports_audio: bool = False
    supports_seed: bool = False
    max_duration_seconds: int = Field(default=15, ge=1)
    aspect_ratios: list[str] = Field(default_factory=lambda: ["16:9"])
    supported_resolutions: list[str] = Field(default_factory=lambda: ["720p"])


class CostProfile(SchemaBase):
    """Cost basis for a provider."""

    unit: str = Field(default="second", description="'second' | 'image' | 'request'.")
    estimated_rate_usd: float = Field(default=0.0, ge=0)


class ProviderRegistryEntry(SchemaBase):
    """Discoverable record for a provider."""

    provider_id: str
    provider_type: str = Field(description="'video' | 'image' | 'audio' | 'music' | 'tts'.")
    models: list[str] = Field(default_factory=list)
    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)
    cost_profile: CostProfile = Field(default_factory=CostProfile)
    failure_modes: list[str] = Field(default_factory=list)
    enabled: bool = True
