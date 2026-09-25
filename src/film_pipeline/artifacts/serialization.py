"""Compatibility aliases for :mod:`film_pipeline.storage.serialization`."""

from __future__ import annotations

from film_pipeline.storage.serialization import NonFiniteNumberError as NonFiniteNumberError

# Private helpers still reached through this path during migration.
from film_pipeline.storage.serialization import _fsync_directory as _fsync_directory
from film_pipeline.storage.serialization import _reject_non_finite as _reject_non_finite
from film_pipeline.storage.serialization import atomic_write_text as atomic_write_text
from film_pipeline.storage.serialization import dump_json as dump_json
from film_pipeline.storage.serialization import write_json_atomic as write_json_atomic

__all__ = [
    "NonFiniteNumberError",
    "atomic_write_text",
    "dump_json",
    "write_json_atomic",
]
