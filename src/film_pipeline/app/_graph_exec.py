"""Compatibility aliases for :mod:`film_pipeline.studio._graph_exec`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.studio._graph_exec import _approval_stalled as _approval_stalled
from film_pipeline.studio._graph_exec import _approve_phase_artifacts as _approve_phase_artifacts
from film_pipeline.studio._graph_exec import (
    _has_pending_human_interrupt as _has_pending_human_interrupt,
)
from film_pipeline.studio._graph_exec import _logger as _logger
from film_pipeline.studio._graph_exec import _resume_after_approval as _resume_after_approval
from film_pipeline.studio._graph_exec import advance_to_next_phase as advance_to_next_phase
from film_pipeline.studio._graph_exec import approve_phase as approve_phase
from film_pipeline.studio._graph_exec import auto_checkpoint as auto_checkpoint
from film_pipeline.studio._graph_exec import ensure_graph as ensure_graph
from film_pipeline.studio._graph_exec import request_revision as request_revision
from film_pipeline.studio._graph_exec import run_graph as run_graph
from film_pipeline.studio._graph_exec import run_phase_node as run_phase_node
from film_pipeline.studio._graph_exec import run_validation as run_validation
from film_pipeline.studio._graph_exec import save_graph_state as save_graph_state

__all__ = [
    "advance_to_next_phase",
    "approve_phase",
    "auto_checkpoint",
    "ensure_graph",
    "request_revision",
    "run_graph",
    "run_phase_node",
    "run_validation",
    "save_graph_state",
]
