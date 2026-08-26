"""DevelopmentAgent — produces a Treatment and SceneIntent list."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.story_bible import (
    ActMap,
    SceneIntent,
    SceneList,
    Treatment,
)

_logger = logging.getLogger(__name__)


def _build_treatment(treatment_data: dict[str, Any]) -> Treatment:
    """Coerce the raw treatment payload into a Treatment."""
    act_map = None
    if treatment_data.get("act_map"):
        am = treatment_data["act_map"]
        act_map = ActMap(
            act1_setup=str(am.get("act1_setup", "")),
            act2_confrontation=str(am.get("act2_confrontation", "")),
            act3_resolution=str(am.get("act3_resolution", "")),
        )
    return Treatment(
        text=str(treatment_data.get("text", "")),
        themes=[str(t) for t in treatment_data.get("themes", [])],
        act_map=act_map,
    )


def _build_scene_intents(scenes: Any) -> list[SceneIntent]:
    """Coerce raw scene payloads into SceneIntents with fallback ids."""
    return [
        SceneIntent(
            scene_id=str(s.get("scene_id", f"s_{i:03d}")),
            dramatic_function=str(s.get("dramatic_function", "")),
            emotional_shift=str(s.get("emotional_shift", "")),
            conflict=str(s.get("conflict", "")),
            outcome=str(s.get("outcome", "")),
        )
        for i, s in enumerate(scenes)
    ]


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

        try:
            treatment = _build_treatment(data.get("treatment", {}))
            scenes = data.get("scenes", data.get("scene_list", []))
            scene_list = SceneList(scenes=_build_scene_intents(scenes))
        except ValidationError as exc:
            _logger.error(
                "DevelopmentAgent: Pydantic validation failed. Errors: %s | Model output: %s",
                exc.errors(),
                json.dumps(model_output, indent=2, default=str)[:2000],
            )
            raise ValueError(f"DevelopmentAgent produced invalid output: {exc.errors()}") from exc

        return {"treatment": treatment, "scene_list": scene_list}

    def validate(self, result: dict[str, Any]) -> bool:
        treatment = result.get("treatment")
        scene_list = result.get("scene_list")
        if not isinstance(treatment, Treatment) or not isinstance(scene_list, SceneList):
            return False
        return bool(treatment.text and len(scene_list.scenes) > 0)
