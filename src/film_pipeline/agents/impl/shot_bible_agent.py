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
        data = model_output.get("shot_matrix", model_output)

        # Handle the case where the LLM returns the rows as a direct list
        # (e.g. {"shot_matrix": [{"shot_id": ...}]}) instead of a dict
        # with separate "rows" and "coverage_groups" keys.
        if isinstance(data, list):
            rows_data = data
            groups_data = []
        elif isinstance(data, dict):
            rows_candidate = data.get("rows", data.get("matrix_rows", data.get("shots")))
            rows_data = rows_candidate if isinstance(rows_candidate, list) else []
            groups_candidate = data.get("coverage_groups")
            groups_data = groups_candidate if isinstance(groups_candidate, list) else []
        else:
            rows_data = []
            groups_data = []

        rows = []
        for i, r in enumerate(rows_data):
            chaining_data = r.get("chaining", {})
            chaining = ChainingConfig(
                input_frame_ref=str(chaining_data.get("input_frame_ref", "")) or None,
                re_anchor=bool(chaining_data.get("re_anchor", False)),
            )
            row = MasterFilmMatrixRow(
                shot_id=str(r.get("shot_id", f"shot_{i:04d}")),
                act_id=str(r.get("act_id", "act1")),
                sequence_id=str(r.get("sequence_id", f"seq_{i:03d}")),
                scene_id=str(r.get("scene_id", "")),
                scene_intent_ref=str(r.get("scene_intent_ref", "")),
                duration_seconds=int(r.get("duration_seconds", 5)),
                story_function=str(r.get("story_function", "")),
                characters=[str(c) for c in r.get("characters", [])],
                environment=str(r.get("environment", "")),
                camera_profile=str(r.get("camera_profile", "")),
                prompt_ref=str(r.get("prompt_ref", "")),
                generation_order=int(r.get("generation_order", i)),
                chaining=chaining,
                priority=str(r.get("priority", "standard")),
                risk_level=str(r.get("risk_level", "medium")),
            )
            rows.append(row)

        coverage_groups = [
            CoverageGroup(
                coverage_group_id=str(g.get("coverage_group_id", f"cg_{j:03d}")),
                scene_id=str(g.get("scene_id", "")),
                story_moment=str(g.get("story_moment", "")),
                continuity_event=str(g.get("continuity_event", "")),
                coverage_type=str(g.get("coverage_type", "dialogue_exchange")),
                required_angles=[str(a) for a in g.get("required_angles", [])],
                editorial_intent=str(g.get("editorial_intent", "")),
            )
            for j, g in enumerate(groups_data)
        ]

        shot_matrix = MasterFilmMatrix(
            project_id=str(data.get("project_id", "")) if isinstance(data, dict) else "",
            rows=rows,
            coverage_groups=coverage_groups,
        )
        return {"shot_matrix": shot_matrix}

    def validate(self, result: dict[str, Any]) -> bool:
        matrix = result.get("shot_matrix")
        if not isinstance(matrix, MasterFilmMatrix):
            return False
        return len(matrix.rows) > 0
