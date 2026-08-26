"""StyleBibleAgent — produces StyleBible from FilmConstitution + EnvironmentBible."""

from __future__ import annotations

import json
from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.style import StyleBible


class StyleBibleAgent(BaseAgent):
    """Produces a StyleBible from the film constitution and environment bibles.

    Output artifact: ``StyleBible``
    """

    def prepare(self, state: dict[str, Any], kb_context: object, task: str) -> dict[str, Any]:
        _ = kb_context
        return {
            "project_id": str(state.get("project_id", "")),
            "visual_language": str(state.get("visual_language", "")),
            "tone": str(state.get("tone", "")),
            "palette_hint": str(state.get("palette_hint", "")),
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        data = _normalize_model_output(model_output)
        bible = StyleBible(
            project_id=str(data.get("project_id", "")),
            color_palette=_coerce_str_list(data.get("color_palette")),
            texture=str(data.get("texture", "")),
            grain=str(data.get("grain", "")),
            visual_mood=str(data.get("visual_mood", "")),
            reference_stills=_coerce_str_list(data.get("reference_stills")),
            must_not_change=_coerce_str_list(data.get("must_not_change")),
        )
        return {"style_bible": bible}

    def validate(self, result: dict[str, Any]) -> bool:
        bible = result.get("style_bible")
        if not isinstance(bible, StyleBible):
            return False
        if not bible.project_id:
            return False
        return len(bible.color_palette) > 0 or bool(bible.visual_mood)


def _coerce_str_list(value: object) -> list[str]:
    """Coerce a model-provided list field to ``list[str]``; non-lists yield ``[]``."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _normalize_model_output(model_output: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(model_output, str):
        try:
            model_output = json.loads(model_output)
        except (json.JSONDecodeError, TypeError):
            return {}
    if not isinstance(model_output, dict):
        return {}
    for key in ("style_bible", "data", "output"):
        candidate = model_output.get(key)
        if isinstance(candidate, dict):
            return candidate
    return model_output
