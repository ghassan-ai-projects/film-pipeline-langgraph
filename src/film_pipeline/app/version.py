"""Compatibility aliases for :mod:`film_pipeline.studio.version`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.studio.version import _VERSION_INFO as _VERSION_INFO
from film_pipeline.studio.version import BUILD_LABEL as BUILD_LABEL
from film_pipeline.studio.version import __version__ as __version__

__all__ = [
    "BUILD_LABEL",
]
