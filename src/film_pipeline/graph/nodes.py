"""Graph node definitions — one per phase.

Spine phases (intake, constitution, development, script) invoke real agents
and persist artifacts. Remaining phases are flag-only pending fan-out.
"""

from __future__ import annotations

import contextvars
import json
from copy import deepcopy
from typing import Any, cast

from film_pipeline.agents.base import BaseAgent
from film_pipeline.agents.impl.registry import get_agent_class
from film_pipeline.graph.services import SERVICES_KEY, GraphServices
from film_pipeline.kb.compression import DEFAULT_MAX_CONTEXT_CHARS, compact_json_context
from film_pipeline.schemas._base import ArtifactType as _ArtifactType
from film_pipeline.schemas.artifact import ArtifactRef as _ArtifactRef

_SERVICES_CTX: contextvars.ContextVar[GraphServices | None] = contextvars.ContextVar(
    "_film_pipeline_services", default=None
)


def _get_services(state: dict[str, Any]) -> GraphServices | None:
    """Return ``GraphServices`` from state, falling back to context variable.

    When running through a LangGraph ``StateGraph`` channel system,
    extra state keys not declared in the TypedDict may be dropped.
    The context variable provides a reliable fallback.
    """
    svc = state.get(SERVICES_KEY)
    if svc is not None:
        return svc  # type: ignore[no-any-return]
    return _SERVICES_CTX.get()


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
    "orchestrator-agent": "strict_validator",
    "kb-curator-agent": "operations_triage",
}


# Upstream context a phase cannot do good work without. If one of these refs is
# set but failed to load, the agent ran context-blind — block instead of
# silently shipping weak output.
_CRITICAL_CONTEXT: dict[str, list[str]] = {
    "development": ["constitution_ref"],
    "script": ["constitution_ref", "treatment_ref", "scene_list_ref"],
}


def _critical_context_issues(state: dict[str, Any], phase: str) -> list[dict[str, Any]]:
    """Blocking issues for critical upstream context that failed to load."""
    required = _CRITICAL_CONTEXT.get(phase, [])
    if not required:
        return []
    failures = set(state.get("_context_load_failures", []) or [])
    issues: list[dict[str, Any]] = []
    for key in required:
        ref = str(state.get(key, "") or "").strip()
        if ref and key in failures:
            issues.append(
                {
                    "issue_id": f"ctx_unavailable_{key}",
                    "severity": "blocking",
                    "code": "critical_context_unavailable",
                    "message": (
                        f"Required upstream artifact '{key}' ({ref}) could not be "
                        f"loaded for the {phase} phase. The agent would write "
                        "context-blind; resolve the upstream artifact before continuing."
                    ),
                }
            )
    return issues


def _coerce_user_runtime(state: dict[str, Any]) -> int:
    """Return the user-supplied target runtime (seconds), or 0 if not provided.

    Seeded into state before the graph runs by the create/submit entry points.
    When > 0 it is authoritative and overrides any model-estimated runtime.
    """
    raw = state.get("target_runtime_seconds")
    if raw is None or isinstance(raw, bool):
        return 0
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return value if value > 0 else 0


def _require_human_approval(state: dict[str, Any]) -> bool:
    """Read ``require_human_approval`` from resolved config.

    Defaults to ``True`` (gates ON) when the key is missing or the config
    is unpopulated — safe-by-default for production. Set to ``False`` in
    a profile (e.g. ``auto-approve.yaml``) for headless/automated runs.
    """
    cfg = state.get("resolved_config", {})
    if isinstance(cfg, dict):
        studio = cfg.get("studio", {})
        if isinstance(studio, dict):
            return bool(studio.get("require_human_approval", True))
    return True


