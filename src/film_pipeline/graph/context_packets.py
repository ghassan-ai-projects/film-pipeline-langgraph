"""Phase-specific context packets — scoped data for agent prompts.

Each builder returns a compact structured string containing only the data that
phase's agent needs. Replaces loading ALL artifacts and truncating at 6000 chars.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from film_pipeline.schemas._base import FilmPhase
    from film_pipeline.schemas.artifact import ArtifactRef


class _ArtifactLoader(Protocol):
    """Loads artifact bodies by coordinates or by ref."""

    def load(
        self, project_id: str, phase: FilmPhase, artifact_id: str, version: int
    ) -> dict[str, Any]: ...

    def load_ref(self, project_id: str, ref: str | ArtifactRef) -> dict[str, Any]: ...


class _ContextPacketSources(Protocol):
    """Services surface the packet builders need: an artifact loader."""

    @property
    def artifact_store(self) -> _ArtifactLoader: ...


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


def build_development_context(state: dict[str, Any], services: _ContextPacketSources) -> str:
    """Development phase: constitution summary + target runtime."""
    parts: list[str] = []
    constitution = _load_state_ref(state, services, "constitution_ref")
    if constitution:
        parts.append(
            f"Constitution theme: {constitution.get('theme', '')}\n"
            f"Tone: {constitution.get('tone', '')}"
        )
    parts.append(_render_target_and_type(state))
    return "\n\n".join(parts)


def build_script_context(state: dict[str, Any], services: _ContextPacketSources) -> str:
    """Script phase: treatment summary + scene list count + constitution style."""
    parts: list[str] = []
    treatment = _load_state_ref(state, services, "treatment_ref")
    if treatment:
        themes = treatment.get("themes", [])
        act_map = treatment.get("act_map", {})
        parts.append(
            f"Treatment themes: {', '.join(themes)}\nAct structure: {list(act_map.keys())}"
        )
    scene_list = _load_state_ref(state, services, "scene_list_ref")
    if scene_list:
        scenes = scene_list.get("scenes", [])
        parts.append(f"Scene count: {len(scenes)}")
    return "\n\n".join(parts)


def build_visual_dev_context(state: dict[str, Any], services: _ContextPacketSources) -> str:
    """Visual dev phase: script scene count + constitution style."""
    parts: list[str] = []
    constitution = _load_state_ref(state, services, "constitution_ref")
    if constitution:
        parts.append(
            f"Visual language: {constitution.get('visual_language', '')}\n"
            f"Camera philosophy: {constitution.get('camera_philosophy', '')}"
        )
    script = _load_state_ref(state, services, "script_ref")
    if script:
        scenes = script.get("scenes", [])
        parts.append(f"Script scenes: {len(scenes)}")
    parts.append(_render_target_and_type(state))
    return "\n\n".join(parts)


def build_shot_bible_context(state: dict[str, Any], services: _ContextPacketSources) -> str:
    """Shot bible phase: execution brief summary + script scene list.

    Does NOT load the full matrix (it doesn't exist yet in this phase).
    """
    parts: list[str] = []
    brief = _load_state_ref(state, services, "execution_brief_ref")
    if brief:
        parts.append(_summarize_execution_brief(brief))
    script = _load_state_ref(state, services, "script_ref")
    if script:
        scenes = script.get("scenes", [])
        parts.append(f"Script has {len(scenes)} scenes across 3 acts")
    return "\n\n".join(parts)


def build_gen_planning_context(state: dict[str, Any], services: _ContextPacketSources) -> str:
    """Gen planning phase: row count summary + budget + provider policy."""
    parts: list[str] = []
    matrix = _load_state_ref(state, services, "shot_matrix_ref")
    if matrix:
        rows = matrix.get("rows", [])
        rows_per_act = _count_rows_per_act(rows)
        parts.append(
            f"Shot matrix: {len(rows)} rows across {len(rows_per_act)} acts\n"
            + "\n".join(f"  {k}: {v} rows" for k, v in sorted(rows_per_act.items()))
        )
    budget = state.get("budget_snapshot", {})
    cap = budget.get("cap_usd", 0) if isinstance(budget, dict) else 0
    parts.append(f"Budget cap: ${cap}")
    return "\n\n".join(parts)


# Map phase → context builder
PHASE_BUILDERS: dict[str, Callable[..., str]] = {
    "intake": build_constitution_context,
    "constitution": build_constitution_context,
    "development": build_development_context,
    "script": build_script_context,
    "visual_dev": build_visual_dev_context,
    "shot_bible": build_shot_bible_context,
    "gen_planning": build_gen_planning_context,
}


def _render_target_and_type(state: dict[str, Any]) -> str:
    """Render the shared target-runtime / film-type summary line."""
    target = state.get("target_runtime_seconds", 0)
    film_type = str(state.get("film_type", ""))
    return f"Target runtime: {target}s | Film type: {film_type}"


def _summarize_execution_brief(data: dict[str, Any]) -> str:
    """Format an execution brief as header plus movement lines."""
    movements = data.get("movements", [])
    return (
        f"Execution brief — {data.get('target_runtime_seconds', '?')}s, "
        f"{data.get('pacing_style', '?')}\n"
        + "\n".join(
            f"  {movement.get('movement_id', '?')}: {movement.get('shot_count', 0)} shots "
            f"({movement.get('duration_range_seconds', [0, 0])})"
            for movement in movements
        )
        + f"\n  Mandatory anchors: {data.get('mandatory_anchors', [])}"
        + f"\n  Environment progression: {data.get('environment_progression', [])}"
    )


def _count_rows_per_act(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Count shot-matrix rows grouped by their act id."""
    counts: dict[str, int] = {}
    for row in rows:
        act = str(row.get("act_id", "?"))
        counts[act] = counts.get(act, 0) + 1
    return counts


def _load_state_ref(
    state: dict[str, Any], services: _ContextPacketSources, ref_key: str
) -> dict[str, Any] | None:
    """Load the artifact referenced at ``state[ref_key]``; None when unset or unloadable."""
    ref = state.get(ref_key, "")
    return _load_ref(state, services, ref) if ref else None


def _load_ref(
    state: dict[str, Any], services: _ContextPacketSources, ref: str
) -> dict[str, Any] | None:
    """Load an artifact's content by ref string. Returns None on failure."""
    try:
        return services.artifact_store.load_ref(str(state.get("project_id", "")), ref)
    except (FileNotFoundError, ValueError):
        return None
