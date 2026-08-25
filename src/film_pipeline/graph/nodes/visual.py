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
from film_pipeline.graph.nodes._context import (
    _parse_ref,
)
from film_pipeline.graph.nodes._shared import (
    _get_services,
    _is_new_issue,
    _is_new_ref,
    _phase_gate_updates,
)
from film_pipeline.graph.services import GraphServices
from film_pipeline.schemas.matrix import MasterFilmMatrixRow


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


def _load_script_scenes(state: dict[str, Any], services: GraphServices) -> list[Any]:
    """Load raw scene entries from the script artifact referenced in state."""
    script_ref = state.get("script_ref")
    if not script_ref or not isinstance(script_ref, str):
        return []
    parts = script_ref.split(":")
    if len(parts) < 3:
        return []
    artifact_id = parts[1]
    try:
        version = int(parts[2].removeprefix("v"))
    except ValueError:
        return []

    from film_pipeline.schemas._base import FilmPhase

    try:
        script_raw = services.artifact_store.load(
            str(state.get("project_id", "")),
            FilmPhase("script"),
            artifact_id,
            version,
        )
    except Exception:
        return []

    scenes: list[Any] = script_raw.get("scenes", []) if isinstance(script_raw, dict) else []
    return scenes


def _row_get(row: Any, field: str) -> str:
    """Read a field from a matrix row that may be a model or a raw dict."""
    if isinstance(row, BaseModel):
        return str(getattr(row, field, ""))
    return str(row.get(field, ""))


def _infer_act_id(idx: int, total: int) -> str:
    """Determine a likely act from a scene's position (thirds)."""
    position = idx / max(total, 1)
    if position < 0.33:
        return "act_1"
    if position < 0.66:
        return "act_2"
    return "act_3"


def _next_auto_shot_id(base: str, taken: set[str]) -> str:
    """Return an unused auto shot id derived from *base* and register it."""
    candidate = base if base not in taken else f"{base}_1"
    taken.add(candidate)
    return candidate


def _build_autofilled_row(
    template_row: Any,
    scene: dict[str, Any],
    act_id: str,
    shot_id: str,
    generation_order: int,
) -> MasterFilmMatrixRow:
    """Clone the template row and stamp autofill fields for a missing scene."""
    scene_id = str(scene.get("scene_id", ""))
    if isinstance(template_row, BaseModel):
        row_data = template_row.model_dump()
    else:
        row_data = dict(template_row)
    row_data["shot_id"] = shot_id
    row_data["scene_id"] = scene_id
    row_data["act_id"] = act_id
    row_data["generation_order"] = generation_order
    row_data["auto_filled"] = True
    return MasterFilmMatrixRow(**row_data)


def _write_back_rows(matrix: Any, rows: list[Any]) -> Any:
    """Store the updated rows back onto the matrix artifact."""
    if isinstance(matrix, BaseModel):
        # Frozen model: return a copy with the updated rows list.
        return matrix.model_copy(update={"rows": rows})
    matrix["rows"] = rows
    return matrix


def _ensure_matrix_scene_coverage(
    state: dict[str, Any],
    shot_matrix: Any,
) -> Any:
    """Guarantee every scene_id in the script appears in at least one matrix row.

    LLM shot designers sometimes concentrate shots in a subset of scenes. This
    deterministic back-fill creates placeholder rows for any missing scenes so
    downstream generation planning never drops a scene entirely. Rows added here
    are flagged with ``auto_filled=True`` so operators can spot them.
    """
    services = _get_services(state)
    if services is None:
        return shot_matrix

    scenes = _load_script_scenes(state, services)
    if not scenes:
        return shot_matrix

    # Support both raw dicts and Pydantic models from the agent output.
    rows: list[Any] = (
        list(getattr(shot_matrix, "rows", []))
        if isinstance(shot_matrix, BaseModel)
        else list(shot_matrix.get("rows", []))
    )
    if not rows:
        return shot_matrix

    covered_scene_ids = {_row_get(row, "scene_id") for row in rows}
    template_row = rows[-1]
    taken_shot_ids = {_row_get(row, "shot_id") for row in rows}

    for idx, scene in enumerate(scenes):
        scene_id = str(scene.get("scene_id", ""))
        if not scene_id or scene_id in covered_scene_ids:
            continue
        rows.append(
            _build_autofilled_row(
                template_row,
                scene,
                act_id=_infer_act_id(idx, len(scenes)),
                shot_id=_next_auto_shot_id(f"s_auto_{scene_id}", taken_shot_ids),
                generation_order=len(rows) + 1,
            )
        )
        covered_scene_ids.add(scene_id)

    return _write_back_rows(shot_matrix, rows)


def _ensure_execution_brief(new_state: dict[str, Any]) -> None:
    """Extract structural metadata into state if not already present."""
    from film_pipeline.graph.orchestrator_state import has_execution_brief, set_execution_brief
    from film_pipeline.graph.orchestrator_validators import load_execution_brief

    if has_execution_brief(new_state) or load_execution_brief(new_state) is not None:
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


def _design_shot_matrix(new_state: dict[str, Any]) -> Any | None:
    """Run the shot design agent, backfill scene coverage, and save the matrix."""
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
    if shot_matrix is None:
        return None
    shot_matrix = _ensure_matrix_scene_coverage(new_state, shot_matrix)
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

    shot_matrix = _design_shot_matrix(new_state)

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