def _build_phase_context(state: dict[str, Any]) -> dict[str, str]:
    """Build context vars for the orchestrator review agent.

    Summarises the target film, current phase output, and structural metrics
    so the orchestrator can assess quality without loading every artifact.
    """
    ctx: dict[str, str] = {
        "target_runtime_seconds": str(state.get("target_runtime_seconds", "300")),
        "film_type": str(state.get("film_type", "narrative")),
        "pacing_style": "standard",
        "current_phase": str(state.get("current_phase", "")),
        "convergence_round": "1",
        "constitution_summary": "(not available)",
        "phase_output_summary": "(not available)",
        "metrics_summary": "(not available)",
        "consistency_warnings": "(none)",
    }

    # Convergence round from orchestrator state
    conv = state.get("_orchestrator__convergence", {})
    if isinstance(conv, dict):
        phase_conv = conv.get(ctx["current_phase"], {})
        if isinstance(phase_conv, dict):
            ctx["convergence_round"] = str(phase_conv.get("round_count", 1))

    # Constitution summary
    constitution_ref = state.get("constitution_ref", "")
    if constitution_ref and isinstance(constitution_ref, str) and constitution_ref.strip():
        services = _get_services(state)
        if services is not None:
            try:
                parsed = _parse_ref(str(constitution_ref))
                from film_pipeline.schemas._base import FilmPhase

                data = services.artifact_store.load(
                    str(state.get("project_id", "")),
                    FilmPhase("constitution"),
                    parsed.artifact_id,
                    parsed.version,
                )
                if isinstance(data, dict):
                    ctx["constitution_summary"] = (
                        f"theme: {data.get('theme', '?')}\n"
                        f"tone: {data.get('tone', '?')}\n"
                        f"visual_language: {str(data.get('visual_language', ''))[:200]}"
                    )
            except Exception:
                pass

    # Phase output summary — load current phase artifacts
    services = _get_services(state)
    if services is not None:
        from film_pipeline.schemas._base import FilmPhase

        project_id = str(state.get("project_id", ""))
        try:
            artifacts = services.artifact_store.list_artifacts(
                project_id, FilmPhase(ctx["current_phase"])
            )
        except Exception:
            artifacts = []

        lines: list[str] = []
        total_scenes = 0
        total_shots = 0
        for a in artifacts:
            try:
                data = services.artifact_store.load(
                    project_id, FilmPhase(ctx["current_phase"]), a.artifact_id, a.version
                )
            except Exception:
                continue
            if isinstance(data, dict):
                lines.append(f"\n{a.artifact_id} (v{a.version}):")
                # Extract key metrics
                for key in ("scenes", "scene_list", "rows", "shot_count"):
                    val = data.get(key)
                    if isinstance(val, list):
                        lines.append(f"  {key}: {len(val)} items")
                        if key == "scenes":
                            total_scenes = len(val)
                        elif key == "rows":
                            total_shots = len(val)
                # Scene-level preview
                scenes = data.get("scenes", [])
                if isinstance(scenes, list):
                    for s in scenes[:5]:
                        if isinstance(s, dict):
                            sid = s.get("scene_id", "?")
                            func = str(s.get("dramatic_function", ""))[:80]
                            lines.append(f"  {sid}: {func}")
                rows = data.get("rows", [])
                if isinstance(rows, list):
                    for r in rows[:5]:
                        if isinstance(r, dict):
                            sid = r.get("shot_id", "?")
                            dur = r.get("duration_seconds", "?")
                            lines.append(f"  {sid}: {dur}s")
                # Key text fields
                for key in ("text", "theme", "themes", "title"):
                    val = data.get(key)
                    if isinstance(val, str) and val:
                        lines.append(f"  {key}: {val[:150]}")
                    elif isinstance(val, list):
                        lines.append(f"  {key}: {', '.join(str(x)[:60] for x in val[:3])}")

        ctx["phase_output_summary"] = "\n".join(lines) if lines else "(no artifacts produced)"

        # Metrics
        target = int(ctx["target_runtime_seconds"])
        metrics_parts: list[str] = []
        if total_scenes:
            avg_scene = target / max(total_scenes, 1)
            metrics_parts.append(
                f"scene_count: {total_scenes} (~{avg_scene:.0f}s per scene for {target}s target)"
            )
        if total_shots:
            metrics_parts.append(f"shot_count: {total_shots}")
        if total_shots and total_scenes:
            metrics_parts.append(f"shots_per_scene: {total_shots / max(total_scenes, 1):.1f}")
        ctx["metrics_summary"] = "\n".join(metrics_parts) if metrics_parts else "(no metrics)"

        # Consistency warnings
        warnings = state.get("consistency_warnings", [])
        if warnings:
            ctx["consistency_warnings"] = "\n".join(
                str(w)[:200] for w in (warnings if isinstance(warnings, list) else [])
            )
            if (
                isinstance(ctx["consistency_warnings"], str)
                and len(ctx["consistency_warnings"]) > 800
            ):
                ctx["consistency_warnings"] = ctx["consistency_warnings"][:800] + "..."

    return ctx


