"""Registry entry schemas (provider, validator, model).

The agent roster's registration model is :class:`AgentRegistration` in
``film_pipeline.schemas.handoff`` — it is the single record for that concept and
is what ``agents.registry`` validates and what ``agents.mvp`` populates.
"""

from __future__ import annotations

from film_pipeline.schemas.registries.model_registry import ModelRegistry, ModelRegistryEntry
from film_pipeline.schemas.registries.provider_registry import (
    CostProfile,
    ProviderCapabilities,
    ProviderRegistry,
    ProviderRegistryEntry,
)
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistry,
    ValidatorRegistryEntry,
    ValidatorThresholds,
)

__all__ = [
    "CostProfile",
    "ModelRegistry",
    "ModelRegistryEntry",
    "ProviderCapabilities",
    "ProviderRegistry",
    "ProviderRegistryEntry",
    "ValidatorRegistry",
    "ValidatorRegistryEntry",
    "ValidatorThresholds",
]
