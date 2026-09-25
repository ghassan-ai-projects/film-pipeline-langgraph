"""Compatibility aliases for devharness mock model adapter.

Re-exports from the canonical owner. Only symbols with real consumers are
kept, so strict mypy sees an explicit export surface.
"""

from film_pipeline.devharness.mock_model import MockModelAdapter as MockModelAdapter

__all__ = ["MockModelAdapter"]