def _propagate_side_effects(source: dict[str, Any], dest: dict[str, Any]) -> None:
    """Copy known side-effect keys from ``source`` to ``dest``.

    ``_run_agent`` mutates ``source`` (the node's ``new_state``) via
    ``_record_handoff``, but nodes return only an ``updates`` dict.
    This helper ensures routing decisions and other side effects
    survive the node boundary.
    """
    for key in (
        "_routing_decisions",
        "_repair_feedback",
        "issues",
        "validation_report_refs",
        "_validation_reports",
    ):
        if key in source:
            dest[key] = source[key]


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
    "StoryScopeContract": "project_config",
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
            context_vars[content_key] = compact_json_context(
                data,
                max_chars=_artifact_context_max_chars(state),
            )
        except (FileNotFoundError, ValueError, KeyError) as exc:
            # Do NOT swallow silently — a missing upstream artifact means the
            # agent would run context-blind (a hidden cause of weak output).
            # Log it and record the failure so the phase gate can block.
            import logging

            logging.getLogger(__name__).warning(
                "Could not load upstream artifact for prompt context: %s=%s (%s)",
                ref_key,
                ref,
                exc,
            )
            failures = state.setdefault("_context_load_failures", [])
            if ref_key not in failures:
                failures.append(ref_key)
            continue


def _model_overrides_for(state: dict[str, Any], model_profile: str) -> dict[str, Any] | None:
    """Return per-profile model overrides from resolved config, if any.

    Profiles may declare a ``model_profiles`` map to swap the model or sampling
    params for a logical profile (e.g. festival → a stronger model for the
    ``creative_writer`` profile) without any code change.
    """
    resolved_config = state.get("resolved_config", {})
    if not isinstance(resolved_config, dict):
        return None
    model_profiles = resolved_config.get("model_profiles", {})
    if not isinstance(model_profiles, dict):
        return None
    override = model_profiles.get(model_profile)
    return override if isinstance(override, dict) and override else None


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


def _artifact_context_max_chars(state: dict[str, Any]) -> int:
    resolved_config = state.get("resolved_config", {})
    if not isinstance(resolved_config, dict):
        return DEFAULT_MAX_CONTEXT_CHARS
    context_config = resolved_config.get("context", {})
    if not isinstance(context_config, dict):
        return DEFAULT_MAX_CONTEXT_CHARS
    raw = context_config.get("max_chars_per_artifact")
    if raw is None or isinstance(raw, bool):
        return DEFAULT_MAX_CONTEXT_CHARS
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_MAX_CONTEXT_CHARS
    return value if value > 0 else DEFAULT_MAX_CONTEXT_CHARS


# ── Intake ───────────────────────────────────────────────────────────────────


def intake_node(state: dict[str, Any]) -> dict[str, Any]:
    """Intake: classify input, infer config, present for approval."""
    new_state = deepcopy(state)
    auto = not _require_human_approval(new_state)
    updates: dict[str, Any] = {
        "current_phase": "intake",
        "approved": auto,
        "human_approval_required": not auto,
        "human_approval_phase": "config",
    }
    new_refs: list[str] = []

    # User-supplied runtime (seeded before the graph ran) is authoritative.
    user_runtime = _coerce_user_runtime(new_state)
    runtime_clause = (
        f" The user REQUIRES a target runtime of {user_runtime} seconds — adopt it "
        "exactly as target_runtime_seconds; do not estimate your own."
        if user_runtime > 0
        else " Estimate a realistic runtime from the story's scope."
    )

    result = _run_agent(
        new_state,
        agent_id="intake-classifier-agent",
        phase="intake",
        task=(
            "Classify the user's film idea: determine genre, tone, audience, "
            "aspect ratio, and delivery format." + runtime_clause + " "
            "Identify risks and produce a structured project profile."
        ),
    )
    profile = result.get("profile")
    if profile is not None:
        # Authority override: lock the user's runtime onto the saved profile so the
        # persisted artifact and downstream state agree.
        if user_runtime > 0 and hasattr(profile, "model_copy"):
            profile = profile.model_copy(update={"target_runtime_seconds": user_runtime})
        ref = _save_artifact(new_state, profile, "project_profile", "intake")
        if ref:
            updates["profile_ref"] = ref
            new_refs.append(ref)
        if user_runtime > 0:
            updates["target_runtime_seconds"] = user_runtime
        elif hasattr(profile, "target_runtime_seconds"):
            updates["target_runtime_seconds"] = profile.target_runtime_seconds
        if hasattr(profile, "film_type"):
            updates["film_type"] = str(profile.film_type)

    # ── Derive the Story Scope Contract (deterministic, forward-looking) ──
    _attach_scope_contract(new_state, updates, new_refs)

    if new_refs:
        updates["artifact_refs"] = new_refs
    _propagate_side_effects(new_state, updates)
    return updates


