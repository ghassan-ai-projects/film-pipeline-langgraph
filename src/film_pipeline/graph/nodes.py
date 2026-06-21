"""Graph node definitions — one per phase.

Spine phases (intake, constitution, development, script) invoke real agents
and persist artifacts. Remaining phases are flag-only pending fan-out.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from film_pipeline.graph.services import SERVICES_KEY, GraphServices
from film_pipeline.schemas._base import ArtifactType as _ArtifactType
from film_pipeline.schemas.artifact import ArtifactRef as _ArtifactRef


def _get_services(state: dict[str, Any]) -> GraphServices | None:
    return state.get(SERVICES_KEY)


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
    from film_pipeline.agents.impl.visual_dev_agent import VisualDevAgent

    agent_map: dict[str, type[BaseAgent]] = {
        "intake-classifier-agent": IntakeAgent,
        "film-constitution-agent": ConstitutionAgent,
        "treatment-agent": DevelopmentAgent,
        "screenwriter-agent": ScreenwriterAgent,
        "shot-design-agent": ShotBibleAgent,
        "reference-strategy-planner": VisualDevAgent,
        "visual-dev-agent": VisualDevAgent,
        "provider-planning-agent": GenPlannerAgent,
        "clip-validator": QCSynthesisAgent,
        "failure-handling-agent": AssemblyAgent,
    }
    agent_cls = agent_map.get(resolved_agent_id)

    template_id = ""
    model_profile = ""

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
        ):
            val = state.get(key)
            if val:
                context_vars[key] = str(val)
        _inject_artifact_context(state, services, context_vars)
        _inject_config_context(state, context_vars)

        model_output, template_id, model_profile = services.prompt_runner.run_from_template(
            template, kb, task, context_vars=context_vars
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
        model_profile=model_profile,
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
) -> str | None:
    """Persist an artifact via ArtifactStore and return its ref string.

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

    parent_refs = state.get("artifact_refs", [])
    parents = [_parse_ref(r) for r in parent_refs]

    meta = ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=atype,
        project_id=str(state.get("project_id", "")),
        phase=FilmPhase(phase),
        version=1,
        status=ArtifactStatus.CANDIDATE,
        parents=parents,
        created_by="graph_node",
        created_at=datetime.now(UTC),
    )
    services.artifact_store.save(artifact, meta)
    ref = f"artifact:{artifact_id}:v1"

    # Record candidate ref for orchestrator state
    from film_pipeline.graph.orchestrator_state import ensure_orchestrator_state, set_candidate_ref

    ensure_orchestrator_state(state)
    set_candidate_ref(state, artifact_id, ref)

    return ref


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
    new_state["current_phase"] = "intake"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "config"

    result = _run_agent(
        new_state,
        agent_id="intake-classifier-agent",
        phase="intake",
        task="Classify the user's film idea and produce a project profile.",
    )
    profile = result.get("profile")
    if profile is not None:
        ref = _save_artifact(new_state, profile, "project_profile", "intake")
        if ref:
            new_state["profile_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    return new_state


# ── Constitution ─────────────────────────────────────────────────────────────


def constitution_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "constitution"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "constitution"

    result = _run_agent(
        new_state,
        agent_id="film-constitution-agent",
        phase="constitution",
        task="Create the film's creative constitution from the project idea.",
    )
    constitution = result.get("constitution")
    if constitution is not None:
        ref = _save_artifact(new_state, constitution, "film_constitution", "constitution")
        if ref:
            new_state["constitution_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    return new_state


# ── Development ──────────────────────────────────────────────────────────────


def development_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "development"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "treatment"

    result = _run_agent(
        new_state,
        agent_id="treatment-agent",
        phase="development",
        task="Write the film treatment and scene breakdown from the constitution.",
    )
    treatment = result.get("treatment")
    scene_list = result.get("scene_list")
    if treatment is not None:
        ref = _save_artifact(new_state, treatment, "treatment", "development")
        if ref:
            new_state["treatment_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)
    if scene_list is not None:
        ref = _save_artifact(new_state, scene_list, "scene_list", "development")
        if ref:
            new_state["scene_list_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    return new_state


# ── Script ───────────────────────────────────────────────────────────────────


def script_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "script"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "script"

    result = _run_agent(
        new_state,
        agent_id="screenwriter-agent",
        phase="script",
        task="Write the full screenplay from the treatment and scene intents.",
    )
    story_bible = result.get("story_bible")
    script = result.get("script")
    if story_bible is not None:
        ref = _save_artifact(new_state, story_bible, "story_bible", "script")
        if ref:
            new_state["story_bible_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)
    if script is not None:
        ref = _save_artifact(new_state, script, "script", "script")
        if ref:
            new_state["script_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    return new_state


# ── Remaining phases (flag-only, pending agent implementations) ──────────────


def visual_dev_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "visual_dev"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "visual_bible"

    result = _run_agent(
        new_state,
        agent_id="reference-strategy-planner",
        phase="visual_dev",
        task="Create visual development references from the script and constitution.",
    )
    index = result.get("reference_index")
    if index is not None:
        ref = _save_artifact(new_state, index, "reference_index", "visual_dev")
        if ref:
            new_state["visual_refs"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    return new_state


def shot_bible_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "shot_bible"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "shot_bible"

    result = _run_agent(
        new_state,
        agent_id="shot-design-agent",
        phase="shot_bible",
        task="Create the detailed shot matrix from the script and visual references.",
    )
    shot_matrix = result.get("shot_matrix")
    if shot_matrix is not None:
        ref = _save_artifact(new_state, shot_matrix, "shot_matrix", "shot_bible")
        if ref:
            new_state["shot_matrix_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    return new_state


def gen_planning_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "gen_planning"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "generation_spend"

    result = _run_agent(
        new_state,
        agent_id="provider-planning-agent",
        phase="gen_planning",
        task="Create the generation plan from the shot matrix and budget constraints.",
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

    return new_state


def generation_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "generation"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "generation_batch"
    return new_state


def qc_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "qc"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "qc"

    # Run the consensus agent for QC synthesis
    result = _run_agent(
        new_state,
        agent_id="clip-validator",
        phase="qc",
        task="Synthesize validator reports into a unified QC report.",
    )
    report = result.get("consensus_report")
    if report is not None:
        ref = _save_artifact(new_state, report, "consensus_report", "qc")
        if ref:
            new_state["consensus_report_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    # Run validators against upstream artifacts
    _run_validators(new_state)

    return new_state


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
        _run_script_validators(artifact_data, issues, state)

    if phase in ("visual_dev", "qc") and artifact_data:
        _run_reference_validators(artifact_data, issues, state)

    if phase in ("gen_planning", "qc") and artifact_data:
        _run_prompt_validators(artifact_data, issues, state)

    if phase in ("shot_bible", "qc") and artifact_data:
        _run_continuity_validators(artifact_data, issues, state)

    if phase in ("post", "assembly", "qc") and artifact_data:
        _run_assembly_validators(artifact_data, issues, state)

    if phase == "delivery" and artifact_data:
        _run_delivery_validators(artifact_data, issues, state)

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
) -> None:
    """Run the two script-phase validators against loaded artifacts."""
    from film_pipeline.validation.impl.dialogue_voice import DialogueVoiceValidator
    from film_pipeline.validation.impl.script_structure import ScriptStructureValidator

    raw: Any = next(iter(artifact_data.values()), {})
    artifact: dict[str, Any] = raw if isinstance(raw, dict) else {}
    for vcls in (ScriptStructureValidator, DialogueVoiceValidator):
        try:
            instance = vcls()
            report = instance.run(artifact)
        except Exception:
            continue
        _append_validator_report(report, issues, state)


def _run_reference_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
) -> None:
    """Run reference usability validator against visual_dev artifacts."""
    from film_pipeline.validation.impl.reference_usability import ReferenceUsabilityValidator

    raw: Any = next(iter(artifact_data.values()), {})
    artifact: dict[str, Any] = raw if isinstance(raw, dict) else {}
    try:
        instance = ReferenceUsabilityValidator()
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _run_prompt_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
) -> None:
    """Run prompt readiness validator against gen_planning artifacts."""
    from film_pipeline.validation.impl.prompt_readiness import PromptReadinessValidator

    raw: Any = next(iter(artifact_data.values()), {})
    artifact: dict[str, Any] = raw if isinstance(raw, dict) else {}
    try:
        instance = PromptReadinessValidator()
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _run_continuity_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
) -> None:
    """Run scene continuity validator against shot_bible artifacts."""
    from film_pipeline.validation.impl.scene_continuity import SceneContinuityValidator

    raw: Any = next(iter(artifact_data.values()), {})
    artifact: dict[str, Any] = raw if isinstance(raw, dict) else {}
    try:
        instance = SceneContinuityValidator()
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _run_assembly_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
) -> None:
    """Run assembly validator against post/assembly artifacts."""
    from film_pipeline.validation.impl.assembly import AssemblyValidator

    raw: Any = next(iter(artifact_data.values()), {})
    artifact: dict[str, Any] = raw if isinstance(raw, dict) else {}
    try:
        instance = AssemblyValidator()
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _run_delivery_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
) -> None:
    """Run delivery completeness validator against delivery artifacts."""
    from film_pipeline.validation.impl.delivery_completeness import (
        DeliveryCompletenessValidator,
    )

    raw: Any = next(iter(artifact_data.values()), {})
    artifact: dict[str, Any] = raw if isinstance(raw, dict) else {}
    try:
        instance = DeliveryCompletenessValidator()
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
    new_state["current_phase"] = "post"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "assembly"

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
            new_state["assembly_manifest_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    return new_state


def delivery_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "delivery"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "final_delivery"
    return new_state


def approve_phase_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
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
    issues = new_state.get("issues", [])
    new_state["issues"] = [
        *issues,
        {
            "issue_id": "rev",
            "severity": "warning",
            "code": "REVISION_REQUESTED",
            "message": "Human requested revision.",
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
