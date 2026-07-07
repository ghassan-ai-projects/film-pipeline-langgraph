"""Prompt-context assembly: phase context, artifact injection, config context."""

from __future__ import annotations

import logging
from typing import Any

from film_pipeline.graph.nodes._shared import (
    _get_services,
)
from film_pipeline.graph.services import GraphServices
from film_pipeline.kb.compression import DEFAULT_MAX_CONTEXT_CHARS, compact_json_context
from film_pipeline.schemas._base import ArtifactType as _ArtifactType
from film_pipeline.schemas.artifact import ArtifactRef as _ArtifactRef

_logger = logging.getLogger(__name__)


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
            except Exception as exc:
                _logger.warning("Could not load constitution summary for context: %s", exc)

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
            _logger.warning(
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
