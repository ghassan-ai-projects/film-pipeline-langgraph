"""Dynamic action router — computes eligible actions and selects agents.

This module is the stable import surface; the implementation lives in two
cohesive siblings:

1. Action routing (:mod:`film_pipeline.graph._action_routing`): what action
   to take next, taking into account provider health, budget state, failure
   decisions, revision requests, and profile policy.
2. Agent routing (:mod:`film_pipeline.graph._agent_routing`): which agent
   performs the action, with KB context selection.

The orchestrator state domain (``orchestrator_state.py``) is the source
of truth for all routing-relevant state beyond the base graph fields.
"""

from __future__ import annotations

from film_pipeline.graph._action_routing import (
    APPROVAL_GATES,
    PHASE_ORDER,
    RouterResult,
    compute_actions,
)
from film_pipeline.graph._agent_routing import (
    AgentRouteResult,
    route_agent,
)

__all__ = [
    "APPROVAL_GATES",
    "PHASE_ORDER",
    "AgentRouteResult",
    "RouterResult",
    "compute_actions",
    "route_agent",
]
