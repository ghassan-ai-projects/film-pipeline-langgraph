"""Real provider adapters — Seedance (OpenRouter) and Veo (Google).

All adapters implement BaseProviderAdapter. Mock-compatible via ``_http_opener``
injection for tests.
"""

from __future__ import annotations

from film_pipeline.providers.adapters.seedance_openrouter import (
    SeedanceOpenRouterProvider,
)
from film_pipeline.providers.adapters.veo_fast import VeoFastProvider

__all__ = [
    "SeedanceOpenRouterProvider",
    "VeoFastProvider",
]
