"""Agent execution: run an agent with context, persist artifacts, record handoffs."""

from __future__ import annotations

import json
from typing import Any

from film_pipeline.agents.base import BaseAgent
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
    # Inject repair feedback into the task if present (set by repair_phase_node)
    feedback = str(state.get("_repair_feedback", "") or "")
    if feedback:
        task = f"{feedback}\n\n{task}"

    services = _get_services(state)
    if services is None:
        return {"status": "no_services", "agent": agent_id}

    # Dynamic routing: select agent based on task type
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
    if contract is None:
        return {"status": "agent_not_found", "agent": resolved_agent_id}

    kb = services.kb_for(
        project_id=str(state.get("project_id", "")),
        phase=phase,
        agent_id=resolved_agent_id,
        task=task,
    )
    # Capture the KB context id so saved artifacts can reference it.
    state["_last_kb_context_ref"] = kb.kb_context_id

    # Build prompt, call model, execute agent
    # Critical-path agents (those in agent_map) require dedicated prompt templates.
    # Non-critical agents fall through to generic RCTCO assembly.

    agent_cls = get_agent_class(resolved_agent_id)

    template_id = ""

    if agent_cls is not None:
        # Critical-path agent: dedicated template required
        from film_pipeline.agents.prompt_templates.registry import get_registry

        prompt_registry = get_registry()
        template = prompt_registry.get_required(resolved_agent_id)

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
        for key in (
            "constitution_ref",
            "treatment_ref",
            "scene_list_ref",
            "script_ref",
            "story_bible_ref",
            "shot_matrix_ref",
            "visual_refs",
            "execution_brief_ref",
        ):
            val = state.get(key)
            if val:
                context_vars[key] = str(val)
        # Populate numeric/typed state fields (incl. Story Scope Contract targets)
        for key in (
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
        _inject_artifact_context(state, services, context_vars)
        _inject_config_context(state, context_vars)

        # Render user-intent constraints into the prompt block.
        raw_constraints = state.get("constraints")
        if raw_constraints and isinstance(raw_constraints, (ProjectConstraints, dict)):
            context_vars["constraints"] = render_constraints(raw_constraints)

        # Inject orchestrator review context when this is the orchestrator agent
        if resolved_agent_id == "orchestrator-agent":
            phase_ctx = _build_phase_context(state)
            context_vars.update(phase_ctx)

        # Build scoped context packet for this phase (Phase 6 — replaces
        # loading all artifacts when the phase has a dedicated builder)
        from film_pipeline.graph.context_packets import PHASE_BUILDERS

        builder = PHASE_BUILDERS.get(phase)
        if builder is not None:
            from contextlib import suppress

            with suppress(Exception):
                context_vars["scoped_context"] = builder(state, services)

        # Inject validator issues for QC synthesis
        issues_list: list[dict[str, Any]] = state.get("issues", [])
        if issues_list:
            context_vars["validator_issues"] = json.dumps(issues_list, indent=2)

        # Compute script scene count from loaded script content (for structure extractor)
        if resolved_agent_id == "structure-extractor-agent" and context_vars.get("script_content"):
            try:
                script_data = json.loads(context_vars["script_content"])
                scenes = script_data.get("scenes", [])
                context_vars["script_scene_count"] = str(len(scenes))
            except (json.JSONDecodeError, KeyError, TypeError):
                context_vars["script_scene_count"] = "0"

        resolved_profile = _AGENT_PROFILE_MAP.get(resolved_agent_id, "operations_triage")
        model_overrides = _model_overrides_for(state, resolved_profile)
        model_output, template_id, _ = services.prompt_runner.run_from_template(
            template,
            kb,
            task,
            context_vars=context_vars,
            model_profile=resolved_profile,
            agent_id=resolved_agent_id,
            model_overrides=model_overrides,
        )
    else:
        # Non-critical agent: generic RCTCO assembly (not in critical path)
        model_output = services.prompt_runner.run(contract, kb, task)

    if agent_cls is None:
        return {"status": "no_impl", "agent": resolved_agent_id, "model_output": model_output}

    instance: BaseAgent = agent_cls(contract)
    result = instance.run(state, kb, task, model_output)

    # Persist routing decision as a handoff record
    _record_handoff(
        state,
        resolved_agent_id,
        phase,
        task,
        route_result,
        result,
        template_id=template_id,
        model_profile=resolved_profile,
    )

    # Propagate side-effect state mutations so callers can merge them
    routing = state.get("_routing_decisions")
    if routing:
        result["_routing_decisions"] = list(routing)
    if feedback:
        state["_repair_feedback"] = ""
        result["_repair_feedback"] = ""

    return result


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
    handoff_key = f"{phase}:{task}"
    for existing in routes:
        existing_key = f"{existing.get('phase', '')}:{existing.get('task', '')}"
        if existing_key == handoff_key:
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
    from datetime import UTC, datetime

    from film_pipeline.schemas._base import ArtifactStatus, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata

    if artifact_type is not None:
        try:
            atype = _ArtifactType(artifact_type)
        except ValueError:
            atype = _ArtifactType.SCRIPT
    else:
        atype = _infer_artifact_type(artifact)

    project_id = str(state.get("project_id", ""))
    version = services.artifact_store.next_version(project_id, phase, artifact_id)

    parent_refs = state.get("artifact_refs", [])
    parents = [_parse_ref(r) for r in parent_refs]

    if built_from is None:
        built_from = _build_dependency_map(state)

    if kb_context_ref is None:
        kb_context_ref = state.get("_last_kb_context_ref")

    meta = ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=atype,
        project_id=project_id,
        phase=FilmPhase(phase),
        version=version,
        status=ArtifactStatus.CANDIDATE,
        parents=parents,
        created_by="graph_node",
        kb_context_ref=kb_context_ref,
        created_at=datetime.now(UTC),
        built_from=built_from,
        change_summary=change_summary,
    )
    services.artifact_store.save(artifact, meta)
    ref = f"artifact:{artifact_id}:v{version}"

    # Record candidate ref for orchestrator state
    from film_pipeline.graph.orchestrator_state import ensure_orchestrator_state, set_candidate_ref

    ensure_orchestrator_state(state)
    set_candidate_ref(state, artifact_id, ref)

    return ref
