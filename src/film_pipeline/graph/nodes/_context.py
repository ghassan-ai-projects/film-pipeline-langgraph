"""Prompt-context assembly: phase context, artifact injection, config context."""

from __future__ import annotations

import logging
from typing import Any

from film_pipeline.graph.services import GraphServices, _get_services
from film_pipeline.kb.compression import DEFAULT_MAX_CONTEXT_CHARS, compact_json_context
from film_pipeline.schemas._base import ArtifactType as _ArtifactType
from film_pipeline.schemas._base import FilmPhase
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


def _build_phase_context(state: dict[str, Any]) -> dict[str, str]:
    """Build context vars for the orchestrator review agent.

    Summarises the target film, current phase output, and structural metrics
    so the orchestrator can assess quality without loading every artifact.
    """
    ctx = _initial_phase_context(state)
    ctx["constitution_summary"] = _constitution_summary(state)
    _apply_phase_output_sections(state, ctx)
    return ctx


def _initial_phase_context(state: dict[str, Any]) -> dict[str, str]:
    """Default context values with the orchestrator convergence round resolved."""
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

    conv = state.get("_orchestrator__convergence", {})
    if isinstance(conv, dict):
        phase_conv = conv.get(ctx["current_phase"], {})
        if isinstance(phase_conv, dict):
            ctx["convergence_round"] = str(phase_conv.get("round_count", 1))

    return ctx


def _constitution_summary(state: dict[str, Any]) -> str:
    """Constitution digest for prompts, or the placeholder when unavailable."""
    constitution_ref = state.get("constitution_ref", "")
    if not (constitution_ref and isinstance(constitution_ref, str) and constitution_ref.strip()):
        return "(not available)"
    services = _get_services(state)
    if services is None:
        return "(not available)"
    try:
        parsed = _parse_ref(str(constitution_ref))
        data = services.artifact_store.load(
            str(state.get("project_id", "")),
            FilmPhase(parsed.phase),
            parsed.artifact_id,
            parsed.version,
        )
        if isinstance(data, dict):
            return (
                f"theme: {data.get('theme', '?')}\n"
                f"tone: {data.get('tone', '?')}\n"
                f"visual_language: {str(data.get('visual_language', ''))[:200]}"
            )
    except Exception as exc:
        _logger.warning("Could not load constitution summary for context: %s", exc)
    return "(not available)"


def _load_phase_artifacts(
    services: GraphServices,
    project_id: str,
    phase: FilmPhase,
) -> list[tuple[str, dict[str, Any]]]:
    """List and load a phase's artifacts as (versioned label, data) pairs.

    Listing or load failures are skipped silently, matching prior behavior.
    """
    try:
        artifacts = services.artifact_store.list_artifacts(project_id, phase)
    except Exception:
        return []
    loaded: list[tuple[str, dict[str, Any]]] = []
    for a in artifacts:
        try:
            data = services.artifact_store.load(project_id, phase, a.artifact_id, a.version)
        except Exception:
            continue
        if isinstance(data, dict):
            loaded.append((f"{a.artifact_id} (v{a.version})", data))
    return loaded


def _summarize_phase_artifact(artifact: str, data: dict[str, Any]) -> tuple[list[str], int, int]:
    """Preview lines for one artifact plus its scene/shot counts.

    Counts are -1 when the underlying key is absent so callers can reproduce
    the historical last-write-wins totals across artifacts.
    """
    count_lines, scene_count, shot_count = _collection_count_lines(data)
    lines = [
        f"\n{artifact}:",
        *count_lines,
        *_scene_preview_lines(data),
        *_shot_preview_lines(data),
        *_descriptive_field_lines(data),
    ]
    return lines, scene_count, shot_count


