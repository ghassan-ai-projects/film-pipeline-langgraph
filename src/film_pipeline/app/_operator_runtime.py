"""Compatibility aliases for :mod:`film_pipeline.studio._operator_runtime`."""

from __future__ import annotations

from film_pipeline.studio._operator_runtime import StudioRuntimeProvider as StudioRuntimeProvider

# Private helpers still reached through this path during migration.
from film_pipeline.studio._operator_runtime import (
    _ProfileProviderComposition as _ProfileProviderComposition,
)
from film_pipeline.studio._operator_runtime import (
    missing_profile_credentials as missing_profile_credentials,
)
from film_pipeline.studio._operator_runtime import (
    profile_provider_composition as profile_provider_composition,
)
from film_pipeline.studio._operator_runtime import (
    register_profile_providers as register_profile_providers,
)
from film_pipeline.studio._operator_runtime import runtime_for as runtime_for

__all__ = [
    "StudioRuntimeProvider",
    "missing_profile_credentials",
    "profile_provider_composition",
    "register_profile_providers",
    "runtime_for",
]
