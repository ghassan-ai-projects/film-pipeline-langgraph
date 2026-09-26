"""Provider contracts, mocks, health, registry, and credential policy.

Concrete real adapters are exported from :mod:`film_pipeline.providers.adapters`.
Mock providers and the shared adapter contract remain available here.

Credential policy is public: `studio`'s bootstrap and provider seeding ask
whether a provider is configured before selecting it, and failure classification
redacts secrets on the way out. Those callers previously reached the module by
path (``from film_pipeline.providers import credentials``); the names are
re-exported here so the declared interface matches how the package is used.
"""

from __future__ import annotations

from film_pipeline.providers.base import BaseProviderAdapter, ProviderJob
from film_pipeline.providers.catalog import (
    KNOWN_PROVIDER_IDS,
    PROVIDER_IDS_BY_MODE,
    is_known_provider,
    supported_provider_ids,
)
from film_pipeline.providers.credentials import (
    MissingProviderCredential,
    env_or_dotenv,
    is_configured,
    lookup,
    missing_provider_credentials,
    redact,
)
from film_pipeline.providers.health import ProviderHealth, ProviderHealthTracker
from film_pipeline.providers.mock_image_provider import MockImageProvider
from film_pipeline.providers.mock_provider import MockVideoProvider, ScenarioStep
from film_pipeline.providers.registry import ProviderRegistry

__all__ = [
    "KNOWN_PROVIDER_IDS",
    "PROVIDER_IDS_BY_MODE",
    "BaseProviderAdapter",
    "MissingProviderCredential",
    "MockImageProvider",
    "MockVideoProvider",
    "ProviderHealth",
    "ProviderHealthTracker",
    "ProviderJob",
    "ProviderRegistry",
    "ScenarioStep",
    "env_or_dotenv",
    "is_configured",
    "is_known_provider",
    "lookup",
    "missing_provider_credentials",
    "redact",
    "supported_provider_ids",
]