def _collection_count_lines(data: dict[str, Any]) -> tuple[list[str], int, int]:
    """One 'key: N items' line per list-valued collection key, with tallies.

    The scene and shot counts are -1 when their underlying key is absent so
    callers can reproduce the historical last-write-wins totals across
    artifacts.
    """
    lines: list[str] = []
    scene_count = -1
    shot_count = -1
    for key in ("scenes", "scene_list", "rows", "shot_count"):
        val = data.get(key)
        if isinstance(val, list):
            lines.append(f"  {key}: {len(val)} items")
            if key == "scenes":
                scene_count = len(val)
            elif key == "rows":
                shot_count = len(val)
    return lines, scene_count, shot_count


def _scene_preview_lines(data: dict[str, Any]) -> list[str]:
    """First five scenes as '<scene_id>: <truncated dramatic_function>'."""
    lines: list[str] = []
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list):
        return lines
    for scene in scenes[:5]:
        if not isinstance(scene, dict):
            continue
        scene_id = scene.get("scene_id", "?")
        dramatic_function = str(scene.get("dramatic_function", ""))[:80]
        lines.append(f"  {scene_id}: {dramatic_function}")
    return lines


def _shot_preview_lines(data: dict[str, Any]) -> list[str]:
    """First five shots as '<shot_id>: <duration_seconds>s'."""
    lines: list[str] = []
    rows = data.get("rows", [])
    if not isinstance(rows, list):
        return lines
    for row in rows[:5]:
        if not isinstance(row, dict):
            continue
        shot_id = row.get("shot_id", "?")
        duration_seconds = row.get("duration_seconds", "?")
        lines.append(f"  {shot_id}: {duration_seconds}s")
    return lines


def _descriptive_field_lines(data: dict[str, Any]) -> list[str]:
    """Truncated string or list values of the artifact's descriptive fields."""
    lines: list[str] = []
    for key in ("text", "theme", "themes", "title"):
        val = data.get(key)
        if isinstance(val, str) and val:
            lines.append(f"  {key}: {val[:150]}")
        elif isinstance(val, list):
            lines.append(f"  {key}: {', '.join(str(x)[:60] for x in val[:3])}")
    return lines


def _metrics_summary(target: int, scenes: int, shots: int) -> str:
    """Structural pacing metrics derived from counted scenes/shots."""
    metrics_parts: list[str] = []
    if scenes:
        avg_scene = target / max(scenes, 1)
        metrics_parts.append(
            f"scene_count: {scenes} (~{avg_scene:.0f}s per scene for {target}s target)"
        )
    if shots:
        metrics_parts.append(f"shot_count: {shots}")
    if shots and scenes:
        metrics_parts.append(f"shots_per_scene: {shots / max(scenes, 1):.1f}")
    return "\n".join(metrics_parts) if metrics_parts else "(no metrics)"


def _consistency_warnings_text(state: dict[str, Any]) -> str:
    """Joined consistency warnings, truncated past 800 chars."""
    warnings = state.get("consistency_warnings", [])
    if not warnings:
        return "(none)"
    text = "\n".join(str(w)[:200] for w in (warnings if isinstance(warnings, list) else []))
    if len(text) > 800:
        return text[:800] + "..."
    return text


def _apply_phase_output_sections(state: dict[str, Any], ctx: dict[str, str]) -> None:
    """Fill phase output summary, metrics, and warnings sections in place.

    No-op when services are unavailable so the placeholder defaults survive.
    """
    services = _get_services(state)
    if services is None:
        return
    project_id = str(state.get("project_id", ""))
    phase = FilmPhase(ctx["current_phase"])
    lines: list[str] = []
    total_scenes = 0
    total_shots = 0
    for artifact, data in _load_phase_artifacts(services, project_id, phase):
        artifact_lines, scene_count, shot_count = _summarize_phase_artifact(artifact, data)
        lines.extend(artifact_lines)
        if scene_count >= 0:
            total_scenes = scene_count
        if shot_count >= 0:
            total_shots = shot_count
    ctx["phase_output_summary"] = "\n".join(lines) if lines else "(no artifacts produced)"
    ctx["metrics_summary"] = _metrics_summary(
        int(ctx["target_runtime_seconds"]), total_scenes, total_shots
    )
    ctx["consistency_warnings"] = _consistency_warnings_text(state)


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
            try:
                parsed = _ArtifactRef.from_string(ref)
            except ValueError:
                continue
            built_from[parsed.artifact_id] = ref
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
    try:
        return _ArtifactType(_ARTIFACT_TYPE_BY_CLASS.get(class_name, "script"))
    except ValueError:
        return _ArtifactType.SCRIPT


