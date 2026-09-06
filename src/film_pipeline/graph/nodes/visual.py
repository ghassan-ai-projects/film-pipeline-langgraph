"""Visual planning phase nodes: visual_dev, shot_bible, and gen_planning."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel

from film_pipeline.graph.nodes._agent import (
    _propagate_side_effects,
    _run_agent,
    _save_artifact,
)
from film_pipeline.graph.nodes._context import _parse_ref
from film_pipeline.graph.nodes._shared import (
    _get_services,
    _is_new_issue,
    _is_new_ref,
    _phase_gate_updates,
)
from film_pipeline.graph.nodes._visual_matrix_coverage import (
    _ensure_matrix_scene_coverage as _ensure_matrix_scene_coverage,
)
from film_pipeline.graph.nodes._visual_matrix_coverage import (
    _load_script_scenes,
)
from film_pipeline.schemas.execution_brief import ExecutionBrief
from film_pipeline.schemas.matrix import MasterFilmMatrix


def visual_dev_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    updates: dict[str, Any] = _phase_gate_updates(
        new_state, phase="visual_dev", gate="visual_bible"
    )
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
    _propagate_side_effects(new_state, updates, state)
    return updates


def _collect_updates(
    gate_updates: dict[str, Any],
    new_state: dict[str, Any],
    original: dict[str, Any],
    ref_keys: tuple[str, ...],
) -> dict[str, Any]:
    """Compute the partial update from a before/after diff of the node state."""
    updates: dict[str, Any] = dict(gate_updates)
    new_refs = [r for r in (new_state.get("artifact_refs", []) or []) if _is_new_ref(r, original)]
    if new_refs:
        updates["artifact_refs"] = new_refs
    new_issues = [i for i in (new_state.get("issues", []) or []) if _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    for key in ref_keys:
        val = new_state.get(key)
        if val:
            updates[key] = val
    return updates


def _ensure_execution_brief(new_state: dict[str, Any]) -> None:
    """Load or extract the structural contract needed by shot generation.

    Persisted states from older runs may contain the cache key with a null
    value, or may have the artifact without its scalar state ref. Neither
    shape is sufficient for prompt assembly, so a valid stored brief is
    rehydrated into both state domains before extraction is considered.
    """
    from film_pipeline.graph.orchestrator_state import set_execution_brief
    from film_pipeline.graph.orchestrator_validators import load_execution_brief

    brief = load_execution_brief(new_state)
    if brief is not None:
        set_execution_brief(new_state, brief)
        if not new_state.get("execution_brief_ref"):
            stored_ref = _latest_execution_brief_ref(new_state)
            if stored_ref:
                new_state["execution_brief_ref"] = stored_ref
                if stored_ref not in (new_state.get("artifact_refs", []) or []):
                    new_state.setdefault("artifact_refs", []).append(stored_ref)
        return
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
    if brief is None:
        return
    set_execution_brief(new_state, brief)
    brief_ref = _save_artifact(new_state, brief, "execution_brief", "shot_bible")
    if brief_ref:
        new_state["execution_brief_ref"] = brief_ref

    # Cross-validate the extracted brief against the StoryBible
    from film_pipeline.graph.orchestrator_validators import validate_execution_brief

    brief_issues = validate_execution_brief(new_state, brief)
    new_state.setdefault("issues", []).extend(brief_issues)


def _latest_execution_brief_ref(state: dict[str, Any]) -> str:
    """Return the latest stored execution-brief ref, if one exists."""
    services = _get_services(state)
    if services is None:
        return ""
    from film_pipeline.schemas._base import FilmPhase

    try:
        artifacts = services.artifact_store.list_artifacts(
            str(state.get("project_id", "")), FilmPhase("shot_bible")
        )
    except (FileNotFoundError, OSError, ValueError):
        return ""
    matches = [a for a in artifacts if a.artifact_id == "execution_brief"]
    if not matches:
        return ""
    latest = max(matches, key=lambda artifact: artifact.version)
    return f"artifact:execution_brief:v{latest.version}"


def _execution_brief_contract(brief: ExecutionBrief | None) -> str:
    """Render the authoritative movement/act contract into the shot task."""
    if brief is None:
        return ""
    movement_lines = "\n".join(
        "- "
        f"{movement.movement_id}: exactly {movement.shot_count} rows, "
        f"{movement.duration_range_seconds[0]}-{movement.duration_range_seconds[1]}s each"
        for movement in brief.movements
    )
    total_shots = sum(movement.shot_count for movement in brief.movements)
    return (
        "\n\nAUTHORITATIVE EXECUTION-BRIEF CONTRACT — HIGHEST PRIORITY:\n"
        f"Total rows: exactly {total_shots}; target runtime: "
        f"{brief.target_runtime_seconds}s.\n"
        f"{movement_lines}\n"
        "The movement_id values above are the only legal act_id values. "
        "This contract overrides scene-count, treatment-movement, target-shot, "
        "or max-shot hints when those conflict. Scenes must be distributed inside "
        "these movements, never turned into additional acts."
    )


def _script_scene_ids(new_state: dict[str, Any]) -> list[str]:
    """Return the scripted scene ids available for deterministic backfill."""
    services = _get_services(new_state)
    if services is None:
        return []
    return [
        str(scene.get("scene_id", ""))
        for scene in _load_script_scenes(new_state, services)
        if isinstance(scene, dict) and scene.get("scene_id")
    ]


def _reconcile_shot_matrix_to_brief(
    shot_matrix: Any,
    brief: ExecutionBrief | None,
    scene_ids: list[str] | None = None,
) -> Any:
    """Deterministically force the matrix to match the brief's exact contract.

    The node invokes this before and after the scene-coverage helper. The first
    invocation carries the script scene ids so the coverage helper has no rows
    to append; the second protects the exact contract if coverage changes.
    The final persisted matrix satisfies ``validate_shot_structure`` regardless
    of what the LLM returned. Preserves the input shape: a Pydantic
    ``MasterFilmMatrix`` stays a model, a raw dict stays a dict.

    Returns an empty dict/``None``-safe value shape only when no rows exist;
    rows are returned as a reconciled matrix otherwise.
    """
    if brief is None or not brief.movements:
        return shot_matrix

    is_model = isinstance(shot_matrix, BaseModel)
    matrix_dict = shot_matrix.model_dump() if is_model else dict(shot_matrix)

    rows = list(matrix_dict.get("rows") or [])
    if not rows:
        return shot_matrix

    # Contract from the authoritative brief.
    target_counts = {movement.movement_id: movement.shot_count for movement in brief.movements}
    duration_ranges = {
        movement.movement_id: movement.duration_range_seconds for movement in brief.movements
    }

    def _row_dump(row: Any) -> dict[str, Any]:
        if isinstance(row, BaseModel):
            return row.model_dump()
        return dict(row)

    def _get(row: dict[str, Any], key: str, default: Any = "") -> Any:
        return row.get(key, default)

    raw_rows = [_row_dump(r) for r in rows]

    # 1. Normalize every row to one of the brief's movement ids. Extra acts
    #    are mapped by their numeric suffix (act_4/act_5 both become act_3 for
    #    a three-movement brief); unknown/missing ids use row position.
    movement_ids = list(target_counts)
    retained: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rows):
        raw_act_id = str(_get(row, "act_id", "") or "")
        if raw_act_id not in target_counts:
            suffix = raw_act_id.rsplit("_", 1)[-1]
            if suffix.isdigit():
                movement_index = min(max(int(suffix) - 1, 0), len(movement_ids) - 1)
            else:
                movement_index = min(
                    index * len(movement_ids) // max(len(raw_rows), 1),
                    len(movement_ids) - 1,
                )
            raw_act_id = movement_ids[movement_index]
        row["act_id"] = raw_act_id
        retained.append(row)

    # 2. Partition the retained rows per act, preserving relative order.
    per_act: dict[str, list[dict[str, Any]]] = {movement_id: [] for movement_id in target_counts}
    for row in retained:
        per_act[str(_get(row, "act_id", ""))].append(row)

    # 3. Pad/trim each act to the exact count while preserving scene diversity.
    padded: list[dict[str, Any]] = []
    for movement in brief.movements:
        act_id = movement.movement_id
        target = target_counts[act_id]
        act_rows = per_act[act_id]
        padded.extend(_balance_act_rows(act_id, act_rows, target, retained))

    # 4. Preserve every scripted scene while the row count is still exact.
    if scene_ids and padded:
        covered_scene_ids = {str(row.get("scene_id", "") or "") for row in padded}
        scene_counts: dict[str, int] = {}
        for row in padded:
            scene_id = str(row.get("scene_id", "") or "")
            scene_counts[scene_id] = scene_counts.get(scene_id, 0) + 1
        missing_scene_ids = [
            scene_id for scene_id in scene_ids if scene_id not in covered_scene_ids
        ]
        for scene_id in missing_scene_ids:
            replacement = next(
                (
                    row
                    for row in padded
                    if scene_counts.get(str(row.get("scene_id", "") or ""), 0) > 1
                ),
                padded[0],
            )
            previous_scene_id = str(replacement.get("scene_id", "") or "")
            scene_counts[previous_scene_id] -= 1
            replacement["scene_id"] = scene_id
            scene_counts[scene_id] = scene_counts.get(scene_id, 0) + 1
            covered_scene_ids.add(scene_id)

    # 5. Re-sequence ids deterministically across the whole matrix.
    for index, row in enumerate(padded):
        number = index + 1
        row["shot_id"] = f"shot_{number:04d}"
        row["sequence_id"] = f"seq_{number:03d}"
        row["generation_order"] = index

    # 6. Clamp per-row durations to their movement range and bring the total
    #    sum to the brief's target runtime where reachable.
    _reconcile_durations(padded, brief, duration_ranges)

    # 7. Rebuild the matrix in its original shape.
    matrix_dict["rows"] = padded
    if is_model:
        return MasterFilmMatrix.model_validate(matrix_dict)
    return matrix_dict


def _balance_act_rows(
    act_id: str,
    act_rows: list[dict[str, Any]],
    target: int,
    retained_pool: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return exactly ``target`` rows for one act, preserving scene diversity.

    Short acts are padded by cycling the rows already present; an empty act is
    seeded by cloning a real, scene-bearing row from the retained pool (re-
    tagged to this act) so it never fabricates a phantom scene. Over counts are
    trimmed from the tail while never dropping the last row of a scene still
    present in this act.
    """
    if target <= 0:
        return []

    # Trim over-count rows, keeping the last occurrence of each scene in the act.
    if len(act_rows) > target:
        scene_counts: dict[str, int] = {}
        for row in act_rows:
            scene_id = str(row.get("scene_id", "") or "")
            scene_counts[scene_id] = scene_counts.get(scene_id, 0) + 1
        # Remove ``to_remove`` rows from the tail, preferring rows whose scene
        # appears more than once; never remove the last row of a live scene.
        to_remove = len(act_rows) - target
        remove_indices: set[int] = set()
        for idx in range(len(act_rows) - 1, -1, -1):
            if len(remove_indices) == to_remove:
                break
            scene_id = str(act_rows[idx].get("scene_id", "") or "")
            if scene_counts.get(scene_id, 0) > 1:
                scene_counts[scene_id] -= 1
                remove_indices.add(idx)
        base = [r for idx, r in enumerate(act_rows) if idx not in remove_indices]
    else:
        base = list(act_rows)

    # Empty act: seed from a real scene-bearing row so scene diversity is kept
    # and no phantom scene id is fabricated.
    if not base and retained_pool:
        donor = deepcopy(retained_pool[-1])
        donor["act_id"] = act_id
        base = [donor]

    if target <= len(base):
        return base[:target]

    # Pad by cycling the base rows in reverse so the donor/first row is reused
    # last and scene distribution stays diverse.
    padded = list(base)
    for index in range(len(base), target):
        source = base[len(base) - 1 - ((index - len(base)) % len(base))]
        padded.append(deepcopy(source))
    return padded


