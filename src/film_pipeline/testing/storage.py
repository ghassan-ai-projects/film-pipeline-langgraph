"""Compatibility aliases for devharness storage.

Re-exports from the canonical owner. Only symbols with real consumers are
kept, so strict mypy sees an explicit export surface.
"""

from film_pipeline.devharness.storage import make_store as make_store
from film_pipeline.devharness.storage import (
    sandbox_store_root as sandbox_store_root,
)

__all__ = ["make_store", "sandbox_store_root"]
