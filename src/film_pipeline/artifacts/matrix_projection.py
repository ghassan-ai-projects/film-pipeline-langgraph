"""Compatibility aliases for :mod:`film_pipeline.storage.matrix_projection`."""

from __future__ import annotations

from film_pipeline.storage.matrix_projection import _load_base_matrix as _load_base_matrix
from film_pipeline.storage.matrix_projection import _load_patch as _load_patch

# Private helpers still reached through this path during migration.
from film_pipeline.storage.matrix_projection import _MatrixStore as _MatrixStore
from film_pipeline.storage.matrix_projection import _parse_artifact_ref as _parse_artifact_ref
from film_pipeline.storage.matrix_projection import materialize_matrix as materialize_matrix

__all__ = [
    "materialize_matrix",
]
