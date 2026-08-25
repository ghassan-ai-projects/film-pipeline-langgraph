"""Agent routing — role- and capability-based selection of agents.

Given a phase, a task type (``create``/``review``/``repair``/
``failure_handler``), an optional preferred capability, and an optional
agent registry, ``route_agent()`` resolves a single ``AgentRouteResult``.
Without a registry the selection falls back to the phase's default agent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from film_pipeline.schemas._base import AgentRole


@dataclass
class AgentRouteResult:
    """Result of routing a task to an agent."""

    agent_id: str
    routing_reason: str
    fallback: bool = False
    kb_context_ref: str = ""
    review_strategy: str = "single"


# Capability → role mapping for routing
_REVIEW_CAPABILITIES = {"review", "validation", "qc", "inspecting"}
_REPAIR_CAPABILITIES = {"repair", "revision", "replan", "correcting"}

# Default agent per phase (for backward compatibility)
_PHASE_DEFAULT_AGENTS: Mapping[str, str] = MappingProxyType(
    {
        "intake": "intake-classifier-agent",
        "constitution": "film-constitution-agent",
        "development": "treatment-agent",
        "script": "screenwriter-agent",
        "visual_dev": "reference-strategy-planner",
        "shot_bible": "shot-design-agent",
        "gen_planning": "provider-planning-agent",
        "qc": "clip-validator",
        "post": "failure-handling-agent",
    }
)


def _default_agent_for(phase: str) -> str:
    """Backward-compatible default agent for a phase."""
    return _PHASE_DEFAULT_AGENTS.get(phase, "orchestrator-agent")


def _normalized_task_type(task_type: str, preferred_capability: str | None) -> str:
    """Map preferred_capability to task_type when registry is absent."""
    if preferred_capability in _REPAIR_CAPABILITIES:
        return "repair"
    if preferred_capability in _REVIEW_CAPABILITIES:
        return "review"
    return task_type


def _first_registered(
    candidates: list[Any],
    routing_reason: str,
    review_strategy: str = "single",
) -> AgentRouteResult:
    """Route to the first registered candidate with its KB context ref."""
    agent = candidates[0]
    return AgentRouteResult(
        agent_id=agent.agent_id,
        routing_reason=routing_reason,
        review_strategy=review_strategy,
        kb_context_ref=_build_kb_context_ref(agent),
    )


def _failure_handler_route(registry: Any, phase: str) -> AgentRouteResult:
    """Failure-handling path: first operator agent, else orchestrator fallback."""
    candidates = registry.lookup_by_role(AgentRole.OPERATOR)
    if candidates:
        return _first_registered(candidates, f"failure-handling path for phase '{phase}'")
    return AgentRouteResult(
        agent_id="orchestrator-agent",
        routing_reason="failure handler requested but no operator agents available",
        fallback=True,
    )


def _repair_route(registry: Any, phase: str) -> AgentRouteResult:
    """Repair path: first operator agent, else explicit fall-through to creator."""
    candidates = registry.lookup_by_role(AgentRole.OPERATOR)
    if candidates:
        return _first_registered(
            candidates, f"repair path for phase '{phase}' after validation failure"
        )
    # Fall through to creator if no repair agents (explicit)
    return AgentRouteResult(
        agent_id=_default_agent_for(phase),
        routing_reason=(
            f"repair requested but no repair agents available for phase '{phase}' — using creator"
        ),
        fallback=True,
    )


def _review_candidates(registry: Any) -> list[Any]:
    """Reviewers, falling back to validators when none are registered."""
    candidates: list[Any] = registry.lookup_by_role(AgentRole.REVIEWER)
    if not candidates:
        candidates = registry.lookup_by_role(AgentRole.VALIDATOR)
    return candidates


def _review_route(state: dict[str, Any], registry: Any, phase: str) -> AgentRouteResult:
    """Review path: reviewer/validator agents with profile-driven strategy."""
    review_strategy = _resolve_review_strategy(state)
    candidates = _review_candidates(registry)
    if candidates:
        return _first_registered(
            candidates, f"review path for phase '{phase}'", review_strategy=review_strategy
        )
    return AgentRouteResult(
        agent_id=_default_agent_for(phase),
        routing_reason=(
            f"review requested but no validator agents for phase '{phase}' — using creator"
        ),
        fallback=True,
    )


def _capability_route(registry: Any, phase: str, capability: str) -> AgentRouteResult | None:
    """Select by an explicit capability; None falls through to the create path."""
    candidates = registry.lookup_by_capability(capability)
    if not candidates:
        return None
    return _first_registered(
        candidates, f"selected by capability '{capability}' for phase '{phase}'"
    )


def route_agent(
    state: dict[str, Any],
    phase: str,
    task_type: str = "create",
    *,
    registry: Any | None = None,
    preferred_capability: str | None = None,
) -> AgentRouteResult:
    """Select an agent based on task type, phase state, and capabilities.

    ``task_type`` is one of: ``"create"``, ``"review"``, ``"repair"``,
    ``"failure_handler"``.

    When ``preferred_capability`` is provided, it overrides task-type-based
    selection.

    When ``registry`` is provided, the selection is validated against
    registered agents. When None, returns a best-effort result using
    the default phase agent.
    """
    task_type = _normalized_task_type(task_type, preferred_capability)

    if registry is not None:
        if task_type == "failure_handler":
            return _failure_handler_route(registry, phase)
        if task_type == "repair" or preferred_capability in _REPAIR_CAPABILITIES:
            return _repair_route(registry, phase)
        if task_type == "review" or preferred_capability in _REVIEW_CAPABILITIES:
            return _review_route(state, registry, phase)
        if preferred_capability:
            routed = _capability_route(registry, phase, preferred_capability)
            if routed is not None:
                return routed

    # Default: create path
    return AgentRouteResult(
        agent_id=_default_agent_for(phase),
        routing_reason=f"create path for phase '{phase}' — using default agent",
    )


def _build_kb_context_ref(agent: Any) -> str:
    """Build a KB context ref string from the agent's allowed KB domains."""
    allowed = getattr(agent, "allowed_kb_domains", [])
    if not allowed:
        return ""
    return f"kbctx:{agent.agent_id}:{'+'.join(sorted(allowed))}"


def _resolve_review_strategy(state: dict[str, Any]) -> str:
    """Resolve the review strategy from the active profile's resolved config."""
    resolved_config = state.get("resolved_config", {})
    if isinstance(resolved_config, dict):
        strategy = resolved_config.get("resolved_review_strategy", "")
        if strategy:
            return str(strategy)
    return "single"