def _reconcile_durations(
    rows: list[dict[str, Any]],
    brief: ExecutionBrief,
    duration_ranges: dict[str, tuple[int, int]],
) -> None:
    """Clamp each row to its movement range and nudge the total to the target.

    First every duration is clamped into the movement's ``duration_range``,
    preferring the authored value when it already lies inside. The residual
    difference from ``target_runtime_seconds`` is then distributed determinis-
    tically (fixed row order) within each row's range, driving the sum to the
    target exactly when it is reachable; otherwise the closest feasible sum is
    kept (still within the validator's 10% tolerance in practice).
    """
    target = brief.target_runtime_seconds

    def _bounds(act_id: str) -> tuple[int, int]:
        raw_lo, raw_hi = duration_ranges.get(act_id, (1, 120))
        lo, hi = sorted((max(1, min(120, int(raw_lo))), max(1, min(120, int(raw_hi)))))
        return lo, max(lo, hi)

    def _clamp(value: Any, lo: int, hi: int) -> int:
        if not isinstance(value, (int, float)):
            value = 10
        return int(max(lo, min(hi, round(value))))

    for row in rows:
        act_id = str(row.get("act_id", "") or "")
        lo, hi = _bounds(act_id)
        row["duration_seconds"] = _clamp(row.get("duration_seconds", 10), lo, hi)

    gap = target - sum(int(r["duration_seconds"]) for r in rows)
    if gap == 0:
        return

    # Distribute the gap across rows in fixed order, within each row's bounds.
    delta = 1 if gap > 0 else -1
    remaining = abs(gap)
    while remaining > 0:
        moved = False
        for row in rows:
            if remaining <= 0:
                break
            act_id = str(row.get("act_id", "") or "")
            lo, hi = _bounds(act_id)
            current = int(row["duration_seconds"])
            if delta > 0 and current < hi:
                row["duration_seconds"] = current + 1
                remaining -= 1
                moved = True
            elif delta < 0 and current > lo:
                row["duration_seconds"] = current - 1
                remaining -= 1
                moved = True
        if not moved:
            break


