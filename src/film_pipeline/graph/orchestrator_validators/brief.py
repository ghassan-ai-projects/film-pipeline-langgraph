"""ExecutionBrief loading and cross-validation against the StoryBible."""

from __future__ import annotations

from typing import Any

from film_pipeline.graph.orchestrator_validators._shared import (
    _blocking,
)
from film_pipeline.schemas.execution_brief import ExecutionBrief

# ── Helpers: load ExecutionBrief from state or artifact store ─────────────


def _load_brief_from_state(state: dict[str, Any]) -> ExecutionBrief | None:
    """Try to load the ExecutionBrief from orchestrator state cache first."""
    from film_pipeline.graph.orchestrator_state import get_execution_brief

    return get_execution_brief(state)


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
    try:
        data = services.artifact_store.load(project_id, FilmPhase.SHOT_BIBLE, "execution_brief", 1)
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


def validate_execution_brief(
    state: dict[str, Any],
    brief: ExecutionBrief,
) -> list[dict[str, Any]]:
    """Cross-validate the ExecutionBrief against the StoryBible and Script.

    Ensures the extracted brief is internally consistent and matches the
    actual story structure. Returns blocking issues if the brief is
    mathematically impossible or contradicts the StoryBible.
    """
    issues: list[dict[str, Any]] = []

    # 1. Act count must match StoryBible (always 3 acts: setup/confrontation/resolution)
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

    # 2. Runtime self-consistency: total shots * avg_duration ~= target_runtime
    total_shots = sum(m.shot_count for m in brief.movements)
    if total_shots == 0:
        issues.append(
            _blocking(
                "brief_zero_shots",
                "ExecutionBrief has zero shots across all movements.",
            )
        )
        return issues

    from film_pipeline.graph.scope_contract import avg_shot_duration_for

    avg_duration = avg_shot_duration_for(brief.pacing_style)
    estimated_runtime = total_shots * avg_duration
    target = brief.target_runtime_seconds
    tolerance = target * 0.20  # 20% tolerance for estimated runtime

    if abs(estimated_runtime - target) > tolerance:
        issues.append(
            _blocking(
                "brief_runtime_inconsistent",
                f"ExecutionBrief runtime ({target}s) is inconsistent with "
                f"{total_shots} shots at {brief.pacing_style} pacing "
                f"(estimated ~{estimated_runtime:.0f}s, tolerance ±{tolerance:.0f}s). "
                "Either adjust shot counts or target_runtime_seconds.",
            )
        )

    # 3. Check mandatory anchors — at minimum, there should be some
    if not brief.mandatory_anchors:
        issues.append(
            _blocking(
                "brief_no_anchors",
                "ExecutionBrief has no mandatory anchors. "
                "At minimum, the main character(s) must be listed.",
            )
        )

    # 4. Load StoryBible from state and cross-check act structure
    story_bible_ref = str(state.get("story_bible_ref", ""))
    if story_bible_ref:
        from film_pipeline.graph.nodes import _get_services, _parse_ref
        from film_pipeline.schemas._base import FilmPhase

        services = _get_services(state)
        if services is not None:
            try:
                parsed = _parse_ref(story_bible_ref)
                bible_data = services.artifact_store.load(
                    str(state.get("project_id", "")),
                    FilmPhase.SCRIPT,
                    parsed.artifact_id,
                    parsed.version,
                )
                if isinstance(bible_data, dict):
                    act_map = bible_data.get("act_map", {})
                    if isinstance(act_map, dict):
                        act_count = sum(
                            1
                            for k in ("act1_setup", "act2_confrontation", "act3_resolution")
                            if act_map.get(k)
                        )
                        if act_count > 0 and len(brief.movements) != act_count:
                            issues.append(
                                _blocking(
                                    "brief_act_count_mismatch",
                                    f"StoryBible has {act_count} non-empty acts but "
                                    f"ExecutionBrief defines {len(brief.movements)} movements. "
                                    "Movement count must match act count.",
                                )
                            )

                    scene_list = bible_data.get("scene_list", {})
                    if isinstance(scene_list, dict):
                        scenes = scene_list.get("scenes", [])
                        actual_scene_count = len(scenes) if isinstance(scenes, list) else 0
                        if actual_scene_count > 0 and total_shots < actual_scene_count:
                            issues.append(
                                _blocking(
                                    "brief_shots_less_than_scenes",
                                    f"StoryBible has {actual_scene_count} scenes but "
                                    f"ExecutionBrief allocates only {total_shots} shots. "
                                    "Each scene needs at least one shot.",
                                )
                            )
            except (FileNotFoundError, ValueError, KeyError):
                pass

    return issues
