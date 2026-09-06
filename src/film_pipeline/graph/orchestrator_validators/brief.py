"""ExecutionBrief loading and cross-validation against the StoryBible."""

from __future__ import annotations

from typing import Any

from film_pipeline.graph.orchestrator_validators._shared import (
    _blocking,
)
from film_pipeline.schemas.execution_brief import ExecutionBrief

# ── Helpers: load ExecutionBrief from state or artifact store ─────────────


def _load_brief_from_state(state: dict[str, Any]) -> ExecutionBrief | None:
    """Load the brief cached in orchestrator state, coerced to the model.

    ``set_execution_brief`` persists ``model_dump(mode="json")``, so live
    state holds a plain mapping once the brief crosses any node boundary.
    """
    from film_pipeline.graph.orchestrator_state import get_execution_brief

    data = get_execution_brief(state)
    if data is None:
        return None
    if isinstance(data, ExecutionBrief):
        return data
    if isinstance(data, dict):
        try:
            return ExecutionBrief(**data)
        except (TypeError, ValueError):
            return None
    return None


def _load_brief_from_store(state: dict[str, Any]) -> ExecutionBrief | None:
    """Load the ExecutionBrief from the artifact store."""
    from film_pipeline.graph.nodes import _get_services

    services = _get_services(state)
    if services is None:
        return None
    from film_pipeline.schemas._base import FilmPhase

    project_id = str(state.get("project_id", ""))
    if not project_id:
        return None
    ref = str(state.get("execution_brief_ref", "") or "")
    artifact_id = "execution_brief"
    version = 1
    parts = ref.split(":")
    if len(parts) >= 3 and parts[1]:
        artifact_id = parts[1]
        try:
            version = int(parts[2].removeprefix("v"))
        except ValueError:
            return None
    elif not ref:
        try:
            artifacts = services.artifact_store.list_artifacts(project_id, FilmPhase.SHOT_BIBLE)
            matches = [a for a in artifacts if a.artifact_id == "execution_brief"]
            if matches:
                version = max(a.version for a in matches)
        except (FileNotFoundError, OSError, ValueError):
            return None
    try:
        data = services.artifact_store.load(project_id, FilmPhase.SHOT_BIBLE, artifact_id, version)
        if isinstance(data, dict):
            return ExecutionBrief(**data)
    except (FileNotFoundError, ValueError, KeyError, TypeError):
        pass
    return None


def load_execution_brief(state: dict[str, Any]) -> ExecutionBrief | None:
    """Load the ExecutionBrief, trying state cache first, then artifact store."""
    brief = _load_brief_from_state(state)
    if brief is not None:
        return brief
    return _load_brief_from_store(state)


# ── Post-extraction: cross-validate ExecutionBrief against StoryBible ──────


def _movement_count_issues(brief: ExecutionBrief) -> list[dict[str, Any]]:
    """The StoryBible defines a 3-act structure; flag implausible movement counts."""
    issues: list[dict[str, Any]] = []
    if len(brief.movements) < 2:
        issues.append(
            _blocking(
                "brief_too_few_movements",
                f"ExecutionBrief has only {len(brief.movements)} movement(s). "
                "The StoryBible defines a 3-act structure. At least 2 movements required.",
            )
        )
    if len(brief.movements) > 5:
        issues.append(
            _blocking(
                "brief_too_many_movements",
                f"ExecutionBrief has {len(brief.movements)} movements. "
                "The StoryBible has a 3-act structure. More than 5 movements is suspicious.",
            )
        )
    return issues


def _runtime_inconsistency_issues(brief: ExecutionBrief, total_shots: int) -> list[dict[str, Any]]:
    """Runtime self-consistency: total shots * avg_duration ~= target_runtime."""
    from film_pipeline.graph.scope_contract import avg_shot_duration_for

    avg_duration = avg_shot_duration_for(brief.pacing_style)
    estimated_runtime = total_shots * avg_duration
    target = brief.target_runtime_seconds
    tolerance = target * 0.20  # 20% tolerance for estimated runtime

    if abs(estimated_runtime - target) <= tolerance:
        return []
    return [
        _blocking(
            "brief_runtime_inconsistent",
            f"ExecutionBrief runtime ({target}s) is inconsistent with "
            f"{total_shots} shots at {brief.pacing_style} pacing "
            f"(estimated ~{estimated_runtime:.0f}s, tolerance ±{tolerance:.0f}s). "
            "Either adjust shot counts or target_runtime_seconds.",
        )
    ]


