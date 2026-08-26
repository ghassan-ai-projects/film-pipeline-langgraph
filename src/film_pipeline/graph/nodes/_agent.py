"""Agent execution: route, prepare, prompt, model, execute — then record and persist.

Lifecycle orchestration lives here. Prompt-context assembly, handoff/side-channel
bookkeeping, and artifact persistence live in the ``_agent_*`` sibling modules.
The historical import surface (``_run_agent``, ``_save_artifact``,
``_record_handoff``, ``_propagate_side_effects``) is re-exported unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from film_pipeline.agents.impl.registry import get_agent_class
from film_pipeline.graph.nodes._agent_artifacts import _save_artifact
from film_pipeline.graph.nodes._agent_handoff import (
    _capture_run_outcome,
    _prepend_repair_feedback,
    _propagate_side_effects,
    _record_handoff,
)
from film_pipeline.graph.nodes._agent_prompt_context import (
    _augment_phase_context,
    _build_template_context,
    _populate_state_fields,
)
from film_pipeline.graph.nodes._context import (
    _AGENT_PROFILE_MAP,
    _inject_artifact_context,
    _inject_config_context,
    _model_overrides_for,
)
from film_pipeline.graph.nodes._shared import (
    _get_services,
)

if TYPE_CHECKING:
    from film_pipeline.agents.base import BaseAgent
    from film_pipeline.graph.router import AgentRouteResult
    from film_pipeline.graph.services import GraphServices
    from film_pipeline.schemas.handoff import AgentRegistration
    from film_pipeline.schemas.kb import KBContextPacket

__all__ = [
    "_propagate_side_effects",
    "_record_handoff",
    "_run_agent",
    "_save_artifact",
]


@dataclass(frozen=True)
class _Routing:
    """Routing decision for one agent run."""

    route_result: AgentRouteResult
    agent_id: str
    impl: type[BaseAgent] | None
    contract: AgentRegistration | None


@dataclass(frozen=True)
class _ModelOutcome:
    """Model stage results consumed by execution and handoff recording."""

    model_output: dict[str, Any]
    template_id: str
    profile: str


def _resolve_routing(
    state: dict[str, Any],
    services: GraphServices,
    phase: str,
    task_type: str,
    agent_id: str,
) -> _Routing:
    """Select the agent for this task type and resolve its contract/implementation.

    Uses dynamic routing for ``review``/``repair`` tasks; create paths honor
    the caller-supplied ``agent_id`` when it is registered (several phases run
    more than one creator), falling back to the phase default otherwise.
    """
    from film_pipeline.graph.router import route_agent

    route_result = route_agent(
        state,
        phase=phase,
        task_type=task_type,
        registry=services.agent_registry,
        preferred_agent_id=agent_id if task_type == "create" else None,
    )
    resolved_agent_id = route_result.agent_id

    registry = services.agent_registry
    contract = registry.lookup_by_id(resolved_agent_id) if registry else None
    return _Routing(
        route_result=route_result,
        agent_id=resolved_agent_id,
        impl=get_agent_class(resolved_agent_id),
        contract=contract,
    )


def _open_kb_session(
    state: dict[str, Any],
    services: GraphServices,
    agent_id: str,
    phase: str,
    task: str,
) -> KBContextPacket:
    """Open the run's KB packet; its id is captured for downstream artifact saves."""
    kb = services.kb_for(
        project_id=str(state.get("project_id", "")),
        phase=phase,
        agent_id=agent_id,
        task=task,
    )
    # Capture the KB context id so saved artifacts can reference it.
    state["_last_kb_context_ref"] = kb.kb_context_id
    return kb


def _generate_model_output(
    state: dict[str, Any],
    services: GraphServices,
    kb: KBContextPacket,
    routing: _Routing,
    task: str,
    phase: str,
) -> _ModelOutcome:
    """Build prompt context and produce model output for the routed agent.

    Critical-path agents (those in agent_map) require dedicated prompt templates;
    non-critical agents fall through to generic RCTCO assembly.
    """
    agent_id = routing.agent_id
    contract = cast("AgentRegistration", routing.contract)

    if routing.impl is not None:
        from film_pipeline.agents.prompt_templates.registry import get_registry

        prompt_registry = get_registry()
        template = prompt_registry.get_required(agent_id)

        context_vars = _build_template_context(state, kb)
        _populate_state_fields(context_vars, state)
        _inject_artifact_context(state, services, context_vars)
        _inject_config_context(state, context_vars)
        _augment_phase_context(context_vars, state, services, phase, agent_id)

        resolved_profile = _AGENT_PROFILE_MAP.get(agent_id, "operations_triage")
        model_overrides = _model_overrides_for(state, resolved_profile)
        model_output, template_id, _ = services.prompt_runner.run_from_template(
            template,
            kb,
            task,
            context_vars=context_vars,
            model_profile=resolved_profile,
            agent_id=agent_id,
            model_overrides=model_overrides,
        )
        return _ModelOutcome(
            model_output=model_output,
            template_id=template_id,
            profile=resolved_profile,
        )

    model_output = services.prompt_runner.run(contract, kb, task)
    return _ModelOutcome(model_output=model_output, template_id="", profile="")


def _execute_agent(
    routing: _Routing,
    kb: KBContextPacket,
    task: str,
    model_output: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """Instantiate the routed agent implementation and run it against the task."""
    impl = cast("type[BaseAgent]", routing.impl)
    contract = cast("AgentRegistration", routing.contract)
    instance: BaseAgent = impl(contract)
    return instance.run(state, kb, task, model_output)


def _run_agent(
    state: dict[str, Any],
    agent_id: str,
    phase: str,
    task: str,
    *,
    task_type: str = "create",
) -> dict[str, Any]:
    """Run an agent through the full lifecycle: route → prepare → prompt → model → execute.

    Uses ``route_agent()`` for dynamic agent selection when ``task_type`` is
    ``"review"`` or ``"repair"``, falling back to the explicitly passed
    ``agent_id`` for create paths.

    Returns the agent's result dict, or a fallback if services aren't available.
    """
    had_feedback = bool(state.get("_repair_feedback"))
    task = _prepend_repair_feedback(task, state)

    services = _get_services(state)
    if services is None:
        return {"status": "no_services", "agent": agent_id}

    routing = _resolve_routing(state, services, phase, task_type, agent_id)
    if routing.contract is None:
        return {"status": "agent_not_found", "agent": routing.agent_id}

    kb = _open_kb_session(state, services, routing.agent_id, phase, task)

    outcome = _generate_model_output(state, services, kb, routing, task, phase)

    if routing.impl is None:
        return {
            "status": "no_impl",
            "agent": routing.agent_id,
            "model_output": outcome.model_output,
        }

    result = _execute_agent(routing, kb, task, outcome.model_output, state)

    _record_handoff(
        state,
        routing.agent_id,
        phase,
        task,
        routing.route_result,
        result,
        template_id=outcome.template_id,
        model_profile=outcome.profile,
    )

    return _capture_run_outcome(state, result, had_feedback)