def _attach_scope_contract(
    state: dict[str, Any],
    updates: dict[str, Any],
    new_refs: list[str],
) -> None:
    """Compute and persist the Story Scope Contract from runtime x film style.

    Uses the authoritative runtime (user value already locked into ``updates``),
    the classified film_type, and the profile's pacing. Stores concrete scene/
    shot targets in state so prep prompts and gates can enforce them.
    """
    from film_pipeline.graph.scope_contract import derive_scope_contract, pacing_from_config

    runtime = int(
        updates.get("target_runtime_seconds", state.get("target_runtime_seconds", 0)) or 0
    )
    if runtime <= 0:
        return
    film_type = str(updates.get("film_type", state.get("film_type", "narrative")) or "narrative")
    pacing = pacing_from_config(state.get("resolved_config"))

    contract = derive_scope_contract(
        project_id=str(state.get("project_id", "")),
        target_runtime_seconds=runtime,
        film_type=film_type,
        pacing=pacing,
    )
    ref = _save_artifact(state, contract, "scope_contract", "intake")
    if ref:
        updates["scope_contract_ref"] = ref
        new_refs.append(ref)
    updates["pacing_style"] = contract.pacing_style
    updates["target_scene_count"] = contract.target_scene_count
    updates["min_scene_count"] = contract.min_scene_count
    updates["target_shot_count"] = contract.target_shot_count


# ── Constitution ─────────────────────────────────────────────────────────────


