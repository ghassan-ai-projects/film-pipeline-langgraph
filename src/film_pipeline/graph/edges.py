"""Compatibility aliases for :mod:`film_pipeline.orchestration.edges`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.orchestration.edges import _HUMAN_GATE_ACTIONS as _HUMAN_GATE_ACTIONS
from film_pipeline.orchestration.edges import _REPAIR_ACTIONS as _REPAIR_ACTIONS
from film_pipeline.orchestration.edges import _is_auto_mode as _is_auto_mode
from film_pipeline.orchestration.edges import _record_stall as _record_stall
from film_pipeline.orchestration.edges import after_approval as after_approval
from film_pipeline.orchestration.edges import after_phase as after_phase
from film_pipeline.orchestration.edges import compute_actions as compute_actions
from film_pipeline.orchestration.edges import is_stalled as is_stalled
from film_pipeline.orchestration.edges import next_phase as next_phase

__all__ = [
    "after_approval",
    "after_phase",
    "compute_actions",
    "is_stalled",
    "next_phase",
]
