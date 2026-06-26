"""Phase-specific context packets — scoped data for agent prompts.

Each builder returns a compact structured string containing only the data that
phase's agent needs. Replaces loading ALL artifacts and truncating at 6000 chars.
"""

from __future__ import annotations

from typing import Any


def build_constitution_context(state: dict[str, Any]) -> str:
    """Constitution phase: just the idea and classification."""
    idea = str(state.get("idea", ""))
    film_type = str(state.get("film_type", ""))
    target = state.get("target_runtime_seconds", 0)
    return (
        f"Film idea: {idea}\n"
        f"Film type: {film_type}\n"
        f"Target runtime: {target}s\n"
        f"Project ID: {state.get('project_id', '')}"
    )


def build_development_context(state: dict[str, Any], services: Any) -> str:
    """Development phase: constitution summary + target runtime."""
    parts: list[str] = []
    constitution_ref = state.get("constitution_ref", "")
    if constitution_ref:
        data = _load_ref(state, services, constitution_ref)
        if data:
            parts.append(
                f"Constitution theme: {data.get('theme', '')}\nTone: {data.get('tone', '')}"
            )
    target = state.get("target_runtime_seconds", 0)
    film_type = str(state.get("film_type", ""))
    parts.append(f"Target runtime: {target}s | Film type: {film_type}")
    return "\n\n".join(parts)


def build_script_context(state: dict[str, Any], services: Any) -> str:
    """Script phase: treatment summary + scene list count + constitution style."""
    parts: list[str] = []
    treatment_ref = state.get("treatment_ref", "")
    if treatment_ref:
        data = _load_ref(state, services, treatment_ref)
        if data:
            themes = data.get("themes", [])
            act_map = data.get("act_map", {})
            parts.append(
                f"Treatment themes: {', '.join(themes)}\nAct structure: {list(act_map.keys())}"
            )
    scene_list_ref = state.get("scene_list_ref", "")
    if scene_list_ref:
        data = _load_ref(state, services, scene_list_ref)
        if data:
            scenes = data.get("scenes", [])
            parts.append(f"Scene count: {len(scenes)}")
    return "\n\n".join(parts)


def build_visual_dev_context(state: dict[str, Any], services: Any) -> str:
    """Visual dev phase: script scene count + constitution style."""
    parts: list[str] = []
    constitution_ref = state.get("constitution_ref", "")
    if constitution_ref:
        data = _load_ref(state, services, constitution_ref)
        if data:
            parts.append(
                f"Visual language: {data.get('visual_language', '')}\n"
                f"Camera philosophy: {data.get('camera_philosophy', '')}"
            )
    script_ref = state.get("script_ref", "")
    if script_ref:
        data = _load_ref(state, services, script_ref)
        if data:
            scenes = data.get("scenes", [])
            parts.append(f"Script scenes: {len(scenes)}")
    target = state.get("target_runtime_seconds", 0)
    film_type = str(state.get("film_type", ""))
    parts.append(f"Target runtime: {target}s | Film type: {film_type}")
    return "\n\n".join(parts)


def build_shot_bible_context(state: dict[str, Any], services: Any) -> str:
    """Shot bible phase: execution brief summary + script scene list.

    Does NOT load the full matrix (it doesn't exist yet in this phase).
    """
    parts: list[str] = []
    brief_ref = state.get("execution_brief_ref", "")
    if brief_ref:
        data = _load_ref(state, services, brief_ref)
        if data:
            movements = data.get("movements", [])
            parts.append(
                f"Execution brief — {data.get('target_runtime_seconds', '?')}s, "
                f"{data.get('pacing_style', '?')}\n"
                + "\n".join(
                    f"  {m.get('movement_id', '?')}: {m.get('shot_count', 0)} shots "
                    f"({m.get('duration_range_seconds', [0, 0])})"
                    for m in movements
                )
                + f"\n  Mandatory anchors: {data.get('mandatory_anchors', [])}"
                + f"\n  Environment progression: {data.get('environment_progression', [])}"
            )
    script_ref = state.get("script_ref", "")
    if script_ref:
        data = _load_ref(state, services, script_ref)
        if data:
            scenes = data.get("scenes", [])
            parts.append(f"Script has {len(scenes)} scenes across 3 acts")
    return "\n\n".join(parts)


def build_gen_planning_context(state: dict[str, Any], services: Any) -> str:
    """Gen planning phase: row count summary + budget + provider policy."""
    parts: list[str] = []
    matrix_ref = state.get("shot_matrix_ref", "")
    if matrix_ref:
        data = _load_ref(state, services, matrix_ref)
        if data:
            rows = data.get("rows", [])
            acts: dict[str, int] = {}
            for r in rows:
                act = str(r.get("act_id", "?"))
                acts[act] = acts.get(act, 0) + 1
            parts.append(
                f"Shot matrix: {len(rows)} rows across {len(acts)} acts\n"
                + "\n".join(f"  {k}: {v} rows" for k, v in sorted(acts.items()))
            )
    budget = state.get("budget_snapshot", {})
    cap = budget.get("cap_usd", 0) if isinstance(budget, dict) else 0
    parts.append(f"Budget cap: ${cap}")
    return "\n\n".join(parts)


def _load_ref(state: dict[str, Any], services: Any, ref: str) -> dict[str, Any] | None:
    """Load an artifact's content by ref string. Returns None on failure."""
    parts = ref.split(":")
    if len(parts) < 3:
        return None
    artifact_id = parts[1]
    try:
        version = int(parts[2].lstrip("v"))
    except ValueError:
        return None
    # Try common phase directories
    from film_pipeline.schemas._base import FilmPhase

    for phase in FilmPhase:
        try:
            result: dict[str, Any] = services.artifact_store.load(
                str(state.get("project_id", "")), phase, artifact_id, version
            )
            return result
        except (FileNotFoundError, ValueError):
            continue
    return None


# Map phase → context builder
PHASE_BUILDERS: dict[str, Any] = {
    "intake": build_constitution_context,
    "constitution": build_constitution_context,
    "development": build_development_context,
    "script": build_script_context,
    "visual_dev": build_visual_dev_context,
    "shot_bible": build_shot_bible_context,
    "gen_planning": build_gen_planning_context,
}
