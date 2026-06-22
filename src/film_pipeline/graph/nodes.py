"""Graph node definitions — one per phase.

Spine phases (intake, constitution, development, script) invoke real agents
and persist artifacts. Remaining phases are flag-only pending fan-out.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, cast

from film_pipeline.graph.services import SERVICES_KEY, GraphServices
from film_pipeline.schemas._base import ArtifactType as _ArtifactType
from film_pipeline.schemas.artifact import ArtifactRef as _ArtifactRef


def _get_services(state: dict[str, Any]) -> GraphServices | None:
    return state.get(SERVICES_KEY)


def _get_template_registry() -> Any:
    """Return the session-scoped prompt template registry."""
    from film_pipeline.agents.prompt_templates.registry import get_registry

    return get_registry()


_AGENT_PROFILE_MAP: dict[str, str] = {
    # Creative agents → creative profiles (temperature 0.7, 8192 tokens)
    "film-constitution-agent": "creative_writer",
    "treatment-agent": "creative_writer",
    "screenwriter-agent": "creative_writer",
    "shot-design-agent": "creative_writer",
    "reference-strategy-planner": "visual_reasoner",
    "visual-dev-agent": "visual_reasoner",
    "character-dossier-agent": "creative_writer",
    "environment-bible-agent": "creative_writer",
    "prompt-composition-agent": "creative_writer",
    # Analytical/structural agents → strict profiles
    "structure-extractor-agent": "strict_validator",
    "clip-validator": "strict_validator",
    "scene-continuity-validator": "strict_validator",
    "full-movie-flow-validator": "strict_validator",
    # Operational agents → operational profiles
    "intake-classifier-agent": "operations_triage",
    "config-inference-agent": "operations_triage",
    "provider-planning-agent": "operations_triage",
    "generation-scheduler-agent": "operations_triage",
    "continuity-ledger-agent": "operations_triage",
    "failure-handling-agent": "operations_triage",
    "orchestrator-agent": "operations_triage",
    "kb-curator-agent": "operations_triage",
}


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
    feedback = state.pop("_repair_feedback", "")
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

    # Build prompt, call model, execute agent
    # Critical-path agents (those in agent_map) require dedicated prompt templates.
    # Non-critical agents fall through to generic RCTCO assembly.

    from film_pipeline.agents.base import BaseAgent
    from film_pipeline.agents.impl.assembly_agent import AssemblyAgent
    from film_pipeline.agents.impl.constitution_agent import ConstitutionAgent
    from film_pipeline.agents.impl.development_agent import DevelopmentAgent
    from film_pipeline.agents.impl.gen_planner_agent import GenPlannerAgent
    from film_pipeline.agents.impl.intake_agent import IntakeAgent
    from film_pipeline.agents.impl.qc_synthesis_agent import QCSynthesisAgent
    from film_pipeline.agents.impl.screenwriter_agent import ScreenwriterAgent
    from film_pipeline.agents.impl.shot_bible_agent import ShotBibleAgent
    from film_pipeline.agents.impl.structure_extractor_agent import StructureExtractorAgent
    from film_pipeline.agents.impl.visual_dev_agent import VisualDevAgent

    agent_map: dict[str, type[BaseAgent]] = {
        "intake-classifier-agent": IntakeAgent,
        "film-constitution-agent": ConstitutionAgent,
        "treatment-agent": DevelopmentAgent,
        "screenwriter-agent": ScreenwriterAgent,
        "structure-extractor-agent": StructureExtractorAgent,
        "shot-design-agent": ShotBibleAgent,
        "reference-strategy-planner": VisualDevAgent,
        "visual-dev-agent": VisualDevAgent,
        "provider-planning-agent": GenPlannerAgent,
        "clip-validator": QCSynthesisAgent,
        "failure-handling-agent": AssemblyAgent,
    }
    agent_cls = agent_map.get(resolved_agent_id)

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
            "budget_cap": "",
            "preferred_providers": "",
        }
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
        # Populate numeric/typed state fields
        for key in ("target_runtime_seconds", "film_type"):
            val = state.get(key)
            if val:
                context_vars[key] = str(val)
        _inject_artifact_context(state, services, context_vars)
        _inject_config_context(state, context_vars)

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
        model_output, template_id, _ = services.prompt_runner.run_from_template(
            template,
            kb,
            task,
            context_vars=context_vars,
            model_profile=resolved_profile,
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

    meta = ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=atype,
        project_id=project_id,
        phase=FilmPhase(phase),
        version=version,
        status=ArtifactStatus.CANDIDATE,
        parents=parents,
        created_by="graph_node",
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


def _build_dependency_map(state: dict[str, Any]) -> dict[str, str]:
    """Build built_from map from current state artifact refs."""
    ref_keys = [
        "profile_ref",
        "constitution_ref",
        "treatment_ref",
        "scene_list_ref",
        "script_ref",
        "story_bible_ref",
        "shot_matrix_ref",
        "visual_refs",
        "execution_brief_ref",
        "cost_estimate_ref",
    ]
    built_from: dict[str, str] = {}
    for key in ref_keys:
        ref = state.get(key)
        if ref and isinstance(ref, str) and ":" in ref:
            parts = ref.split(":")
            if len(parts) >= 3:
                built_from[parts[1]] = ref
    return built_from


_ARTIFACT_TYPE_BY_CLASS: dict[str, str] = {
    "ProjectProfile": "project_config",
    "FilmConstitution": "film_constitution",
    "Treatment": "treatment",
    "SceneList": "scene_list",
    "StoryBible": "script",
    "Script": "script",
    "MasterFilmMatrix": "shot_bible",
    "CostEstimate": "cost_estimate_bom",
    "ConsensusReport": "consensus_report",
    "AssemblyManifest": "assembly_manifest",
}


def _infer_artifact_type(artifact: Any) -> _ArtifactType:
    """Infer ArtifactType from the object's class name."""
    class_name = type(artifact).__name__
    mapped = _ARTIFACT_TYPE_BY_CLASS.get(class_name, "script")
    try:
        return _ArtifactType(mapped)
    except ValueError:
        return _ArtifactType.SCRIPT


