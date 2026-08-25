"""ShotBibleAgent — produces a MasterFilmMatrix from the script and visual references."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.matrix import (
    ChainingConfig,
    CoverageGroup,
    MasterFilmMatrix,
    MasterFilmMatrixRow,
)


class ShotBibleAgent(BaseAgent):
    """Creates the detailed shot matrix from the script and visual references.

    Output artifact: ``MasterFilmMatrix``
    """

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: object,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context
        project_id = str(state.get("project_id", ""))
        script_ref = str(state.get("script_ref", ""))
        visual_refs = str(state.get("visual_refs", ""))
        return {
            "project_id": project_id,
            "script_ref": script_ref,
            "visual_refs": visual_refs,
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        """Parse model output into a MasterFilmMatrix artifact."""
        data = model_output.get("shot_matrix", model_output)
        rows_data, groups_data = _matrix_sections(data)
        matrix = MasterFilmMatrix(
            project_id=str(data.get("project_id", "")) if isinstance(data, dict) else "",
            rows=[_build_matrix_row(r, i) for i, r in enumerate(rows_data)],
            coverage_groups=[_build_coverage_group(g, j) for j, g in enumerate(groups_data)],
        )
        return {"shot_matrix": matrix}

    def validate(self, result: dict[str, Any]) -> bool:
        matrix = result.get("shot_matrix")
        if not isinstance(matrix, MasterFilmMatrix):
            return False
        return len(matrix.rows) > 0


def _matrix_sections(data: Any) -> tuple[list[Any], list[Any]]:
    """Split raw model output into (rows, coverage_groups) sections.

    Handles the case where the LLM returns the rows as a direct list
    (e.g. ``{"shot_matrix": [{"shot_id": ...}]}``) instead of a dict
    with separate "rows" and "coverage_groups" keys.
    """
    if isinstance(data, list):
        return data, []
    if not isinstance(data, dict):
        return [], []
    rows_candidate = data.get("rows", data.get("matrix_rows", data.get("shots")))
    groups_candidate = data.get("coverage_groups")
    rows = rows_candidate if isinstance(rows_candidate, list) else []
    groups = groups_candidate if isinstance(groups_candidate, list) else []
    return rows, groups


def _build_matrix_row(entry: dict[str, Any], index: int) -> MasterFilmMatrixRow:
    """Build one MasterFilmMatrixRow from a raw shot mapping."""
    chaining_data = entry.get("chaining", {})
    chaining = ChainingConfig(
        input_frame_ref=str(chaining_data.get("input_frame_ref", "")) or None,
        re_anchor=bool(chaining_data.get("re_anchor", False)),
    )
    return MasterFilmMatrixRow(
        shot_id=str(entry.get("shot_id", f"shot_{index:04d}")),
        act_id=str(entry.get("act_id", "act1")),
        sequence_id=str(entry.get("sequence_id", f"seq_{index:03d}")),
        scene_id=str(entry.get("scene_id", "")),
        scene_intent_ref=str(entry.get("scene_intent_ref", "")),
        duration_seconds=int(entry.get("duration_seconds", 5)),
        story_function=str(entry.get("story_function", "")),
        characters=[str(c) for c in entry.get("characters", [])],
        environment=str(entry.get("environment", "")),
        camera_profile=str(entry.get("camera_profile", "")),
        prompt_ref=str(entry.get("prompt_ref", "")),
        generation_order=int(entry.get("generation_order", index)),
        chaining=chaining,
        priority=str(entry.get("priority", "standard")),
        risk_level=str(entry.get("risk_level", "medium")),
    )


def _build_coverage_group(entry: dict[str, Any], index: int) -> CoverageGroup:
    """Build one CoverageGroup from a raw coverage mapping."""
    return CoverageGroup(
        coverage_group_id=str(entry.get("coverage_group_id", f"cg_{index:03d}")),
        scene_id=str(entry.get("scene_id", "")),
        story_moment=str(entry.get("story_moment", "")),
        continuity_event=str(entry.get("continuity_event", "")),
        coverage_type=str(entry.get("coverage_type", "dialogue_exchange")),
        required_angles=[str(a) for a in entry.get("required_angles", [])],
        editorial_intent=str(entry.get("editorial_intent", "")),
    )
