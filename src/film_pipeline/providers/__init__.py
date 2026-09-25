"""Provider contracts, mocks, health, and registry.

Concrete real adapters are exported from :mod:`film_pipeline.providers.adapters`.
Mock providers and the shared adapter contract remain available here.
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
