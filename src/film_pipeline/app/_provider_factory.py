"""Compatibility aliases for :mod:`film_pipeline.studio._provider_factory`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.studio._provider_factory import _default_capabilities as _default_capabilities
from film_pipeline.studio._provider_factory import _default_cost_profile as _default_cost_profile
from film_pipeline.studio._provider_factory import _default_models as _default_models
from film_pipeline.studio._provider_factory import build_provider_adapter as build_provider_adapter

__all__ = [
    "build_provider_adapter",
]
