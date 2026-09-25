"""Compatibility aliases for :mod:`film_pipeline.studio.logging_setup`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.studio.logging_setup import _BACKUP_COUNT as _BACKUP_COUNT
from film_pipeline.studio.logging_setup import _LEVEL_ENV_VAR as _LEVEL_ENV_VAR
from film_pipeline.studio.logging_setup import _MARKER_ATTR as _MARKER_ATTR
from film_pipeline.studio.logging_setup import _MAX_BYTES as _MAX_BYTES
from film_pipeline.studio.logging_setup import _resolve_level as _resolve_level
from film_pipeline.studio.logging_setup import configure_logging as configure_logging

__all__ = [
    "configure_logging",
]
