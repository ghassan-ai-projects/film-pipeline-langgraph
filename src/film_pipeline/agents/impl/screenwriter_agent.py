"""ScreenwriterAgent — produces StoryBible and Script from the treatment."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.script import DialogueLine, Script, ScriptScene
from film_pipeline.schemas.story_bible import (
    ActMap,
    Logline,
    Premise,
    SceneList,
    SetupPayoffEntry,
    StoryBible,
    Treatment,
)

_logger = logging.getLogger(__name__)


class ScreenwriterAgent(BaseAgent):
    """Writes the full screenplay from the treatment and scene intents.

    Output artifacts: ``StoryBible``, ``Script``
    """

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: object,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context
        project_id = str(state.get("project_id", ""))
        treatment_ref = str(state.get("treatment_ref", ""))
        scene_list_ref = str(state.get("scene_list_ref", ""))
        constitution_ref = str(state.get("constitution_ref", ""))
        return {
            "project_id": project_id,
            "treatment_ref": treatment_ref,
            "scene_list_ref": scene_list_ref,
            "constitution_ref": constitution_ref,
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        """Parse model output into StoryBible + Script."""
        data = model_output.get("script_output", model_output)

        try:
            # --- StoryBible ---
            bible_data = data.get("story_bible", data)
            raw_logline = bible_data.get("logline", "")
            if isinstance(raw_logline, dict):
                logline_text = str(raw_logline.get("text", ""))
                logline_hook = str(raw_logline.get("hook", ""))
            else:
                logline_text = str(raw_logline)
                logline_hook = str(bible_data.get("hook", ""))
            try:
                logline = Logline(text=logline_text, hook=logline_hook)
            except Exception:
                logline = Logline(text=logline_text or "Untitled film project.")
            premise_data = bible_data.get("premise", {})
            if isinstance(premise_data, dict):
                premise = Premise(
                    text=str(premise_data.get("text", "")),
                    dramatic_question=str(premise_data.get("dramatic_question", "")),
                )
            else:
                premise = Premise(
                    text=str(premise_data),
                    dramatic_question=str(bible_data.get("dramatic_question", "")),
                )
            am = bible_data.get("act_map", {})
            act_map = ActMap(
                act1_setup=str(am.get("act1_setup", "")),
                act2_confrontation=str(am.get("act2_confrontation", "")),
                act3_resolution=str(am.get("act3_resolution", "")),
            )
            treatment = Treatment(
                text=str(bible_data.get("treatment_text", "")),
                themes=[str(t) for t in bible_data.get("themes", [])],
                act_map=act_map,
            )
            raw_scenes = bible_data.get("scene_list", bible_data.get("scenes", []))
            # Unwrap if LLM produced {"scenes": [...]} (matching the template's
            # SceneList object shape) instead of a bare list
            if isinstance(raw_scenes, dict):
                raw_scenes = raw_scenes.get("scenes", [])
            from film_pipeline.schemas.story_bible import SceneIntent as SI

            scene_intents = [
                SI(
                    scene_id=str(s.get("scene_id", f"s_{i:03d}")),
                    dramatic_function=str(s.get("dramatic_function", "")),
                    emotional_shift=str(s.get("emotional_shift", "")),
                    conflict=str(s.get("conflict", "")),
                    outcome=str(s.get("outcome", "")),
                )
                for i, s in enumerate(raw_scenes)
            ]
            story_bible = StoryBible(
                project_id=str(bible_data.get("project_id", "")),
                logline=logline,
                premise=premise,
                treatment=treatment,
                act_map=act_map,
                scene_list=SceneList(scenes=scene_intents),
                setup_payoff_map=[
                    SetupPayoffEntry(
                        setup_scene_id=str(sp.get("setup_scene_id", "")),
                        payoff_scene_id=str(sp.get("payoff_scene_id", "")),
                        description=str(sp.get("description", "")),
                    )
                    for sp in bible_data.get("setup_payoff_map", [])
                ],
                unresolved_threads=[str(t) for t in bible_data.get("unresolved_threads", [])],
                theme_map=[str(t) for t in bible_data.get("theme_map", [])],
            )

            # --- Script ---
            script_data = data.get("script", data)
            script_scenes = [
                ScriptScene(
                    scene_id=str(s.get("scene_id", f"sc_{i:03d}")),
                    scene_heading=str(s.get("scene_heading", "")),
                    action_lines=[str(a) for a in s.get("action_lines", [])],
                    dialogue=[
                        DialogueLine(
                            character_id=str(d.get("character_id", "")),
                            line=str(d.get("line", "")),
                            direction=str(d.get("direction", "")),
                        )
                        for d in s.get("dialogue", [])
                    ],
                    intent_ref=str(s.get("intent_ref", "")),
                )
                for i, s in enumerate(script_data.get("scenes", []))
            ]
            script = Script(
                project_id=str(script_data.get("project_id", "")),
                title=str(script_data.get("title", "")),
                scenes=script_scenes,
                total_scenes=len(script_scenes),
                total_dialogue_lines=sum(len(sc.dialogue) for sc in script_scenes),
            )
        except ValidationError as exc:
            _logger.error(
                "ScreenwriterAgent: Pydantic validation failed. Errors: %s | Model output: %s",
                exc.errors(),
                json.dumps(model_output, indent=2, default=str)[:2000],
            )
            raise ValueError(f"ScreenwriterAgent produced invalid output: {exc.errors()}") from exc

        return {"story_bible": story_bible, "script": script}

    def validate(self, result: dict[str, Any]) -> bool:
        story_bible = result.get("story_bible")
        script = result.get("script")
        if not isinstance(story_bible, StoryBible) or not isinstance(script, Script):
            return False
        return bool(story_bible.logline.text and len(script.scenes) > 0)
