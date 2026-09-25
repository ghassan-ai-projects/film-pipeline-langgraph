"""Compatibility aliases for :mod:`film_pipeline.studio.graph_factory`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.studio.graph_factory import (
    _AFTER_PHASE_DESTINATIONS as _AFTER_PHASE_DESTINATIONS,
)
from film_pipeline.studio.graph_factory import _APPROVAL_DESTINATIONS as _APPROVAL_DESTINATIONS
from film_pipeline.studio.graph_factory import _ROUTER_DESTINATIONS as _ROUTER_DESTINATIONS
from film_pipeline.studio.graph_factory import _default_checkpointer as _default_checkpointer
from film_pipeline.studio.graph_factory import _passthrough as _passthrough
from film_pipeline.studio.graph_factory import _register_nodes as _register_nodes
from film_pipeline.studio.graph_factory import _route_current_phase as _route_current_phase
from film_pipeline.studio.graph_factory import _wire_entry_router as _wire_entry_router
from film_pipeline.studio.graph_factory import _wire_gate_edges as _wire_gate_edges
from film_pipeline.studio.graph_factory import _wire_phase_transitions as _wire_phase_transitions
from film_pipeline.studio.graph_factory import build_graph as build_graph
from film_pipeline.studio.graph_factory import graph as graph

__all__ = [
    "build_graph",
    "graph",
]
