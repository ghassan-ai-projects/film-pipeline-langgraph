"""Compatibility aliases for devharness mock human actor.

Re-exports from the canonical owner. Only symbols with real consumers are
kept, so strict mypy sees an explicit export surface.
"""

from film_pipeline.devharness.mock_human import DecisionProfile as DecisionProfile
from film_pipeline.devharness.mock_human import MockHumanActor as MockHumanActor

__all__ = ["DecisionProfile", "MockHumanActor"]
