"""DevelopmentAgent — produces a Treatment and SceneIntent list."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.story_bible import (
    ActMap,
    SceneIntent,
    SceneList,
    Treatment,
)


class DevelopmentAgent(BaseAgent):
    """Creates the film treatment and scene breakdown.

    Output artifacts: ``Treatment``, ``SceneList`` (list of ``SceneIntent``)
    """

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: object,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context
        project_id = str(state.get("project_id", ""))
        constitution_ref = str(state.get("constitution_ref", ""))
        return {
            "project_id": project_id,
            "constitution_ref": constitution_ref,
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        """Parse model output into Treatment + SceneList."""
        data = model_output.get("development", model_output)

        treatment_data = data.get("treatment", {})
        act_map = None
        if treatment_data.get("act_map"):
            am = treatment_data["act_map"]
            act_map = ActMap(
                act1_setup=str(am.get("act1_setup", "")),
                act2_confrontation=str(am.get("act2_confrontation", "")),
                act3_resolution=str(am.get("act3_resolution", "")),
            )
        treatment = Treatment(
            text=str(treatment_data.get("text", "")),
            themes=[str(t) for t in treatment_data.get("themes", [])],
            act_map=act_map,
        )

        scenes = data.get("scenes", data.get("scene_list", []))
        scene_intents = [
            SceneIntent(
                scene_id=str(s.get("scene_id", f"s_{i:03d}")),
                dramatic_function=str(s.get("dramatic_function", "")),
                emotional_shift=str(s.get("emotional_shift", "")),
                conflict=str(s.get("conflict", "")),
                outcome=str(s.get("outcome", "")),
            )
            for i, s in enumerate(scenes)
        ]
        scene_list = SceneList(scenes=scene_intents)

        return {"treatment": treatment, "scene_list": scene_list}

    def validate(self, result: dict[str, Any]) -> bool:
        treatment = result.get("treatment")
        scene_list = result.get("scene_list")
        if not isinstance(treatment, Treatment) or not isinstance(scene_list, SceneList):
            return False
        return bool(treatment.text and len(scene_list.scenes) > 0)