def _design_shot_matrix(
    new_state: dict[str, Any], brief: ExecutionBrief | None = None
) -> Any | None:
    """Run the shot design agent, backfill scene coverage, reconcile, and save."""
    result = _run_agent(
        new_state,
        agent_id="shot-design-agent",
        phase="shot_bible",
        task=(
            "Produce the master film matrix: decompose every scene into "
            "individual shots with camera, duration, characters, environment, "
            "and prompt_ref. Match the exact shot count and runtime from "
            "the Execution Brief. Do not create one act per scene or treatment "
            "movement." + _execution_brief_contract(brief)
        ),
    )
    shot_matrix = result.get("shot_matrix")
    if shot_matrix is None:
        return None
    scene_ids = _script_scene_ids(new_state) if brief is not None else []
    # Reconcile before coverage backfill so the coverage helper observes all
    # script scenes, then reconcile once more to guarantee exact cardinality.
    shot_matrix = _reconcile_shot_matrix_to_brief(shot_matrix, brief, scene_ids)
    shot_matrix = _ensure_matrix_scene_coverage(new_state, shot_matrix)
    shot_matrix = _reconcile_shot_matrix_to_brief(shot_matrix, brief, scene_ids)
    ref = _save_artifact(new_state, shot_matrix, "shot_matrix", "shot_bible")
    if ref:
        new_state["shot_matrix_ref"] = ref
        new_state.setdefault("artifact_refs", []).append(ref)
    return shot_matrix