def _parse_ref(ref_str: str) -> _ArtifactRef:
    """Parse an artifact ref string like 'artifact:id:v1' into an ArtifactRef."""
    parts = ref_str.split(":")
    artifact_id = parts[1] if len(parts) > 1 else ref_str
    version_str = parts[2] if len(parts) > 2 else "1"
    version = int(version_str.lstrip("v"))
    return _ArtifactRef(artifact_id=artifact_id, version=version)


def _inject_artifact_context(
    state: dict[str, Any],
    services: GraphServices,
    context_vars: dict[str, str],
) -> None:
    """Load upstream artifact content into prompt context to preserve continuity."""
    project_id = str(state.get("project_id", ""))
    if not project_id:
        return

    from film_pipeline.schemas._base import FilmPhase

    artifact_map = {
        "constitution_ref": ("constitution", "constitution_content"),
        "treatment_ref": ("development", "treatment_content"),
        "scene_list_ref": ("development", "scene_list_content"),
        "story_bible_ref": ("script", "story_bible_content"),
        "script_ref": ("script", "script_content"),
        "shot_matrix_ref": ("shot_bible", "shot_matrix_content"),
        "visual_refs": ("visual_dev", "visual_refs_content"),
        "execution_brief_ref": ("shot_bible", "execution_brief_content"),
    }
    for ref_key, (phase_name, content_key) in artifact_map.items():
        ref = str(state.get(ref_key, "") or "").strip()
        if not ref:
            continue
        try:
            parsed = _parse_ref(ref)
            data = services.artifact_store.load(
                project_id,
                FilmPhase(phase_name),
                parsed.artifact_id,
                parsed.version,
            )
            context_vars[content_key] = _compact_json_context(data)
        except (FileNotFoundError, ValueError, KeyError):
            continue


def _inject_config_context(state: dict[str, Any], context_vars: dict[str, str]) -> None:
    """Expose resolved config details that matter for planning prompts."""
    resolved_config = state.get("resolved_config", {})
    if not isinstance(resolved_config, dict):
        return
    budget = resolved_config.get("budget", {})
    providers = resolved_config.get("providers", {})
    if isinstance(budget, dict):
        for key in ("project_cap_usd", "max_total_usd"):
            value = budget.get(key)
            if value is not None:
                context_vars["budget_cap"] = str(value)
                break
    preferred: list[str] = []
    if isinstance(providers, dict):
        order = providers.get("order", [])
        if isinstance(order, list):
            preferred = [str(item) for item in order if str(item)]
        elif isinstance(providers.get("video"), list):
            preferred = [
                str(entry.get("provider_id", ""))
                for entry in providers["video"]
                if isinstance(entry, dict) and str(entry.get("provider_id", ""))
            ]
    if preferred:
        context_vars["preferred_providers"] = ", ".join(preferred)


