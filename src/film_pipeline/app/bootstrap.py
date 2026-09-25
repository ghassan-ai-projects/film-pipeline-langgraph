"""Compatibility aliases for :mod:`film_pipeline.studio.bootstrap`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.studio.bootstrap import (
    _missing_kb_manifest_issues as _missing_kb_manifest_issues,
)
from film_pipeline.studio.bootstrap import (
    _missing_profiles_dir_issues as _missing_profiles_dir_issues,
)
from film_pipeline.studio.bootstrap import (
    _missing_real_mode_credentials_issues as _missing_real_mode_credentials_issues,
)
from film_pipeline.studio.bootstrap import (
    _unusable_artifacts_dir_issues as _unusable_artifacts_dir_issues,
)
from film_pipeline.studio.bootstrap import bootstrap_ok as bootstrap_ok
from film_pipeline.studio.bootstrap import validate_environment as validate_environment

__all__ = [
    "bootstrap_ok",
    "validate_environment",
]
