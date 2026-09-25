"""Compatibility aliases for :mod:`film_pipeline.storage.storage`."""

from __future__ import annotations

from film_pipeline.storage.storage import LAYOUT_VERSION as LAYOUT_VERSION
from film_pipeline.storage.storage import MARKER_FILENAME as MARKER_FILENAME
from film_pipeline.storage.storage import MARKER_SCHEMA_VERSION as MARKER_SCHEMA_VERSION
from film_pipeline.storage.storage import PROFILE_PRODUCTION as PROFILE_PRODUCTION
from film_pipeline.storage.storage import PROFILE_SANDBOX as PROFILE_SANDBOX
from film_pipeline.storage.storage import STORAGE_ROOT_ENV as STORAGE_ROOT_ENV
from film_pipeline.storage.storage import StorageMarker as StorageMarker
from film_pipeline.storage.storage import StorageRootError as StorageRootError

# Private helpers still reached through this path during migration.
from film_pipeline.storage.storage import _logger as _logger
from film_pipeline.storage.storage import default_checkpoints_root as default_checkpoints_root
from film_pipeline.storage.storage import default_run_root as default_run_root
from film_pipeline.storage.storage import default_runtime_root as default_runtime_root
from film_pipeline.storage.storage import default_storage_root as default_storage_root
from film_pipeline.storage.storage import ensure_storage_root as ensure_storage_root
from film_pipeline.storage.storage import init_storage_root as init_storage_root
from film_pipeline.storage.storage import marker_path as marker_path
from film_pipeline.storage.storage import read_marker as read_marker
from film_pipeline.storage.storage import resolve_storage_root as resolve_storage_root

__all__ = [
    "LAYOUT_VERSION",
    "MARKER_FILENAME",
    "MARKER_SCHEMA_VERSION",
    "PROFILE_PRODUCTION",
    "PROFILE_SANDBOX",
    "STORAGE_ROOT_ENV",
    "StorageMarker",
    "StorageRootError",
    "default_checkpoints_root",
    "default_run_root",
    "default_runtime_root",
    "default_storage_root",
    "ensure_storage_root",
    "init_storage_root",
    "marker_path",
    "read_marker",
    "resolve_storage_root",
]
