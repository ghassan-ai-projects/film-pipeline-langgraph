"""Compatibility aliases for :mod:`film_pipeline.orchestration.router`."""

from __future__ import annotations

from film_pipeline.orchestration.router import GATE_FACTS as GATE_FACTS
from film_pipeline.orchestration.router import AgentRouteResult as AgentRouteResult
from film_pipeline.orchestration.router import RouterResult as RouterResult

# Private helpers still reached through this path during migration.
from film_pipeline.orchestration.router import compute_actions as compute_actions
from film_pipeline.orchestration.router import get_blockers_for_state as get_blockers_for_state
from film_pipeline.orchestration.router import public_blocked_actions as public_blocked_actions
from film_pipeline.orchestration.router import route_agent as route_agent

__all__ = [
    "GATE_FACTS",
    "AgentRouteResult",
    "RouterResult",
    "compute_actions",
    "get_blockers_for_state",
    "public_blocked_actions",
    "route_agent",
]
