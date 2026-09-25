"""Compatibility aliases for :mod:`film_pipeline.studio._provider_seeds`."""

from __future__ import annotations

from film_pipeline.studio._provider_seeds import default_video_provider as default_video_provider
from film_pipeline.studio._provider_seeds import (
    seed_default_provider_adapters as seed_default_provider_adapters,
)
from film_pipeline.studio._provider_seeds import (
    seed_default_provider_health as seed_default_provider_health,
)

__all__ = [
    "default_video_provider",
    "seed_default_provider_adapters",
    "seed_default_provider_health",
]
