"""Provider adapters and registry.

Real providers (Seedance, Veo) and the mock provider all implement the same
:class:`BaseProviderAdapter` contract.
"""

from __future__ import annotations

from film_pipeline.providers.base import BaseProviderAdapter, ProviderJob
from film_pipeline.providers.health import ProviderHealth, ProviderHealthTracker
from film_pipeline.providers.mock_image_provider import MockImageProvider
from film_pipeline.providers.mock_provider import MockVideoProvider, ScenarioStep
from film_pipeline.providers.registry import ProviderRegistry

__all__ = [
    "BaseProviderAdapter",
    "MockImageProvider",
    "MockVideoProvider",
    "ProviderHealth",
    "ProviderHealthTracker",
    "ProviderJob",
    "ProviderRegistry",
    "ScenarioStep",
]