def _parse_ref(ref_str: str) -> _ArtifactRef:
    """Parse the canonical ``artifact:<phase>:<id>:v<N>`` ref string."""
    return _ArtifactRef.from_string(ref_str)


_UPSTREAM_CONTENT_SOURCES: dict[str, tuple[str, str]] = {
    "constitution_ref": ("constitution", "constitution_content"),
    "treatment_ref": ("development", "treatment_content"),
    "scene_list_ref": ("development", "scene_list_content"),
    "story_bible_ref": ("script", "story_bible_content"),
    "script_ref": ("script", "script_content"),
    "shot_matrix_ref": ("shot_bible", "shot_matrix_content"),
    "visual_refs": ("visual_dev", "visual_refs_content"),
    "execution_brief_ref": ("shot_bible", "execution_brief_content"),
}


def _inject_artifact_context(
    state: dict[str, Any],
    services: GraphServices,
    context_vars: dict[str, str],
) -> None:
    """Load upstream artifact content into prompt context to preserve continuity."""
    project_id = str(state.get("project_id", ""))
    if not project_id:
        return

    for ref_key, (_phase_name, content_key) in _UPSTREAM_CONTENT_SOURCES.items():
        ref = str(state.get(ref_key, "") or "").strip()
        if not ref:
            continue
        try:
            context_vars[content_key] = _compact_upstream_content(state, services, project_id, ref)
        except (FileNotFoundError, ValueError, KeyError) as exc:
            _record_context_load_failure(state, ref_key, ref, exc)
            continue


def _compact_upstream_content(
    state: dict[str, Any],
    services: GraphServices,
    project_id: str,
    ref: str,
) -> str:
    """Load one upstream artifact and compact it to the configured char budget."""
    parsed = _parse_ref(ref)
    data = services.artifact_store.load(
        project_id,
        FilmPhase(parsed.phase),
        parsed.artifact_id,
        parsed.version,
    )
    return compact_json_context(data, max_chars=_artifact_context_max_chars(state))


def _record_context_load_failure(
    state: dict[str, Any],
    ref_key: str,
    ref: str,
    exc: Exception,
) -> None:
    # Upstream context a phase cannot do good work without. If one of these refs
    # is set but failed to load, the agent ran context-blind (a hidden cause of
    # weak output) — do NOT swallow silently: log it and record the failure so
    # the phase gate can block.
    _logger.warning(
        "Could not load upstream artifact for prompt context: %s=%s (%s)",
        ref_key,
        ref,
        exc,
    )
    failures = state.setdefault("_context_load_failures", [])
    if ref_key not in failures:
        failures.append(ref_key)


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
    if isinstance(budget, dict):
        for key in ("project_cap_usd", "max_total_usd"):
            value = budget.get(key)
            if value is not None:
                context_vars["budget_cap"] = str(value)
                break
    preferred = _preferred_providers(resolved_config.get("providers", {}))
    if preferred:
        context_vars["preferred_providers"] = ", ".join(preferred)


def _preferred_providers(providers: Any) -> list[str]:
    """Ordered provider ids from config: explicit order list, else video entries."""
    if not isinstance(providers, dict):
        return []
    order = providers.get("order", [])
    if isinstance(order, list):
        return [str(item) for item in order if str(item)]
    video = providers.get("video")
    if isinstance(video, list):
        return [
            str(entry.get("provider_id", ""))
            for entry in video
            if isinstance(entry, dict) and str(entry.get("provider_id", ""))
        ]
    return []


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
