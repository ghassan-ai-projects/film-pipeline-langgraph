"""Deterministic scene-coverage back-fill for the master film matrix.

LLM shot designers sometimes concentrate shots in a subset of scenes. These
helpers guarantee every scripted scene appears in at least one matrix row by
appending ``auto_filled`` placeholder rows for any missing scene.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from film_pipeline.graph.services import GraphServices, _get_services
from film_pipeline.schemas.matrix import MasterFilmMatrixRow


def _load_script_scenes(state: dict[str, Any], services: GraphServices) -> list[Any]:
    """Load raw scene entries from the script artifact referenced in state."""
    script_ref = state.get("script_ref")
    if not script_ref or not isinstance(script_ref, str):
        return []

    from film_pipeline.schemas._base import FilmPhase
    from film_pipeline.schemas.artifact import ArtifactRef

    try:
        parsed = ArtifactRef.from_string(script_ref)
    except ValueError:
        return []

    phase = FilmPhase(parsed.phase) if parsed.phase else FilmPhase("script")
    try:
        script_raw = services.artifact_store.load(
            str(state.get("project_id", "")),
            phase,
            parsed.artifact_id,
            parsed.version,
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
