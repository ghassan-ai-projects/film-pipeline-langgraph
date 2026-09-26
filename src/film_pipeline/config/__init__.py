"""Configuration and profile system: loading, merging, validation, resolution.

The profile-stack helpers in :mod:`film_pipeline.config.profile_resolver` are part
of this package's public surface, not an internal detail: `operations`, `studio`
and `mcp` compose project configuration through them. They were previously
reached by module path (``from film_pipeline.config import profile_resolver``),
which left the declared interface incomplete — the names are re-exported here so
consumers have one declared way in.
"""

from __future__ import annotations

from film_pipeline.config.loader import ProfileLoader, ProfileSource
from film_pipeline.config.merger import ProfileMerger
from film_pipeline.config.profile_resolver import (
    canonicalize_profile_stack,
    load_profile_flex,
    provider_specs,
    provider_specs_from_raw,
    resolve_project_config,
    resolved_config_state_keys,
)
from film_pipeline.config.resolver import ConfigResolver, ResolvedConfig
from film_pipeline.config.runtime_overrides import ENV_OVERRIDE_MAP, apply_runtime_overrides
from film_pipeline.config.validator import ConfigConflict, ConfigValidator

__all__ = [
    "ENV_OVERRIDE_MAP",
    "ConfigConflict",
    "ConfigResolver",
    "ConfigValidator",
    "ProfileLoader",
    "ProfileMerger",
    "ProfileSource",
    "ResolvedConfig",
    "apply_runtime_overrides",
    "canonicalize_profile_stack",
    "load_profile_flex",
    "provider_specs",
    "provider_specs_from_raw",
    "resolve_project_config",
    "resolved_config_state_keys",
]