def constitution_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    auto = not _require_human_approval(new_state)
    updates: dict[str, Any] = {
        "current_phase": "constitution",
        "approved": auto,
        "human_approval_required": not auto,
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
    _propagate_side_effects(new_state, updates)
    return updates


# ── Development ──────────────────────────────────────────────────────────────


def development_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    auto = not _require_human_approval(new_state)
    updates: dict[str, Any] = {
        "current_phase": "development",
        "approved": auto,
        "human_approval_required": not auto,
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

    # ── Gate: surface context-blind runs (WS-I) ──────────────────────────
    node_issues: list[dict[str, Any]] = _critical_context_issues(new_state, "development")

    if scene_list is not None:
        ref = _save_artifact(new_state, scene_list, "scene_list", "development")
        if ref:
            updates["scene_list_ref"] = ref
            new_refs.append(ref)

        # ── Gate S: scene count must meet the Scope Contract floor ────────
        from film_pipeline.graph.orchestrator_validators import validate_scene_count

        scene_count = len(getattr(scene_list, "scenes", []) or [])
        node_issues += validate_scene_count(new_state, scene_count)

    fresh_issues = [i for i in node_issues if _is_new_issue(i, state)]
    if fresh_issues:
        updates["issues"] = fresh_issues

    if new_refs:
        updates["artifact_refs"] = new_refs
    _propagate_side_effects(new_state, updates)
    return updates


# ── Script ───────────────────────────────────────────────────────────────────


def script_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    auto = not _require_human_approval(new_state)
    updates: dict[str, Any] = {
        "current_phase": "script",
        "approved": auto,
        "human_approval_required": not auto,
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

    # ── Gate: surface context-blind runs (WS-I) ──────────────────────────
    node_issues: list[dict[str, Any]] = _critical_context_issues(new_state, "script")

    if script is not None:
        ref = _save_artifact(new_state, script, "script", "script")
        if ref:
            updates["script_ref"] = ref
            new_refs.append(ref)

        # ── Gate S: script must preserve development scenes and meet floor ─
        from film_pipeline.graph.orchestrator_validators import (
            validate_script_scene_preservation,
        )

        script_scene_count = len(getattr(script, "scenes", []) or [])
        dev_scene_count = _development_scene_count(new_state)
        node_issues += validate_script_scene_preservation(
            new_state, script_scene_count, dev_scene_count
        )

    fresh_issues = [i for i in node_issues if _is_new_issue(i, state)]
    if fresh_issues:
        updates["issues"] = fresh_issues

    if new_refs:
        updates["artifact_refs"] = new_refs
    _propagate_side_effects(new_state, updates)
    return updates


def _development_scene_count(state: dict[str, Any]) -> int:
    """Count scenes in the approved development scene list (0 if unavailable)."""
    services = _get_services(state)
    ref = str(state.get("scene_list_ref", "") or "")
    if services is None or not ref:
        return 0
    try:
        from film_pipeline.schemas._base import FilmPhase

        parsed = _parse_ref(ref)
        data = services.artifact_store.load(
            str(state.get("project_id", "")),
            FilmPhase("development"),
            parsed.artifact_id,
            parsed.version,
        )
    except (FileNotFoundError, ValueError, KeyError):
        return 0
    if isinstance(data, dict):
        scenes = data.get("scenes", [])
        if isinstance(scenes, list):
            return len(scenes)
    return 0


# ── Remaining phases (flag-only, pending agent implementations) ──────────────


def visual_dev_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    auto = not _require_human_approval(new_state)
    updates: dict[str, Any] = {
        "current_phase": "visual_dev",
        "approved": auto,
        "human_approval_required": not auto,
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
    _propagate_side_effects(new_state, updates)
    return updates


def shot_bible_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state  # keep reference for diff computation
    auto = not _require_human_approval(new_state)
    new_state["current_phase"] = "shot_bible"
    new_state["approved"] = auto
    new_state["human_approval_required"] = not auto
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
        "approved": auto,
        "human_approval_required": not auto,
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
    _propagate_side_effects(new_state, updates)
    return updates


def gen_planning_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state
    auto = not _require_human_approval(new_state)
    new_state["current_phase"] = "gen_planning"
    new_state["approved"] = auto
    new_state["human_approval_required"] = not auto
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

    # ── Emit matrix patch: update prompt_ref + status per row ────────────
    shot_groups = result.get("shot_groups") or []
    shot_matrix_ref = str(new_state.get("shot_matrix_ref", ""))
    if shot_groups and shot_matrix_ref:
        from film_pipeline.schemas.matrix_patch import MatrixPatch, MatrixRowUpdate

        row_updates: list[Any] = []
        for group in shot_groups:
            sid = str(group.get("shot_id", ""))
            if not sid:
                continue
            row_updates.append(
                MatrixRowUpdate(
                    shot_id=sid,
                    set={
                        "prompt_ref": str(group.get("prompt_ref", "")),
                        "provider_plan_ref": str(group.get("provider_plan_ref", "")),
                        "status": "prompted",
                    },
                )
            )

        if row_updates:
            patch = MatrixPatch(
                patch_id=f"gen_planning_{new_state.get('project_id', '')}",
                matrix_ref=shot_matrix_ref,
                phase="gen_planning",
                reason="Generation plan assigned prompts and provider references per shot.",
                updates=row_updates,
                created_by_agent="provider-planning-agent",
            )
            patch_ref = _save_artifact(
                new_state,
                patch,
                "matrix_patch_gen_planning",
                "gen_planning",
                artifact_type="generation_plan",
            )
            if patch_ref:
                new_state["gen_planning_patch_ref"] = patch_ref
                new_state.setdefault("artifact_refs", []).append(patch_ref)

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
                    validate_shot_scene_references,
                )

                plan_issues = validate_planning_completeness(new_state, matrix_data, cost_estimate)
                new_state.setdefault("issues", []).extend(plan_issues)
                script_ref = str(new_state.get("script_ref", "") or "")
                if script_ref:
                    script_parsed = _parse_ref(script_ref)
                    script_data = services.artifact_store.load(
                        str(new_state.get("project_id", "")),
                        FilmPhase("script"),
                        script_parsed.artifact_id,
                        script_parsed.version,
                    )
                    ref_issues = validate_shot_scene_references(script_data, matrix_data)
                    new_state.setdefault("issues", []).extend(ref_issues)
            except (FileNotFoundError, ValueError, KeyError):
                pass

    # Compute partial update from before/after diff
    updates: dict[str, Any] = {
        "current_phase": "gen_planning",
        "approved": auto,
        "human_approval_required": not auto,
        "human_approval_phase": "generation_spend",
    }
    new_refs = [r for r in (new_state.get("artifact_refs", []) or []) if _is_new_ref(r, original)]
    if new_refs:
        updates["artifact_refs"] = new_refs
    new_issues = [i for i in (new_state.get("issues", []) or []) if _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    for key in ("cost_estimate_ref", "gen_planning_patch_ref"):
        val = new_state.get(key)
        if val:
            updates[key] = val
    _propagate_side_effects(new_state, updates)
    return updates


def generation_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state
    auto = not _require_human_approval(new_state)
    new_state["current_phase"] = "generation"
    new_state["approved"] = auto
    new_state["human_approval_required"] = not auto
    new_state["human_approval_phase"] = "generation_batch"

    # ── Gate C: validate dispatch readiness ──────────────────────────────
    gen_requests = new_state.get("generation_requests")
    if gen_requests is not None:
        from film_pipeline.graph.orchestrator_validators import validate_dispatch_readiness

        dispatch_issues = validate_dispatch_readiness(new_state, gen_requests)
        new_state.setdefault("issues", []).extend(dispatch_issues)

    # ── Emit matrix patch: mark rows as generated ────────────────────────
    shot_matrix_ref = str(new_state.get("shot_matrix_ref", ""))
    if gen_requests and shot_matrix_ref:
        from film_pipeline.schemas.matrix_patch import MatrixPatch, MatrixRowUpdate

        row_updates: list[Any] = []
        for req in gen_requests:
            if isinstance(req, dict):
                sid = str(req.get("shot_id", ""))
                asset_ref = str(req.get("asset_ref", req.get("output_ref", "")))
                if sid:
                    row_updates.append(
                        MatrixRowUpdate(
                            shot_id=sid,
                            set={"status": "generated"},
                            append={"asset_refs": [asset_ref]} if asset_ref else {},
                        )
                    )

        if row_updates:
            patch = MatrixPatch(
                patch_id=f"generation_{new_state.get('project_id', '')}",
                matrix_ref=shot_matrix_ref,
                phase="generation",
                reason="Clips generated — updating row asset references and status.",
                updates=row_updates,
                created_by_agent="generation-scheduler-agent",
            )
            patch_ref = _save_artifact(
                new_state,
                patch,
                "matrix_patch_generation",
                "generation",
                artifact_type="generation_plan",
            )
            if patch_ref:
                new_state["generation_patch_ref"] = patch_ref
                new_state.setdefault("artifact_refs", []).append(patch_ref)

    # Compute partial update from before/after diff
    updates: dict[str, Any] = {
        "current_phase": "generation",
        "approved": auto,
        "human_approval_required": not auto,
        "human_approval_phase": "generation_batch",
    }
    new_issues = [i for i in (new_state.get("issues", []) or []) if _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    _propagate_side_effects(new_state, updates)
    return updates


def qc_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state
    auto = not _require_human_approval(new_state)
    new_state["current_phase"] = "qc"
    new_state["approved"] = auto
    new_state["human_approval_required"] = not auto
    new_state["human_approval_phase"] = "qc"

    # Run validators against upstream artifacts FIRST
    _run_validators(new_state)

    # ── Emit matrix patch from validator findings ────────────────────────
    pending_updates = new_state.pop("_pending_row_updates", [])
    shot_matrix_ref = str(new_state.get("shot_matrix_ref", ""))
    if pending_updates and shot_matrix_ref:
        from film_pipeline.schemas.matrix_patch import MatrixPatch

        patch = MatrixPatch(
            patch_id=f"qc_{new_state.get('project_id', '')}",
            matrix_ref=shot_matrix_ref,
            phase="qc",
            reason="QC validators produced per-row findings — updating status and validation refs.",
            updates=pending_updates,
            created_by_agent="clip-validator",
        )
        patch_ref = _save_artifact(
            new_state,
            patch,
            "matrix_patch_qc",
            "qc",
            artifact_type="consensus_report",
        )
        if patch_ref:
            new_state["qc_patch_ref"] = patch_ref
            new_state.setdefault("artifact_refs", []).append(patch_ref)

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
        "approved": auto,
        "human_approval_required": not auto,
        "human_approval_phase": "qc",
    }
    new_refs = [r for r in (new_state.get("artifact_refs", []) or []) if _is_new_ref(r, original)]
    if new_refs:
        updates["artifact_refs"] = new_refs
    new_issues = [i for i in (new_state.get("issues", []) or []) if _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    for key in ("consensus_report_ref", "qc_patch_ref"):
        val = new_state.get(key)
        if val:
            updates[key] = val
    _propagate_side_effects(new_state, updates)
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
                adapter=getattr(services.prompt_runner, "model_adapter", None),
                router=getattr(services.prompt_runner, "model_router", None),
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
            adapter=getattr(services.prompt_runner, "model_adapter", None),
            router=getattr(services.prompt_runner, "model_router", None),
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
            adapter=getattr(services.prompt_runner, "model_adapter", None),
            router=getattr(services.prompt_runner, "model_router", None),
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
            adapter=getattr(services.prompt_runner, "model_adapter", None),
            router=getattr(services.prompt_runner, "model_router", None),
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
            adapter=getattr(services.prompt_runner, "model_adapter", None),
            router=getattr(services.prompt_runner, "model_router", None),
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
            adapter=getattr(services.prompt_runner, "model_adapter", None),
            router=getattr(services.prompt_runner, "model_router", None),
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

    # ── Track per-row findings for matrix patch emission ──────────────
    from film_pipeline.schemas.matrix_patch import MatrixRowUpdate

    pending: list[Any] = state.setdefault("_pending_row_updates", [])
    for finding in report.blocking_issues + report.warnings:
        shot_id = getattr(finding, "affected_shot", None)
        if shot_id:
            pending.append(
                MatrixRowUpdate(
                    shot_id=str(shot_id),
                    append={"validation_refs": [report.validator_id]},
                    set={
                        "status": "failed"
                        if getattr(finding, "severity", "") == "blocking"
                        else "validated",
                    },
                )
            )


def post_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    auto = not _require_human_approval(new_state)
    updates: dict[str, Any] = {
        "current_phase": "post",
        "approved": auto,
        "human_approval_required": not auto,
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
    _propagate_side_effects(new_state, updates)
    return updates


def delivery_node(state: dict[str, Any]) -> dict[str, Any]:
    auto = not _require_human_approval(state)
    return {
        "current_phase": "delivery",
        "approved": auto,
        "human_approval_required": not auto,
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


def _run_orchestrator_agent(state: dict[str, Any]) -> dict[str, Any] | None:
    """Run the orchestrator agent to decide approve/revise/escalate.

    Returns the agent's decision dict or ``None`` if the agent is unavailable
    (no services, no model — fall through to human gate).
    """
    services = _get_services(state)
    if services is None:
        return None

    result = _run_agent(
        state,
        agent_id="orchestrator-agent",
        phase=str(state.get("current_phase", "")),
        task=(
            "Review the phase output against the target runtime and constitution. "
            "Decide: approve (output is sound), revise (give one focused suggestion), "
            "or escalate (stuck or fundamentally wrong)."
        ),
    )
    if result.get("status") in ("no_services", "agent_not_found", "no_impl"):
        return None
    action = result.get("action")
    if action not in ("approve", "revise", "escalate"):
        return None
    return result


def await_approval_node(state: dict[str, Any]) -> dict[str, Any]:
    """Pause the graph for human review. Resumes via Command(resume=decision).

    The orchestrator agent runs first — it decides approve/revise autonomously.
    Only escalates to human when the agent is unavailable, returns escalate,
    or the phase is stalled.

    Short-circuits when ``approved`` is already ``True`` — the phase node
    auto-approved (e.g. headless/auto-approve profile). The downstream
    ``after_approval`` routing will advance to the next phase.
    """
    if state.get("approved"):
        return state

    # ── Try autonomous orchestrator agent first ────────────────────────
    from film_pipeline.graph.orchestrator_state import is_stalled

    phase = str(state.get("current_phase", ""))
    stalled = is_stalled(state, phase)

    if not stalled:
        orch_decision = _run_orchestrator_agent(state)
        if orch_decision is not None:
            action = orch_decision.get("action", "escalate")
            if action == "approve":
                return approve_phase_node(state)
            if action == "revise":
                state["_repair_feedback"] = orch_decision.get("feedback", "")
                preserve = orch_decision.get("preserve", [])
                if preserve:
                    state["_repair_feedback"] += "\n\nPreserve: " + "; ".join(
                        str(p) for p in preserve
                    )
                return request_revision_node(state)
            # escalate: fall through to human gate

    # ── Human gate (fallback) ──────────────────────────────────────────
    from langgraph.types import interrupt

    gate = str(state.get("human_approval_phase", ""))
    issues: list[dict[str, Any]] = state.get("issues", [])
    blocking_count = sum(1 for i in issues if i.get("severity") == "blocking")

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
        i.get("issue_id") for i in (original_state.get("issues", []) or []) if i.get("issue_id")
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

    Builds structured ``RepairFeedback`` (saved as artifact) so agents
    know exactly which rows to fix/preserve instead of guessing from text.
    """
    from film_pipeline.graph.orchestrator_state import (
        increment_convergence_round,
        is_stalled,
        mark_stalled,
    )
    from film_pipeline.schemas.repair import (
        GlobalRepairIssue,
        RepairFeedback,
        RowRepairInstruction,
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

    # ── Build structured repair feedback ──────────────────────────────
    issues: list[dict[str, Any]] = state.get("issues", [])
    blocking = [i for i in issues if i.get("severity") == "blocking"]
    all_findings = blocking + [i for i in issues if i.get("severity") == "warning"]

    # Separate row-level from global issues
    row_issues: dict[str, list[dict[str, str]]] = {}
    global_issues: list[GlobalRepairIssue] = []
    passed_ids: list[str] = []

    for finding in all_findings:
        shot_id = str(finding.get("shot_id", finding.get("affected_shot", "")))
        if shot_id:
            row_issues.setdefault(shot_id, []).append(
                {
                    "code": str(finding.get("code", "?")),
                    "field": str(finding.get("field", finding.get("affected_field", ""))),
                    "message": str(finding.get("message", "")),
                    "recommended_action": str(
                        finding.get("suggestion", finding.get("recommended_action", ""))
                    ),
                }
            )
        else:
            global_issues.append(
                GlobalRepairIssue(
                    code=str(finding.get("code", "?")),
                    message=str(finding.get("message", "")),
                    recommended_action=str(finding.get("suggestion", "")),
                )
            )

    # Build row instructions
    failed_rows: list[Any] = []
    for sid, issue_list in row_issues.items():
        failed_rows.append(
            RowRepairInstruction(
                shot_id=sid,
                issues=issue_list,
                preserve_other_fields=True,
            )
        )

    # Determine passed rows from patch history
    previous_artifact = str(state.get("shot_matrix_ref", ""))
    feedback = RepairFeedback(
        repair_id=f"repair:{phase}:r{round_num}",
        phase=phase,
        round=round_num,
        project_id=str(state.get("project_id", "")),
        failed_rows=failed_rows,
        passed_row_ids=passed_ids,
        global_issues=global_issues,
        previous_artifact_ref=previous_artifact,
        convergence_round=round_num,
    )

    # Persist as artifact so the agent can load structured data
    feedback_ref = _save_artifact(
        state,
        feedback,
        f"repair_feedback_{phase}",
        phase,
        artifact_type="script",
    )
    if feedback_ref:
        state["repair_feedback_ref"] = feedback_ref

    # Also inject the rendered context for direct use (backward compat)
    state["_repair_feedback"] = feedback.to_agent_context()

    # Re-run the phase node — gates will re-validate
    return cast(dict[str, Any], phase_fn(state))
