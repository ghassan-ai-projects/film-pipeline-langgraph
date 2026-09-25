"""Compatibility aliases for :mod:`film_pipeline.studio._provider_profiles`."""

from __future__ import annotations

from film_pipeline.studio._provider_profiles import (
    missing_profile_credentials as missing_profile_credentials,
)
from film_pipeline.studio._provider_profiles import (
    register_profile_providers as register_profile_providers,
)

__all__ = [
    "missing_profile_credentials",
    "register_profile_providers",
]
