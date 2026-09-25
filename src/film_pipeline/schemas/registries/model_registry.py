"""Model registry entry schema."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas.base import SchemaBase


class ModelRegistryEntry(SchemaBase):
    """Discoverable record for a model backend."""

    model_id: str
    provider: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    cost_profile_ref: str = ""
    context_limit_tokens: int = Field(default=128_000, ge=0)
    modalities: list[str] = Field(default_factory=lambda: ["text"])
    preferred_tasks: list[str] = Field(default_factory=list)
    avoid_for: list[str] = Field(default_factory=list)
    enabled: bool = True


class ModelRegistry(SchemaBase):
    """Aggregate model registry."""

    models: list[ModelRegistryEntry] = Field(default_factory=list)