def _compact_json_context(data: dict[str, Any], max_chars: int = 6000) -> str:
    """Serialize artifact content for prompt context without exploding token count."""
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n... [truncated]"


# ── Intake ───────────────────────────────────────────────────────────────────


def intake_node(state: dict[str, Any]) -> dict[str, Any]:
    """Intake: classify input, infer config, present for approval."""
    new_state = deepcopy(state)
    updates: dict[str, Any] = {
        "current_phase": "intake",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "config",
    }
    new_refs: list[str] = []

    result = _run_agent(
        new_state,
        agent_id="intake-classifier-agent",
        phase="intake",
        task=(
            "Classify the user's film idea: determine genre, tone, audience, "
            "realistic runtime estimate, aspect ratio, and delivery format. "
            "Identify risks and produce a structured project profile."
        ),
    )
    profile = result.get("profile")
    if profile is not None:
        ref = _save_artifact(new_state, profile, "project_profile", "intake")
        if ref:
            updates["profile_ref"] = ref
            new_refs.append(ref)
        if hasattr(profile, "target_runtime_seconds"):
            updates["target_runtime_seconds"] = profile.target_runtime_seconds
        if hasattr(profile, "film_type"):
            updates["film_type"] = str(profile.film_type)

    if new_refs:
        updates["artifact_refs"] = new_refs
    return updates


# ── Constitution ─────────────────────────────────────────────────────────────


def constitution_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    updates: dict[str, Any] = {
        "current_phase": "constitution",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "constitution",
    }
    new_refs: list[str] = []

    result = _run_agent(
        new_state,
        agent_id="film-constitution-agent",
        phase="constitution",
        task=(
            "Define the film's creative constitution: theme, tone, emotional "
            "promise, visual language, camera philosophy, character truths, "
            "and quality standards. This governs every downstream decision."
        ),
    )
    constitution = result.get("constitution")
    if constitution is not None:
        ref = _save_artifact(new_state, constitution, "film_constitution", "constitution")
        if ref:
            updates["constitution_ref"] = ref
            new_refs.append(ref)

    if new_refs:
        updates["artifact_refs"] = new_refs
    return updates


# ── Development ──────────────────────────────────────────────────────────────


def development_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    updates: dict[str, Any] = {
        "current_phase": "development",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "treatment",
    }
    new_refs: list[str] = []

    result = _run_agent(
        new_state,
        agent_id="treatment-agent",
        phase="development",
        task=(
            "Develop the film treatment: write treatment prose, identify "
            "themes, map the three-act structure, and break down every scene "
            "with dramatic function, emotional shift, conflict, and outcome."
        ),
    )
    treatment = result.get("treatment")
    scene_list = result.get("scene_list")
    if treatment is not None:
        ref = _save_artifact(new_state, treatment, "treatment", "development")
        if ref:
            updates["treatment_ref"] = ref
            new_refs.append(ref)
    if scene_list is not None:
        ref = _save_artifact(new_state, scene_list, "scene_list", "development")
        if ref:
            updates["scene_list_ref"] = ref
            new_refs.append(ref)

    if new_refs:
        updates["artifact_refs"] = new_refs
    return updates


# ── Script ───────────────────────────────────────────────────────────────────


def script_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    updates: dict[str, Any] = {
        "current_phase": "script",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "script",
    }
    new_refs: list[str] = []

    result = _run_agent(
        new_state,
        agent_id="screenwriter-agent",
        phase="script",
        task=(
            "Write the complete screenplay: logline, premise, story bible "
            "with scene-by-scene breakdown, dialogue, action lines, and "
            "setup-payoff mapping across all three acts."
        ),
    )
    story_bible = result.get("story_bible")
    script = result.get("script")
    if story_bible is not None:
        ref = _save_artifact(new_state, story_bible, "story_bible", "script")
        if ref:
            updates["story_bible_ref"] = ref
            new_refs.append(ref)
    if script is not None:
        ref = _save_artifact(new_state, script, "script", "script")
        if ref:
            updates["script_ref"] = ref
            new_refs.append(ref)

    if new_refs:
        updates["artifact_refs"] = new_refs
    return updates


# ── Remaining phases (flag-only, pending agent implementations) ──────────────


