"""Orchestrator structural validators — Gates A, B, and C.

These run at phase boundaries to enforce film-level invariants:
- Gate A (shot_bible): shot-count per movement, runtime totals
- Gate B (gen_planning): field completeness, non-placeholder cost estimates
- Gate C (generation): dispatch readiness — real clip counts, executable requests

On failure they append blocking issues to ``state["issues"]``, which the
router's ``compute_actions()`` already handles via the ``handle_blockers``
path. No new router tier needed.
"""

from __future__ import annotations

from typing import Any

from film_pipeline.schemas._base import IssueSeverity
from film_pipeline.schemas.execution_brief import ExecutionBrief


def _blocking(code: str, message: str) -> dict[str, Any]:
    return {"severity": IssueSeverity.BLOCKING.value, "code": code, "message": message}


def _row_attr(row: Any, key: str, default: Any = None) -> Any:
    """Read a field from a row, handling both dict and object rows.

    Gate validators receive rows that may be Pydantic models (from mock
    executions) or plain dicts (from artifact store deserialization).
    ``getattr`` only works on objects; dicts need ``.get()``.
    """
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


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


# ── Gate S: Prep structural checks (development + script) ──────────────────


def _blocking_with_id(issue_id: str, code: str, message: str) -> dict[str, Any]:
    return {
        "issue_id": issue_id,
        "severity": IssueSeverity.BLOCKING.value,
        "code": code,
        "message": message,
    }


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


def validate_shot_structure(
    _state: dict[str, Any],
    brief: ExecutionBrief,
    shot_matrix: Any,
) -> list[dict[str, Any]]:
    """Gate A: Check shot count per movement and runtime totals.

    Returns a list of blocking issues (empty list = pass).
    """
    issues: list[dict[str, Any]] = []

    # Unpack shot matrix rows
    rows: list[Any] = []
    if hasattr(shot_matrix, "rows"):
        rows = shot_matrix.rows
    elif isinstance(shot_matrix, dict):
        raw = shot_matrix.get("rows", [])
        rows = raw if isinstance(raw, list) else []

    if not rows:
        issues.append(
            _blocking(
                "shot_matrix_empty",
                "Shot matrix has zero rows. Cannot validate structure.",
            )
        )
        return issues

    # --- Check shot count per movement ---
    # Group rows by act_id (maps to movement_id)
    act_counts: dict[str, int] = {}
    for row in rows:
        act_id = str(_row_attr(row, "act_id", "") or "")
        if not act_id:
            continue
        act_counts[act_id] = act_counts.get(act_id, 0) + 1

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

    # --- Check runtime totals ---
    total_duration = 0
    for row in rows:
        dur = _row_attr(row, "duration_seconds", 0)
        if isinstance(dur, (int, float)):
            total_duration += int(dur)

    target = brief.target_runtime_seconds
    tolerance = target * 0.10  # 10% tolerance
    if abs(total_duration - target) > tolerance:
        issues.append(
            _blocking(
                "runtime_mismatch",
                f"Target runtime is {target}s, but shot durations sum to "
                f"{total_duration}s (tolerance ±{tolerance:.0f}s). "
                "Shot durations must match the execution brief within 10%.",
            )
        )

    return issues


# ── Gate B: Generation planning completeness ──────────────────────────────


def validate_planning_completeness(
    _state: dict[str, Any],
    shot_matrix: Any,
    cost_estimate: Any,
) -> list[dict[str, Any]]:
    """Gate B: Check field completeness and non-placeholder cost estimates.

    Returns a list of blocking issues (empty list = pass).
    """
    issues: list[dict[str, Any]] = []

    # Unpack rows
    rows: list[Any] = []
    if hasattr(shot_matrix, "rows"):
        rows = shot_matrix.rows
    elif isinstance(shot_matrix, dict):
        raw = shot_matrix.get("rows", [])
        rows = raw if isinstance(raw, list) else []

    # --- Check field completeness per row ---
    # prompt_ref is filled BY gen_planning (via matrix patch), not a prerequisite.
    REQUIRED_FIELDS = [
        ("characters", "characters"),
        ("environment", "environment"),
        ("camera_profile", "camera_profile"),
    ]

    incomplete_rows: list[str] = []
    for row in rows:
        shot_id = str(_row_attr(row, "shot_id", "?") or "?")
        missing: list[str] = []
        for field_name, display_name in REQUIRED_FIELDS:
            value = _row_attr(row, field_name, None)
            if value is None or (isinstance(value, (str, list)) and not value):
                missing.append(display_name)
        if missing:
            incomplete_rows.append(f"{shot_id}: missing {', '.join(missing)}")

    if incomplete_rows:
        issues.append(
            _blocking(
                "incomplete_shot_rows",
                f"{len(incomplete_rows)} shot row(s) have missing generation-critical "
                f"fields: {'; '.join(incomplete_rows[:5])}"
                + ("..." if len(incomplete_rows) > 5 else ""),
            )
        )

    # --- Check cost estimate is non-placeholder ---
    if cost_estimate is not None:
        clip_count: int = 0
        total_cost: float = 0.0
        if hasattr(cost_estimate, "clip_count"):
            clip_count = int(getattr(cost_estimate, "clip_count", 0) or 0)
        elif isinstance(cost_estimate, dict):
            raw_count = cost_estimate.get("clip_count", cost_estimate.get("total_clips", 0))
            clip_count = int(raw_count) if raw_count is not None else 0
        if hasattr(cost_estimate, "estimated_cost_usd"):
            total_cost = float(getattr(cost_estimate, "estimated_cost_usd", 0.0) or 0.0)
        elif isinstance(cost_estimate, dict):
            raw_cost = cost_estimate.get(
                "estimated_cost_usd",
                cost_estimate.get("total_cost_usd", cost_estimate.get("total_cost", 0.0)),
            )
            total_cost = float(raw_cost) if raw_cost is not None else 0.0

        if clip_count == 0:
            issues.append(
                _blocking(
                    "zero_clip_count",
                    "Generation plan has 0 clips. Cannot dispatch to provider.",
                )
            )

        if total_cost == 0.0 and clip_count > 0:
            issues.append(
                _blocking(
                    "placeholder_cost",
                    "Generation plan has non-zero clips but $0.00 estimated cost. "
                    "Cost estimate must reflect real provider pricing.",
                )
            )
    else:
        issues.append(
            _blocking(
                "missing_cost_estimate",
                "No cost estimate produced by generation planning. "
                "Cannot validate dispatch readiness.",
            )
        )

    return issues


