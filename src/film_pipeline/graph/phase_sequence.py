"""Compatibility aliases for :mod:`film_pipeline.orchestration.phase_sequence`."""

from __future__ import annotations

from film_pipeline.orchestration.phase_sequence import PHASE_NODES as PHASE_NODES
from film_pipeline.orchestration.phase_sequence import PHASE_ORDER as PHASE_ORDER
from film_pipeline.orchestration.phase_sequence import next_phase as next_phase

__all__ = [
    "PHASE_NODES",
    "PHASE_ORDER",
    "next_phase",
]
