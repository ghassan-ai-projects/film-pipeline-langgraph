"""Compatibility aliases for :mod:`film_pipeline.orchestration._agent_routing`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.orchestration._agent_routing import (
    _PHASE_DEFAULT_AGENTS as _PHASE_DEFAULT_AGENTS,
)
from film_pipeline.orchestration._agent_routing import _REPAIR_CAPABILITIES as _REPAIR_CAPABILITIES
from film_pipeline.orchestration._agent_routing import _REVIEW_CAPABILITIES as _REVIEW_CAPABILITIES
from film_pipeline.orchestration._agent_routing import AgentRouteResult as AgentRouteResult
from film_pipeline.orchestration._agent_routing import (
    _build_kb_context_ref as _build_kb_context_ref,
)
from film_pipeline.orchestration._agent_routing import _capability_route as _capability_route
from film_pipeline.orchestration._agent_routing import _default_agent_for as _default_agent_for
from film_pipeline.orchestration._agent_routing import (
    _failure_handler_route as _failure_handler_route,
)
from film_pipeline.orchestration._agent_routing import _first_registered as _first_registered
from film_pipeline.orchestration._agent_routing import (
    _normalized_task_type as _normalized_task_type,
)
from film_pipeline.orchestration._agent_routing import _repair_route as _repair_route
from film_pipeline.orchestration._agent_routing import (
    _resolve_review_strategy as _resolve_review_strategy,
)
from film_pipeline.orchestration._agent_routing import _review_candidates as _review_candidates
from film_pipeline.orchestration._agent_routing import _review_route as _review_route
from film_pipeline.orchestration._agent_routing import route_agent as route_agent

__all__ = [
    "AgentRouteResult",
    "route_agent",
]
