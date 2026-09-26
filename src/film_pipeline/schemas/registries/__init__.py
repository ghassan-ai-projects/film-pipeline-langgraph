"""Registry entry schemas (provider, validator, model).

The agent roster's registration model is :class:`AgentRegistration` in
``film_pipeline.schemas.handoff`` — it is the single record for that concept and
is what ``agents.registry`` validates and what ``agents.roster`` populates.

Only *entry* records live here. The three aggregate wrappers
(``ModelRegistry``, ``ProviderRegistry``, ``ValidatorRegistry``) were deleted:
each was a list-of-entries with no reader anywhere in ``src/``, and each shared
its name with a live, differently-shaped registry class in the package that
actually owns that concern (``providers.registry``, ``validation.registry``).
Keeping them meant two same-named concepts per registry, one of them dead.
"""

from __future__ import annotations

from film_pipeline.schemas.registries.model_registry import ModelRegistryEntry
from film_pipeline.schemas.registries.provider_registry import (
    CostProfile,
    ProviderCapabilities,
    ProviderRegistryEntry,
)
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)

__all__ = [
    "CostProfile",
    "ModelRegistryEntry",
    "ProviderCapabilities",
    "ProviderRegistryEntry",
    "ValidatorRegistryEntry",
    "ValidatorThresholds",
]