def visual_dev_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    updates: dict[str, Any] = {
        "current_phase": "visual_dev",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "visual_bible",
    }
    new_refs: list[str] = []

    result = _run_agent(
        new_state,
        agent_id="reference-strategy-planner",
        phase="visual_dev",
        task=(
            "Design the visual look: color palette, lighting approach, "
            "camera style, and shot-by-shot reference entries with provider "
            "tiers (fast/standard/ultra) for character, environment, and "
            "prop sheets."
        ),
    )
    index = result.get("reference_index")
    if index is not None:
        ref = _save_artifact(new_state, index, "reference_index", "visual_dev")
        if ref:
            updates["visual_refs"] = ref
            new_refs.append(ref)

    if new_refs:
        updates["artifact_refs"] = new_refs
    return updates


def shot_bible_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state  # keep reference for diff computation
    new_state["current_phase"] = "shot_bible"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "shot_bible"

    # ── Pre-step: extract structural metadata if not already present ──────
    from film_pipeline.graph.orchestrator_state import has_execution_brief, set_execution_brief
    from film_pipeline.graph.orchestrator_validators import load_execution_brief

    if not has_execution_brief(new_state) and load_execution_brief(new_state) is None:
        extract_result = _run_agent(
            new_state,
            agent_id="structure-extractor-agent",
            phase="shot_bible",
            task=(
                "Extract the structural metadata from the story: runtime, "
                "movement/act breakdown, shot counts, mandatory anchors, "
                "environment progression, and pacing style."
            ),
        )
        brief = extract_result.get("execution_brief")
        if brief is not None:
            set_execution_brief(new_state, brief)
            brief_ref = _save_artifact(new_state, brief, "execution_brief", "shot_bible")
            if brief_ref:
                new_state["execution_brief_ref"] = brief_ref

            # Cross-validate the extracted brief against the StoryBible
            from film_pipeline.graph.orchestrator_validators import validate_execution_brief

            brief_issues = validate_execution_brief(new_state, brief)
            new_state.setdefault("issues", []).extend(brief_issues)

    # ── Run the shot design agent ────────────────────────────────────────
    result = _run_agent(
        new_state,
        agent_id="shot-design-agent",
        phase="shot_bible",
        task=(
            "Produce the master film matrix: decompose every scene into "
            "individual shots with camera, duration, characters, environment, "
            "and prompt_ref. Match the exact shot count and runtime from "
            "the Execution Brief."
        ),
    )
    shot_matrix = result.get("shot_matrix")
    if shot_matrix is not None:
        ref = _save_artifact(new_state, shot_matrix, "shot_matrix", "shot_bible")
        if ref:
            new_state["shot_matrix_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    # ── Gate A: validate shot structure against execution brief ──────────
    if shot_matrix is not None:
        brief = load_execution_brief(new_state)
        if brief is not None:
            from film_pipeline.graph.orchestrator_validators import validate_shot_structure

            struct_issues = validate_shot_structure(new_state, brief, shot_matrix)
            new_state.setdefault("issues", []).extend(struct_issues)

    # Compute partial update from before/after diff
    updates: dict[str, Any] = {
        "current_phase": "shot_bible",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "shot_bible",
    }
    new_refs = [r for r in (new_state.get("artifact_refs", []) or []) if _is_new_ref(r, original)]
    if new_refs:
        updates["artifact_refs"] = new_refs
    new_issues = [i for i in (new_state.get("issues", []) or []) if _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    for key in ("shot_matrix_ref", "execution_brief_ref"):
        val = new_state.get(key)
        if val:
            updates[key] = val
    return updates


def gen_planning_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state
    new_state["current_phase"] = "gen_planning"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "generation_spend"

    result = _run_agent(
        new_state,
        agent_id="provider-planning-agent",
        phase="gen_planning",
        task=(
            "Plan generation for every shot: select providers and models, "
            "estimate cost per shot and total, order by dependency. "
            "Every row in the shot matrix must have a plan entry with "
            "real (non-zero) cost estimates."
        ),
    )
    cost_estimate = result.get("cost_estimate")
    if cost_estimate is not None:
        ref = _save_artifact(new_state, cost_estimate, "cost_estimate", "gen_planning")
        if ref:
            new_state["cost_estimate_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)
    gen_requests = result.get("generation_requests")
    if gen_requests:
        new_state["generation_requests"] = gen_requests

    # ── Gate B: validate planning completeness ───────────────────────────
    shot_matrix_ref = str(new_state.get("shot_matrix_ref", ""))
    if shot_matrix_ref:
        services = _get_services(new_state)
        if services is not None:
            try:
                from film_pipeline.schemas._base import FilmPhase

                parsed = _parse_ref(shot_matrix_ref)
                matrix_data = services.artifact_store.load(
                    str(new_state.get("project_id", "")),
                    FilmPhase("shot_bible"),
                    parsed.artifact_id,
                    parsed.version,
                )
                from film_pipeline.graph.orchestrator_validators import (
                    validate_planning_completeness,
                )

                plan_issues = validate_planning_completeness(new_state, matrix_data, cost_estimate)
                new_state.setdefault("issues", []).extend(plan_issues)
            except (FileNotFoundError, ValueError, KeyError):
                pass

    # Compute partial update from before/after diff
    updates: dict[str, Any] = {
        "current_phase": "gen_planning",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "generation_spend",
    }
    new_refs = [r for r in (new_state.get("artifact_refs", []) or []) if _is_new_ref(r, original)]
    if new_refs:
        updates["artifact_refs"] = new_refs
    new_issues = [i for i in (new_state.get("issues", []) or []) if _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    for key in ("cost_estimate_ref",):
        val = new_state.get(key)
        if val:
            updates[key] = val
    return updates


def generation_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state
    new_state["current_phase"] = "generation"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "generation_batch"

    # ── Gate C: validate dispatch readiness ──────────────────────────────
    gen_requests = new_state.get("generation_requests")
    if gen_requests is not None:
        from film_pipeline.graph.orchestrator_validators import validate_dispatch_readiness

        dispatch_issues = validate_dispatch_readiness(new_state, gen_requests)
        new_state.setdefault("issues", []).extend(dispatch_issues)

    # Compute partial update from before/after diff
    updates: dict[str, Any] = {
        "current_phase": "generation",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "generation_batch",
    }
    new_issues = [i for i in (new_state.get("issues", []) or []) if _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    return updates


def qc_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state
    new_state["current_phase"] = "qc"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "qc"

    # Run validators against upstream artifacts FIRST
    _run_validators(new_state)

    # Then synthesize their findings into a unified QC report
    result = _run_agent(
        new_state,
        agent_id="clip-validator",
        phase="qc",
        task=(
            "Synthesize all validator reports into a unified QC consensus: "
            "identify agreement areas, resolve conflicts, produce weighted "
            "pass/fail/block recommendation with actionable feedback."
        ),
    )
    report = result.get("consensus_report")
    if report is not None:
        ref = _save_artifact(new_state, report, "consensus_report", "qc")
        if ref:
            new_state["consensus_report_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    # Compute partial update from before/after diff
    updates: dict[str, Any] = {
        "current_phase": "qc",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "qc",
    }
    new_refs = [r for r in (new_state.get("artifact_refs", []) or []) if _is_new_ref(r, original)]
    if new_refs:
        updates["artifact_refs"] = new_refs
    new_issues = [i for i in (new_state.get("issues", []) or []) if _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    for key in ("consensus_report_ref",):
        val = new_state.get(key)
        if val:
            updates[key] = val
    return updates


def _run_validators(state: dict[str, Any]) -> None:
    """Run validators against current-phase artifacts.

    Blocking findings are added to ``state["issues"]``, which prevents
    phase advancement via ``compute_actions()``.

    For the ``qc`` phase, validators inspect artifacts from all upstream
    phases (script, visual_dev, etc.) so that the QC node produces a
    comprehensive validation report.
    """
    services = _get_services(state)
    if services is None:
        return

    from film_pipeline.schemas._base import FilmPhase

    store = services.artifact_store
    phase = str(state.get("current_phase", ""))
    project_id = str(state.get("project_id", ""))

    # Determine which phases to scan for artifacts.
    if phase == "qc":
        load_phases: list[FilmPhase] = [
            FilmPhase("intake"),
            FilmPhase("constitution"),
            FilmPhase("development"),
            FilmPhase("script"),
            FilmPhase("visual_dev"),
            FilmPhase("shot_bible"),
            FilmPhase("gen_planning"),
        ]
    else:
        load_phases = [FilmPhase(phase)]

    # Collect artifacts by trying each upstream phase.
    artifact_data: dict[str, Any] = {}
    artifact_refs = state.get("artifact_refs", [])
    for ref_str in artifact_refs:
        ref_str = str(ref_str)
        if ":" not in ref_str:
            continue
        parts = ref_str.split(":")
        artifact_id = parts[1] if len(parts) > 1 else ref_str
        version_str = parts[2] if len(parts) > 2 else "1"
        version = int(version_str.lstrip("v"))
        for fp in load_phases:
            try:
                artifact_data[artifact_id] = store.load(project_id, fp, artifact_id, version)
                break
            except (FileNotFoundError, ValueError):
                continue

    issues: list[dict[str, Any]] = list(state.get("issues", []))

    # --- Phase-specific validator dispatch ---

    if phase in ("script", "qc") and artifact_data:
        _run_script_validators(artifact_data, issues, state, services)

    if phase in ("visual_dev", "qc") and artifact_data:
        _run_reference_validators(artifact_data, issues, state, services)

    if phase in ("gen_planning", "qc") and artifact_data:
        _run_prompt_validators(artifact_data, issues, state, services)

    if phase in ("shot_bible", "qc") and artifact_data:
        _run_continuity_validators(artifact_data, issues, state, services)

    if phase in ("post", "assembly", "qc") and artifact_data:
        _run_assembly_validators(artifact_data, issues, state, services)

    if phase == "delivery" and artifact_data:
        _run_delivery_validators(artifact_data, issues, state, services)

    state["issues"] = issues

    # --- Build consensus report when multiple validators ran ----------
    _build_consensus_if_needed(state, phase)


def _build_consensus_if_needed(state: dict[str, Any], phase: str) -> None:
    """Build a consensus report when multiple validators produced reports."""
    reports = state.get("_validation_reports", [])
    if len(reports) < 2:
        return

    from film_pipeline.validation.consensus import ConsensusBuilder

    artifact_refs: list[str] = state.get("artifact_refs", [])

    try:
        consensus = ConsensusBuilder().build(reports, artifact_refs)
    except Exception:
        return

    # Save consensus report as an artifact
    ref = _save_artifact(state, consensus, "consensus_report", phase)
    if ref:
        state["consensus_report_ref"] = ref
        state.setdefault("artifact_refs", []).append(ref)


def _run_script_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run the two script-phase validators against loaded artifacts."""
    from film_pipeline.validation.impl.dialogue_voice import DialogueVoiceValidator
    from film_pipeline.validation.impl.script_structure import ScriptStructureValidator

    raw: Any = next(iter(artifact_data.values()), {})
    artifact: dict[str, Any] = raw if isinstance(raw, dict) else {}
    for vcls in (ScriptStructureValidator, DialogueVoiceValidator):
        try:
            instance = vcls()
            instance.set_services(
                adapter=services.model_adapter,
                router=services.model_router,
                template_registry=_get_template_registry(),
            )
            report = instance.run(artifact)
        except Exception:
            continue
        _append_validator_report(report, issues, state)


def _run_reference_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run reference usability validator against visual_dev artifacts."""
    from film_pipeline.validation.impl.reference_usability import ReferenceUsabilityValidator

    raw: Any = next(iter(artifact_data.values()), {})
    artifact: dict[str, Any] = raw if isinstance(raw, dict) else {}
    try:
        instance = ReferenceUsabilityValidator()
        instance.set_services(
            adapter=services.model_adapter,
            router=services.model_router,
        )
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _run_prompt_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run prompt readiness validator against gen_planning artifacts."""
    from film_pipeline.validation.impl.prompt_readiness import PromptReadinessValidator

    raw: Any = next(iter(artifact_data.values()), {})
    artifact: dict[str, Any] = raw if isinstance(raw, dict) else {}
    try:
        instance = PromptReadinessValidator()
        instance.set_services(
            adapter=services.model_adapter,
            router=services.model_router,
        )
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _run_continuity_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run scene continuity validator against shot_bible artifacts."""
    from film_pipeline.validation.impl.scene_continuity import SceneContinuityValidator

    raw: Any = next(iter(artifact_data.values()), {})
    artifact: dict[str, Any] = raw if isinstance(raw, dict) else {}
    try:
        instance = SceneContinuityValidator()
        instance.set_services(
            adapter=services.model_adapter,
            router=services.model_router,
        )
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _run_assembly_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run assembly validator against post/assembly artifacts."""
    from film_pipeline.validation.impl.assembly import AssemblyValidator

    raw: Any = next(iter(artifact_data.values()), {})
    artifact: dict[str, Any] = raw if isinstance(raw, dict) else {}
    try:
        instance = AssemblyValidator()
        instance.set_services(
            adapter=services.model_adapter,
            router=services.model_router,
        )
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _run_delivery_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run delivery completeness validator against delivery artifacts."""
    from film_pipeline.validation.impl.delivery_completeness import (
        DeliveryCompletenessValidator,
    )

    raw: Any = next(iter(artifact_data.values()), {})
    artifact: dict[str, Any] = raw if isinstance(raw, dict) else {}
    try:
        instance = DeliveryCompletenessValidator()
        instance.set_services(
            adapter=services.model_adapter,
            router=services.model_router,
        )
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _append_validator_report(
    report: Any,
    issues: list[dict[str, Any]],
    state: dict[str, Any],
) -> None:
    """Append a validator report's findings to issues and state."""
    reports = state.setdefault("_validation_reports", [])
    reports.append(report.model_dump())

    for bi in report.blocking_issues:
        issues.append(
            {
                "issue_id": f"val:{report.validator_id}:{bi.code}",
                "severity": "blocking",
                "code": bi.code,
                "message": bi.message,
                "validator_id": report.validator_id,
            }
        )

    for w in report.warnings:
        issues.append(
            {
                "issue_id": f"val:{report.validator_id}:{w.code}",
                "severity": "warning",
                "code": w.code,
                "message": w.message,
                "validator_id": report.validator_id,
            }
        )


def post_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    updates: dict[str, Any] = {
        "current_phase": "post",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "assembly",
    }
    new_refs: list[str] = []

    result = _run_agent(
        new_state,
        agent_id="failure-handling-agent",
        phase="post",
        task="Create the assembly manifest from generated media and the shot matrix.",
    )
    manifest = result.get("assembly_manifest")
    if manifest is not None:
        ref = _save_artifact(new_state, manifest, "assembly_manifest", "post")
        if ref:
            updates["assembly_manifest_ref"] = ref
            new_refs.append(ref)

    if new_refs:
        updates["artifact_refs"] = new_refs
    return updates


def delivery_node(_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_phase": "delivery",
        "approved": False,
        "human_approval_required": True,
        "human_approval_phase": "final_delivery",
    }


def consistency_check_node(state: dict[str, Any]) -> dict[str, Any]:
    """Post-phase consistency check: are our outputs still valid?

    Runs staleness detection on all artifacts created in the current phase.
    Warnings are informational (non-blocking) in Phase 3.
    """
    services = _get_services(state)
    if services is None:
        return {}

    from film_pipeline.graph.consistency import check_phase_consistency

    warnings = check_phase_consistency(state, services)
    return {"consistency_warnings": warnings} if warnings else {}


def await_approval_node(state: dict[str, Any]) -> dict[str, Any]:
    """Pause the graph for human review. Resumes via Command(resume=decision).

    LangGraph constraint: all code before ``interrupt()`` re-executes on
    resume. The payload is built from state reads only — no mutations —
    so it is naturally idempotent.
    """
    from langgraph.types import interrupt

    from film_pipeline.graph.orchestrator_state import is_stalled

    phase = str(state.get("current_phase", ""))
    gate = str(state.get("human_approval_phase", ""))
    issues: list[dict[str, Any]] = state.get("issues", [])
    blocking_count = sum(1 for i in issues if i.get("severity") == "blocking")
    stalled = is_stalled(state, phase)

    # Determine allowed actions
    allowed_actions: list[str] = []
    if blocking_count == 0:
        allowed_actions.append("approve_phase")
    if stalled:
        allowed_actions.append("escalate")
    else:
        allowed_actions.append("request_revision")

    payload: dict[str, Any] = {
        "project_id": state.get("project_id", ""),
        "phase": phase,
        "gate": gate,
        "artifact_refs": state.get("artifact_refs", []),
        "blocking_issue_count": blocking_count,
        "stalled": stalled,
        "allowed_actions": allowed_actions,
    }

    decision = interrupt(payload)

    # Normalize the decision
    if isinstance(decision, dict):
        action = str(decision.get("action", ""))
        note = str(decision.get("note", ""))
    elif isinstance(decision, str):
        action = decision
        note = ""
    else:
        action = "await"

    if action in ("approve", "approve_phase"):
        return approve_phase_node(state)
    if action in ("revise", "request_revision"):
        if note:
            state["_revision_note"] = note
        return request_revision_node(state)
    return state


def approve_phase_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)

    # ── Guard: reject approval when structural issues exist ──────────
    issues: list[dict[str, Any]] = new_state.get("issues", [])
    blocking = [i for i in issues if i.get("severity") == "blocking"]
    if blocking:
        new_state["approved"] = False
        new_state["_approval_blocked_by_issues"] = True
        return new_state

    new_state["approved"] = True
    new_state["human_approval_required"] = False

    # Promote all candidate refs to approved
    from film_pipeline.graph.orchestrator_state import (
        ensure_orchestrator_state,
        get_candidate_refs,
        set_approved_ref,
    )

    ensure_orchestrator_state(new_state)
    for family, ref in get_candidate_refs(new_state).items():
        set_approved_ref(new_state, family, ref)

    return new_state


def request_revision_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["approved"] = False
    new_state["human_approval_required"] = False
    revision_note = str(new_state.pop("_revision_note", ""))
    issues = new_state.get("issues", [])
    new_state["issues"] = [
        *issues,
        {
            "issue_id": "rev",
            "severity": "warning",
            "code": "REVISION_REQUESTED",
            "message": revision_note or "Human requested revision.",
        },
    ]
    # Record durable revision request via orchestrator state helpers
    from film_pipeline.graph.orchestrator_state import (
        add_revision_request,
        ensure_orchestrator_state,
    )

    ensure_orchestrator_state(new_state)
    artifact_refs = new_state.get("artifact_refs", [])
    add_revision_request(new_state, artifact_refs, note="Human requested revision.")
    return new_state


def _is_new_ref(ref: str, original_state: dict[str, Any]) -> bool:
    """Return True if *ref* was not present in the original state's artifact_refs."""
    orig_refs = set(original_state.get("artifact_refs", []) or [])
    return ref not in orig_refs


def _is_new_issue(issue: dict[str, Any], original_state: dict[str, Any]) -> bool:
    """Return True if *issue* has a novel issue_id not in the original state."""
    iid = issue.get("issue_id")
    if not iid:
        return False
    orig_ids = {
        i.get("issue_id")
        for i in (original_state.get("issues", []) or [])
        if i.get("issue_id")
    }
    return iid not in orig_ids


# ── Phase node registry (for repair routing) ────────────────────────────


_PHASE_NODES: dict[str, Any] = {
    "intake": None,  # intake_node,
    "constitution": None,  # constitution_node,
    "development": None,  # development_node,
    "script": None,  # script_node,
    "visual_dev": None,  # visual_dev_node,
    "shot_bible": None,  # shot_bible_node,
    "gen_planning": None,  # gen_planning_node,
    "generation": None,  # generation_node,
    "qc": None,  # qc_node,
    "post": None,  # post_node,
    "delivery": None,  # delivery_node,
}


def _init_phase_nodes() -> None:
    """Lazy-init the phase node registry to avoid circular imports."""
    if _PHASE_NODES["intake"] is not None:
        return
    _PHASE_NODES.update(
        {
            "intake": intake_node,
            "constitution": constitution_node,
            "development": development_node,
            "script": script_node,
            "visual_dev": visual_dev_node,
            "shot_bible": shot_bible_node,
            "gen_planning": gen_planning_node,
            "generation": generation_node,
            "qc": qc_node,
            "post": post_node,
            "delivery": delivery_node,
        }
    )


def repair_phase_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generic repair: re-run the current phase's agent to fix issues.

    Checks convergence tracking — after 3 repair rounds without resolution,
    marks the phase as stalled and returns to human.
    """
    from film_pipeline.graph.orchestrator_state import (
        increment_convergence_round,
        is_stalled,
        mark_stalled,
    )

    _init_phase_nodes()
    phase = str(state.get("current_phase", ""))
    phase_fn = _PHASE_NODES.get(phase)
    if phase_fn is None:
        new_state = deepcopy(state)
        new_state.setdefault("issues", []).append(
            {
                "severity": "warning",
                "code": "no_repair_handler",
                "message": f"No repair handler for phase '{phase}'.",
            }
        )
        return new_state

    # Track repair attempts
    round_num = increment_convergence_round(state, phase)

    if is_stalled(state, phase, max_rounds=3):
        mark_stalled(state, phase, f"Repair failed after {round_num} rounds.")
        return state

    # Inject feedback so the agent knows what to fix
    blocking = [i for i in state.get("issues", []) if i.get("severity") == "blocking"]
    if blocking:
        feedback_parts = []
        for i in blocking:
            code = i.get("code", "?")
            msg = i.get("message", "")
            feedback_parts.append(f"[{code}] {msg}")
        state["_repair_feedback"] = (
            f"REPAIR ROUND {round_num}: Your previous output was REJECTED. "
            f"Issues to fix:\n" + "\n".join(feedback_parts)
        )

    # Re-run the phase node — gates will re-validate
    return cast(dict[str, Any], phase_fn(state))
