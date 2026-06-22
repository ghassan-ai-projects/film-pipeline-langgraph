"""StructureExtractorAgent — extracts structural metadata from the approved story.

Runs automatically as a pre-step in shot_bible_node. Takes the raw story text
and the approved StoryBible, then produces an ExecutionBrief that the
orchestrator uses to enforce shot-count, runtime, and structural invariants.
"""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.execution_brief import ExecutionBrief, MovementSpec


class StructureExtractorAgent(BaseAgent):
    """Extracts film structure from the raw story and StoryBible.

    Output artifact: ``ExecutionBrief``
    Uses ``schema_enforcer`` profile for precise structural extraction.
    """

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: object,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context
        project_id = str(state.get("project_id", ""))
        story_bible_ref = str(state.get("story_bible_ref", ""))
        script_ref = str(state.get("script_ref", ""))
        return {
            "project_id": project_id,
            "story_bible_ref": story_bible_ref,
            "script_ref": script_ref,
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        """Parse model output into ExecutionBrief."""
        data = model_output.get("execution_brief", model_output)

        movement_raw: list[dict[str, Any]] = (
            data.get("movements", []) if isinstance(data, dict) else []
        )
        movements: list[MovementSpec] = []
        for m in movement_raw:
            dr = m.get("duration_range_seconds", [10, 15])
            if isinstance(dr, (list, tuple)) and len(dr) == 2:
                dmin, dmax = int(dr[0]), int(dr[1])
            else:
                dmin, dmax = 10, 15
            movements.append(
                MovementSpec(
                    movement_id=str(m.get("movement_id", f"act_{len(movements) + 1}")),
                    shot_count=int(m.get("shot_count", 1)),
                    duration_range_seconds=(dmin, dmax),
                    description=str(m.get("description", "")),
                )
            )

        brief = ExecutionBrief(
            project_id=str(data.get("project_id", "")) if isinstance(data, dict) else "",
            target_runtime_seconds=_coerce_runtime(data),
            movements=movements,
            mandatory_anchors=[str(a) for a in data.get("mandatory_anchors", [])]
            if isinstance(data, dict)
            else [],
            environment_progression=[str(e) for e in data.get("environment_progression", [])]
            if isinstance(data, dict)
            else [],
            pacing_style=str(data.get("pacing_style", "standard"))
            if isinstance(data, dict)
            else "standard",
        )
        return {"execution_brief": brief}

    def validate(self, result: dict[str, Any]) -> bool:
        brief = result.get("execution_brief")
        if not isinstance(brief, ExecutionBrief):
            return False
        return bool(
            brief.project_id and brief.target_runtime_seconds > 0 and len(brief.movements) > 0
        )


def _coerce_runtime(data: Any) -> int:
    """Extract target runtime from model output, with sensible defaults."""
    if not isinstance(data, dict):
        return 300
    candidates = (
        data.get("target_runtime_seconds"),
        data.get("estimated_runtime_seconds"),
    )
    for candidate in candidates:
        try:
            val = int(str(candidate))
            if val > 1:
                return val
        except (TypeError, ValueError):
            continue
    # Fallback: sum movement durations
    movements = data.get("movements", [])
    if isinstance(movements, list):
        total = 0
        for m in movements:
            if isinstance(m, dict):
                sc = m.get("shot_count", 0)
                dr = m.get("duration_range_seconds", [10, 15])
                if isinstance(dr, (list, tuple)) and len(dr) == 2:
                    avg = (dr[0] + dr[1]) / 2
                    total += int(sc * avg)
        if total > 0:
            return total
    return 300