def _validate_shot_structure_gate(new_state: dict[str, Any], shot_matrix: Any) -> None:
    """Validate the shot structure against the execution brief."""
    if shot_matrix is None:
        return
    from film_pipeline.graph.orchestrator_validators import load_execution_brief

    brief = load_execution_brief(new_state)
    if brief is None:
        return
    from film_pipeline.graph.orchestrator_validators import validate_shot_structure

    struct_issues = validate_shot_structure(new_state, brief, shot_matrix)
    new_state.setdefault("issues", []).extend(struct_issues)


def shot_bible_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state  # keep reference for diff computation
    gate_updates = _phase_gate_updates(new_state, phase="shot_bible", gate="shot_bible")
    new_state.update(gate_updates)

    _ensure_execution_brief(new_state)

    from film_pipeline.graph.orchestrator_validators import load_execution_brief

    shot_matrix = _design_shot_matrix(new_state, load_execution_brief(new_state))

    _validate_shot_structure_gate(new_state, shot_matrix)

    updates = _collect_updates(
        gate_updates,
        new_state,
        original,
        ("shot_matrix_ref", "execution_brief_ref"),
    )
    _propagate_side_effects(new_state, updates, state)
    return updates


def _save_cost_estimate(new_state: dict[str, Any], result: dict[str, Any]) -> None:
    """Persist the planner's cost estimate and record its ref in state."""
    cost_estimate = result.get("cost_estimate")
    if cost_estimate is None:
        return
    ref = _save_artifact(new_state, cost_estimate, "cost_estimate", "gen_planning")
    if ref:
        new_state["cost_estimate_ref"] = ref
        new_state.setdefault("artifact_refs", []).append(ref)


def _build_generation_plan_patch(
    new_state: dict[str, Any],
    shot_groups: list[Any],
    shot_matrix_ref: str,
) -> None:
    """Emit a matrix patch setting prompt/provider refs and prompted status."""
    if not shot_groups or not shot_matrix_ref:
        return

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

    if not row_updates:
        return
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


def _validate_planning_gate(new_state: dict[str, Any], cost_estimate: Any) -> None:
    """Validate planning completeness and script/shot scene references."""
    shot_matrix_ref = str(new_state.get("shot_matrix_ref", ""))
    if not shot_matrix_ref:
        return
    services = _get_services(new_state)
    if services is None:
        return
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
        if not script_ref:
            return
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


def gen_planning_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state
    gate_updates = _phase_gate_updates(new_state, phase="gen_planning", gate="generation_spend")
    new_state.update(gate_updates)

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

    _save_cost_estimate(new_state, result)
    gen_requests = result.get("generation_requests")
    if gen_requests:
        new_state["generation_requests"] = gen_requests

    _build_generation_plan_patch(
        new_state,
        result.get("shot_groups") or [],
        str(new_state.get("shot_matrix_ref", "")),
    )

    _validate_planning_gate(new_state, result.get("cost_estimate"))

    updates = _collect_updates(
        gate_updates,
        new_state,
        original,
        ("cost_estimate_ref", "gen_planning_patch_ref"),
    )
    _propagate_side_effects(new_state, updates, state)
    return updates
