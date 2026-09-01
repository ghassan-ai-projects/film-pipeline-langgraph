"""Gate S and Gate A: prep structural checks and shot-bible structure."""

from __future__ import annotations

from typing import Any

from film_pipeline.graph.orchestrator_validators._shared import (
    _blocking,
    _blocking_with_id,
    _extract_rows,
    _row_attr,
)
from film_pipeline.schemas.execution_brief import ExecutionBrief


def validate_scene_count(state: dict[str, Any], scene_count: int) -> list[dict[str, Any]]:
    """Gate S (development): scene count must meet the Scope Contract floor.

    Directly targets the "not enough scenes" symptom: the development phase can
    no longer pass with a thin scene list when the contract demands more.
    """
    min_scenes = int(state.get("min_scene_count", 0) or 0)
    target = int(state.get("target_scene_count", 0) or 0)
    runtime = int(state.get("target_runtime_seconds", 0) or 0)
    if min_scenes and scene_count < min_scenes:
        return [
            _blocking_with_id(
                "gate_s_scene_floor",
                "scene_count_below_floor",
                f"Development produced {scene_count} scenes, but the Scope Contract "
                f"requires at least {min_scenes} (target {target}) for the {runtime}s "
                "runtime. Add scenes that earn their place until the floor is met.",
            )
        ]
    return []


def validate_script_scene_preservation(
    state: dict[str, Any],
    script_scene_count: int,
    development_scene_count: int,
) -> list[dict[str, Any]]:
    """Gate S (script): the script must not silently drop or under-fill scenes."""
    issues: list[dict[str, Any]] = []
    min_scenes = int(state.get("min_scene_count", 0) or 0)
    if development_scene_count and script_scene_count < development_scene_count:
        issues.append(
            _blocking_with_id(
                "gate_s_script_dropped",
                "script_dropped_scenes",
                f"Script has {script_scene_count} scenes but the approved development "
                f"scene list has {development_scene_count}. Every scene intent must "
                "become at least one script scene — none may be dropped or merged away.",
            )
        )
    if min_scenes and script_scene_count < min_scenes:
        issues.append(
            _blocking_with_id(
                "gate_s_script_floor",
                "script_below_floor",
                f"Script has {script_scene_count} scenes, below the Scope Contract "
                f"floor of {min_scenes}.",
            )
        )
    return issues


# ── Gate A: Shot bible structural check ───────────────────────────────────


def _movement_count_issues(
    brief: ExecutionBrief,
    rows: list[Any],
) -> list[dict[str, Any]]:
    """Check shot count per movement against the execution brief."""
    # Group rows by act_id (maps to movement_id)
    act_counts: dict[str, int] = {}
    for row in rows:
        act_id = str(_row_attr(row, "act_id", "") or "")
        if not act_id:
            continue
        act_counts[act_id] = act_counts.get(act_id, 0) + 1

    issues: list[dict[str, Any]] = []
    expected_act_ids = {movement.movement_id for movement in brief.movements}
    unexpected_act_ids = sorted(set(act_counts) - expected_act_ids)
    if unexpected_act_ids:
        issues.append(
            _blocking(
                "unexpected_act_ids",
                "Shot matrix contains act IDs not defined by the execution brief: "
                f"{', '.join(unexpected_act_ids)}.",
            )
        )
    for movement in brief.movements:
        actual = act_counts.get(movement.movement_id, 0)
        expected = movement.shot_count
        if actual != expected:
            issues.append(
                _blocking(
                    "shot_count_mismatch",
                    f"Movement '{movement.movement_id}': expected {expected} shots, "
                    f"got {actual}. Shot matrix does not match the execution brief.",
                )
            )
    return issues


def _runtime_tolerance_issues(
    brief: ExecutionBrief,
    rows: list[Any],
) -> list[dict[str, Any]]:
    """Check total shot duration against the target runtime within 10%."""
    total_duration = 0
    for row in rows:
        dur = _row_attr(row, "duration_seconds", 0)
        if isinstance(dur, (int, float)):
            total_duration += int(dur)

    target = brief.target_runtime_seconds
    tolerance = target * 0.10  # 10% tolerance
    if abs(total_duration - target) > tolerance:
        return [
            _blocking(
                "runtime_mismatch",
                f"Target runtime is {target}s, but shot durations sum to "
                f"{total_duration}s (tolerance ±{tolerance:.0f}s). "
                "Shot durations must match the execution brief within 10%.",
            )
        ]
    return []


def validate_shot_structure(
    _state: dict[str, Any],
    brief: ExecutionBrief,
    shot_matrix: Any,
) -> list[dict[str, Any]]:
    """Gate A: Check shot count per movement and runtime totals.

    Returns a list of blocking issues (empty list = pass).
    """
    rows = _extract_rows(shot_matrix)
    if not rows:
        return [
            _blocking(
                "shot_matrix_empty",
                "Shot matrix has zero rows. Cannot validate structure.",
            )
        ]

    issues: list[dict[str, Any]] = []
    issues.extend(_movement_count_issues(brief, rows))
    issues.extend(_runtime_tolerance_issues(brief, rows))
    return issues
