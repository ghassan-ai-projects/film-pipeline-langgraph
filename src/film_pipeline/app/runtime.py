"""Compatibility aliases for :mod:`film_pipeline.studio.runtime`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.studio.runtime import _RUNTIME as _RUNTIME
from film_pipeline.studio.runtime import _RUNTIME_MODE_OVERRIDE as _RUNTIME_MODE_OVERRIDE
from film_pipeline.studio.runtime import StudioRuntime as StudioRuntime
from film_pipeline.studio.runtime import _build_services_for_mode as _build_services_for_mode
from film_pipeline.studio.runtime import _configured_server_mode as _configured_server_mode
from film_pipeline.studio.runtime import _logger as _logger
from film_pipeline.studio.runtime import _normalize_server_mode as _normalize_server_mode
from film_pipeline.studio.runtime import create_runtime as create_runtime
from film_pipeline.studio.runtime import get_runtime as get_runtime
from film_pipeline.studio.runtime import reset_runtime as reset_runtime

__all__ = [
    "StudioRuntime",
    "create_runtime",
    "get_runtime",
    "reset_runtime",
]
