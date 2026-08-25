"""Agent execution: run an agent with context, persist artifacts, record handoffs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from film_pipeline.agents.impl.registry import get_agent_class
from film_pipeline.constraints import render_constraints
from film_pipeline.graph.nodes._context import (
    _AGENT_PROFILE_MAP,
    _build_dependency_map,
    _build_phase_context,
    _infer_artifact_type,
    _inject_artifact_context,
    _inject_config_context,
    _model_overrides_for,
    _parse_ref,
)
from film_pipeline.graph.nodes._shared import (
    _get_services,
)
from film_pipeline.schemas._base import ArtifactType as _ArtifactType
from film_pipeline.schemas.constraints import ProjectConstraints

if TYPE_CHECKING:
    from film_pipeline.agents.base import BaseAgent
    from film_pipeline.graph.router import AgentRouteResult
    from film_pipeline.graph.services import GraphServices
    from film_pipeline.schemas.artifact import ArtifactMetadata
    from film_pipeline.schemas.handoff import AgentRegistration
    from film_pipeline.schemas.kb import KBContextPacket


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


@dataclass(frozen=True)
class _ArtifactProvenance:
    """Provenance inputs captured once per artifact save."""

    phase: str
    built_from: dict[str, str]
    kb_context_ref: str | None
    change_summary: str


def _propagate_side_effects(
    source: dict[str, Any],
    dest: dict[str, Any],
    original: dict[str, Any] | None = None,
) -> None:
    """Copy known side-effect keys from ``source`` to ``dest``.

    ``_run_agent`` mutates ``source`` (the node's ``new_state``) via
    ``_record_handoff``, but nodes return only an ``updates`` dict.
    This helper ensures routing decisions and other side effects
    survive the node boundary.

    ``issues`` and ``validation_report_refs`` are append-only reducer
    channels: when ``original`` (the node's input state) is provided, only
    entries appended after the node's deep copy are propagated so the
    reducer never re-appends pre-existing entries.
    """
    for key in ("_routing_decisions", "_repair_feedback", "_validation_reports"):
        if key in source:
            dest[key] = source[key]
    for key in ("issues", "validation_report_refs"):
        if key not in source:
            continue
        entries = list(source.get(key, []) or [])
        if original is not None:
            prior = len(list(original.get(key, []) or []))
            entries = entries[prior:]
        if entries or original is None:
            dest[key] = entries


def _prepend_repair_feedback(task: str, state: dict[str, Any]) -> str:
    """Prefix ``task`` with repair feedback injected by repair_phase_node."""
    feedback = str(state.get("_repair_feedback", "") or "")
    if feedback:
        return f"{feedback}\n\n{task}"
    return task


def _resolve_routing(
    state: dict[str, Any],
    services: GraphServices,
    phase: str,
    task_type: str,
) -> _Routing:
    """Select the agent for this task type and resolve its contract/implementation.

    Uses dynamic routing for ``review``/``repair`` tasks; create paths fall
    back to the caller-supplied agent via the router's default.
    """
    from film_pipeline.graph.router import route_agent

    route_result = route_agent(
        state,
        phase=phase,
        task_type=task_type,
        registry=services.agent_registry,
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


def _build_template_context(state: dict[str, Any], kb: KBContextPacket) -> dict[str, str]:
    """Seed template variables with defaults plus live provider pricing."""
    context_vars: dict[str, str] = {
        "project_id": str(state.get("project_id", "")),
        "idea": str(state.get("idea", state.get("input", ""))),
        "kb_refs": kb.kb_context_id,
        "constitution_ref": "",
        "constitution_content": "",
        "treatment_ref": "",
        "treatment_content": "",
        "scene_list_ref": "",
        "scene_list_content": "",
        "script_ref": "",
        "script_content": "",
        "story_bible_ref": "",
        "story_bible_content": "",
        "shot_matrix_ref": "",
        "shot_matrix_content": "",
        "visual_refs": "",
        "visual_refs_content": "",
        "execution_brief_ref": "",
        "execution_brief_content": "",
        "validator_issues": "",
        "target_runtime_seconds": "",
        "film_type": "",
        "pacing_style": "",
        "target_scene_count": "",
        "min_scene_count": "",
        "target_shot_count": "",
        "budget_cap": "",
        "preferred_providers": "",
        "provider_pricing": "",
        "constraints": "",
    }
    from film_pipeline.providers.pricing import pricing_prompt_block

    context_vars["provider_pricing"] = pricing_prompt_block()
    return context_vars


def _populate_state_fields(context_vars: dict[str, str], state: dict[str, Any]) -> None:
    """Copy truthy upstream refs and typed targets into prompt variables."""
    # Refs first, then numeric/typed fields (incl. Story Scope Contract targets)
    for key in (
        "constitution_ref",
        "treatment_ref",
        "scene_list_ref",
        "script_ref",
        "story_bible_ref",
        "shot_matrix_ref",
        "visual_refs",
        "execution_brief_ref",
        "target_runtime_seconds",
        "film_type",
        "pacing_style",
        "target_scene_count",
        "min_scene_count",
        "target_shot_count",
    ):
        val = state.get(key)
        if val:
            context_vars[key] = str(val)


def _render_constraint_block(context_vars: dict[str, str], state: dict[str, Any]) -> None:
    """Render user-intent constraints into the prompt block."""
    raw_constraints = state.get("constraints")
    if raw_constraints and isinstance(raw_constraints, (ProjectConstraints, dict)):
        context_vars["constraints"] = render_constraints(raw_constraints)


def _maybe_add_orchestrator_context(
    context_vars: dict[str, str],
    state: dict[str, Any],
    agent_id: str,
) -> None:
    """Inject orchestrator review context when this is the orchestrator agent."""
    if agent_id == "orchestrator-agent":
        context_vars.update(_build_phase_context(state))


def _attach_scoped_packet(
    context_vars: dict[str, str],
    state: dict[str, Any],
    services: GraphServices,
    phase: str,
) -> None:
    """Attach the phase's scoped context packet (Phase 6) when a builder exists.

    Replaces loading all artifacts into every prompt. ``suppress()`` must wrap
    only ``builder()`` so a failing packet degrades to empty scoped context.
    """
    from film_pipeline.graph.context_packets import PHASE_BUILDERS

    builder = PHASE_BUILDERS.get(phase)
    if builder is not None:
        from contextlib import suppress

        with suppress(Exception):
            context_vars["scoped_context"] = builder(state, services)


def _attach_validator_issues(context_vars: dict[str, str], state: dict[str, Any]) -> None:
    """Inject accumulated validator issues for QC synthesis."""
    issues_list: list[dict[str, Any]] = state.get("issues", [])
    if issues_list:
        context_vars["validator_issues"] = json.dumps(issues_list, indent=2)


def _set_script_scene_count(context_vars: dict[str, str]) -> None:
    """Derive script scene count from loaded script content (structure extractor)."""
    try:
        script_data = json.loads(context_vars["script_content"])
        scenes = script_data.get("scenes", [])
        context_vars["script_scene_count"] = str(len(scenes))
    except (json.JSONDecodeError, KeyError, TypeError):
        context_vars["script_scene_count"] = "0"


def _augment_phase_context(
    context_vars: dict[str, str],
    state: dict[str, Any],
    services: GraphServices,
    phase: str,
    agent_id: str,
) -> None:
    """Layer constraints, orchestrator, scoped-packet, and validator context."""
    _render_constraint_block(context_vars, state)
    _maybe_add_orchestrator_context(context_vars, state, agent_id)
    _attach_scoped_packet(context_vars, state, services, phase)
    _attach_validator_issues(context_vars, state)
    if agent_id == "structure-extractor-agent" and context_vars.get("script_content"):
        _set_script_scene_count(context_vars)


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


def _capture_run_outcome(
    state: dict[str, Any],
    result: dict[str, Any],
    had_feedback: bool,
) -> dict[str, Any]:
    """Propagate handoff mutations into the result and clear consumed repair feedback."""
    routing_decisions = state.get("_routing_decisions")
    if routing_decisions:
        result["_routing_decisions"] = list(routing_decisions)
    if had_feedback:
        state["_repair_feedback"] = ""
        result["_repair_feedback"] = ""
    return result


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

    routing = _resolve_routing(state, services, phase, task_type)
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


def _is_duplicate_handoff(routes: list[dict[str, Any]], phase: str, task: str) -> bool:
    """Return True when a handoff record with the same phase+task already exists."""
    handoff_key = f"{phase}:{task}"
    for existing in routes:
        existing_key = f"{existing.get('phase', '')}:{existing.get('task', '')}"
        if existing_key == handoff_key:
            return True
    return False


def _record_handoff(
    state: dict[str, Any],
    agent_id: str,
    phase: str,
    task: str,
    route_result: Any,
    agent_output: dict[str, Any],
    *,
    template_id: str = "",
    model_profile: str = "",
) -> None:
    """Store a handoff record so routing is explainable and queryable.

    Idempotent: duplicates (same phase + task) on replay are skipped.
    Records prompt template version and resolved model profile for audit.
    """
    routes: list[dict[str, Any]] = state.setdefault("_routing_decisions", [])

    # Guard against duplicates on LangGraph checkpoint replay
    if _is_duplicate_handoff(routes, phase, task):
        return

    handoff = {
        "agent_id": agent_id,
        "phase": phase,
        "task": task,
        "routing_reason": route_result.routing_reason,
        "fallback": route_result.fallback,
        "input_refs": list(state.get("artifact_refs", [])),
        "output_keys": list(agent_output.keys()),
        "project_id": state.get("project_id", ""),
        "template_id": template_id,
        "model_profile": model_profile,
    }
    routes.append(handoff)


def _resolve_artifact_type(artifact_type: str | None, artifact: Any) -> _ArtifactType:
    """Resolve the declared artifact type; infer from the class name when omitted."""
    if artifact_type is not None:
        try:
            return _ArtifactType(artifact_type)
        except ValueError:
            return _ArtifactType.SCRIPT
    return _infer_artifact_type(artifact)


def _publish_candidate_ref(state: dict[str, Any], artifact_id: str, ref: str) -> None:
    """Record the candidate ref in orchestrator state."""
    from film_pipeline.graph.orchestrator_state import ensure_orchestrator_state, set_candidate_ref

    ensure_orchestrator_state(state)
    set_candidate_ref(state, artifact_id, ref)


def _build_artifact_metadata(
    state: dict[str, Any],
    services: GraphServices,
    artifact_id: str,
    artifact_type: _ArtifactType,
    provenance: _ArtifactProvenance,
) -> ArtifactMetadata:
    """Allocate the next version and assemble candidate metadata.

    ``next_version`` must run before metadata construction so repairs (v2, v3, …)
    never overwrite the original version.
    """
    from datetime import UTC, datetime

    from film_pipeline.schemas._base import ArtifactStatus, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata

    project_id = str(state.get("project_id", ""))
    version = services.artifact_store.next_version(project_id, provenance.phase, artifact_id)
    parents = [_parse_ref(r) for r in state.get("artifact_refs", [])]

    return ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        project_id=project_id,
        phase=FilmPhase(provenance.phase),
        version=version,
        status=ArtifactStatus.CANDIDATE,
        parents=parents,
        created_by="graph_node",
        kb_context_ref=provenance.kb_context_ref,
        created_at=datetime.now(UTC),
        built_from=provenance.built_from,
        change_summary=provenance.change_summary,
    )


def _save_artifact(
    state: dict[str, Any],
    artifact: Any,
    artifact_id: str,
    phase: str,
    artifact_type: str | None = None,
    *,
    change_summary: str = "",
    built_from: dict[str, str] | None = None,
    kb_context_ref: str | None = None,
) -> str | None:
    """Persist an artifact via ArtifactStore and return its ref string.

    Auto-increments the version so repairs (v2, v3, …) never overwrite the
    original. Populates ``built_from`` with current upstream artifact refs
    for dependency tracking.

    ``artifact_type`` is an optional ArtifactType enum value. When omitted,
    inferred from the class name via mapping.
    """
    services = _get_services(state)
    if services is None:
        return None

    atype = _resolve_artifact_type(artifact_type, artifact)
    provenance = _ArtifactProvenance(
        phase=phase,
        built_from=built_from if built_from is not None else _build_dependency_map(state),
        kb_context_ref=(
            kb_context_ref if kb_context_ref is not None else state.get("_last_kb_context_ref")
        ),
        change_summary=change_summary,
    )

    meta = _build_artifact_metadata(state, services, artifact_id, atype, provenance)
    services.artifact_store.save(artifact, meta)
    ref = f"artifact:{artifact_id}:v{meta.version}"

    _publish_candidate_ref(state, artifact_id, ref)

    return ref