def validate_shot_scene_references(
    script: Any,
    shot_matrix: Any,
) -> list[dict[str, Any]]:
    """Ensure every shot row references a scene that exists in the script."""
    scene_ids = _extract_scene_ids(script)
    rows = _extract_rows(shot_matrix)
    if not scene_ids or not rows:
        return []

    missing: list[str] = []
    for row in rows:
        scene_id = str(_row_attr(row, "scene_id", "") or "")
        shot_id = str(_row_attr(row, "shot_id", "?") or "?")
        if scene_id and scene_id not in scene_ids:
            missing.append(f"{shot_id}->{scene_id}")

    if not missing:
        return []
    return [
        _blocking(
            "shot_scene_reference_mismatch",
            f"{len(missing)} shot row(s) reference scenes that do not exist in the script: "
            f"{', '.join(missing[:8])}" + ("..." if len(missing) > 8 else ""),
        )
    ]


def _extract_rows(value: Any) -> list[Any]:
    """Return row-like values from a matrix object or dict."""
    if hasattr(value, "rows"):
        rows = value.rows
        return list(rows) if isinstance(rows, list) else []
    if isinstance(value, dict):
        rows = value.get("rows", [])
        return rows if isinstance(rows, list) else []
    return []


def _extract_scene_ids(script: Any) -> set[str]:
    """Extract scene IDs from Script/StoryBible-like objects and dicts."""
    if hasattr(script, "scenes"):
        scenes = script.scenes
        return {
            str(_row_attr(scene, "scene_id", ""))
            for scene in scenes
            if str(_row_attr(scene, "scene_id", ""))
        }
    if not isinstance(script, dict):
        return set()

    candidates: list[Any] = []
    raw_scenes = script.get("scenes", [])
    if isinstance(raw_scenes, list):
        candidates.extend(raw_scenes)
    scene_list = script.get("scene_list", {})
    if isinstance(scene_list, dict):
        nested = scene_list.get("scenes", [])
        if isinstance(nested, list):
            candidates.extend(nested)
    return {
        str(_row_attr(scene, "scene_id", ""))
        for scene in candidates
        if str(_row_attr(scene, "scene_id", ""))
    }


# ── Gate C: Dispatch readiness ────────────────────────────────────────────


def validate_dispatch_readiness(
    _state: dict[str, Any],
    generation_requests: Any,
) -> list[dict[str, Any]]:
    """Gate C: Check that generation requests are dispatchable.

    Returns a list of blocking issues (empty list = pass).
    """
    issues: list[dict[str, Any]] = []

    if generation_requests is None:
        issues.append(
            _blocking(
                "no_generation_requests",
                "No generation requests exist. Cannot dispatch to provider.",
            )
        )
        return issues

    requests: list[Any] = []
    if isinstance(generation_requests, list):
        requests = generation_requests
    elif hasattr(generation_requests, "requests"):
        requests = getattr(generation_requests, "requests", [])
    elif isinstance(generation_requests, dict):
        reqs = generation_requests.get(
            "requests", generation_requests.get("generation_requests", [])
        )
        if isinstance(reqs, list):
            requests = reqs

    if not requests:
        issues.append(
            _blocking(
                "empty_generation_requests",
                "Generation requests list is empty. Nothing to dispatch.",
            )
        )
        return issues

    # Check each request has minimum dispatchable fields
    undispatchable: list[str] = []
    for i, req in enumerate(requests):
        shot_id = "?"
        if isinstance(req, dict):
            shot_id = str(req.get("shot_id", req.get("clip_id", f"request_{i}")))
            has_provider = bool(req.get("provider"))
            has_model = bool(req.get("model"))
            prompt_val = req.get("prompt")
            payload_val = req.get("prompt_payload")
            has_prompt = prompt_val is not None or payload_val is not None
        else:
            shot_id = str(_row_attr(req, "shot_id", f"request_{i}"))
            has_provider = bool(_row_attr(req, "provider", None))
            has_model = bool(_row_attr(req, "model", None))
            prompt_val = _row_attr(req, "prompt", None)
            payload_val = _row_attr(req, "prompt_payload", None)
            has_prompt = prompt_val is not None or payload_val is not None

        if not (has_provider and has_model and has_prompt):
            undispatchable.append(shot_id)

    if undispatchable:
        issues.append(
            _blocking(
                "undispatchable_requests",
                f"{len(undispatchable)} request(s) are not dispatchable "
                f"(missing provider, model, or prompt): "
                f"{', '.join(undispatchable[:5])}" + ("..." if len(undispatchable) > 5 else ""),
            )
        )

    return issues