def _act_structure_issues(bible_data: dict[str, Any], movement_count: int) -> list[dict[str, Any]]:
    """Flag a movement count that contradicts the StoryBible's act structure."""
    act_map = bible_data.get("act_map", {})
    if not isinstance(act_map, dict):
        return []
    act_count = sum(
        1 for k in ("act1_setup", "act2_confrontation", "act3_resolution") if act_map.get(k)
    )
    if not (act_count > 0 and movement_count != act_count):
        return []
    return [
        _blocking(
            "brief_act_count_mismatch",
            f"StoryBible has {act_count} non-empty acts but "
            f"ExecutionBrief defines {movement_count} movements. "
            "Movement count must match act count.",
        )
    ]


def _scene_coverage_issues(bible_data: dict[str, Any], total_shots: int) -> list[dict[str, Any]]:
    """Each scene needs at least one shot allocated by the brief."""
    scene_list = bible_data.get("scene_list", {})
    if not isinstance(scene_list, dict):
        return []
    scenes = scene_list.get("scenes", [])
    actual_scene_count = len(scenes) if isinstance(scenes, list) else 0
    if not (actual_scene_count > 0 and total_shots < actual_scene_count):
        return []
    return [
        _blocking(
            "brief_shots_less_than_scenes",
            f"StoryBible has {actual_scene_count} scenes but "
            f"ExecutionBrief allocates only {total_shots} shots. "
            "Each scene needs at least one shot.",
        )
    ]


def _story_bible_cross_check(
    state: dict[str, Any],
    brief: ExecutionBrief,
    total_shots: int,
) -> list[dict[str, Any]]:
    """Load the StoryBible from the artifact store and cross-check structure."""
    story_bible_ref = str(state.get("story_bible_ref", ""))
    if not story_bible_ref:
        return []
    from film_pipeline.graph.nodes import _get_services, _parse_ref
    from film_pipeline.schemas._base import FilmPhase

    services = _get_services(state)
    if services is None:
        return []
    try:
        parsed = _parse_ref(story_bible_ref)
        bible_data = services.artifact_store.load(
            str(state.get("project_id", "")),
            FilmPhase.SCRIPT,
            parsed.artifact_id,
            parsed.version,
        )
        cross_issues: list[dict[str, Any]] = []
        if isinstance(bible_data, dict):
            cross_issues.extend(_act_structure_issues(bible_data, len(brief.movements)))
            cross_issues.extend(_scene_coverage_issues(bible_data, total_shots))
        return cross_issues
    except (FileNotFoundError, ValueError, KeyError):
        pass
    return []


def validate_execution_brief(
    state: dict[str, Any],
    brief: ExecutionBrief,
) -> list[dict[str, Any]]:
    """Cross-validate the ExecutionBrief against the StoryBible and Script.

    Ensures the extracted brief is internally consistent and matches the
    actual story structure. Returns blocking issues if the brief is
    mathematically impossible or contradicts the StoryBible.
    """
    issues = _movement_count_issues(brief)

    total_shots = sum(m.shot_count for m in brief.movements)
    if total_shots == 0:
        issues.append(
            _blocking(
                "brief_zero_shots",
                "ExecutionBrief has zero shots across all movements.",
            )
        )
        return issues

    issues.extend(_runtime_inconsistency_issues(brief, total_shots))

    # Mandatory anchors — at minimum, there should be some.
    if not brief.mandatory_anchors:
        issues.append(
            _blocking(
                "brief_no_anchors",
                "ExecutionBrief has no mandatory anchors. "
                "At minimum, the main character(s) must be listed.",
            )
        )

    issues.extend(_story_bible_cross_check(state, brief, total_shots))
    return issues
