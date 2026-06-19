"""ConstitutionAgent — produces a FilmConstitution from the project idea."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.film_constitution import CharacterTruth, FilmConstitution


class ConstitutionAgent(BaseAgent):
    """Creates the film's creative constitution from the classified input.

    Output artifact: ``FilmConstitution``
    """

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: object,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context
        project_id = str(state.get("project_id", ""))
        idea = str(state.get("idea", state.get("classified_input", "")))
        return {
            "project_id": project_id,
            "idea": idea,
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        """Parse the model's JSON output into a FilmConstitution.

        Handles both flat keys and a nested ``constitution`` wrapper.
        """
        data = model_output.get("constitution", model_output)
        character_truths = [
            CharacterTruth(
                character_id=str(ct.get("character_id", f"char_{i}")),
                truth=str(ct.get("truth", "")),
            )
            for i, ct in enumerate(data.get("character_truths", []))
        ]
        constitution = FilmConstitution(
            project_id=str(data.get("project_id", "")),
            theme=str(data.get("theme", "")),
            tone=str(data.get("tone", "")),
            emotional_promise=str(data.get("emotional_promise", "")),
            visual_language=str(data.get("visual_language", "")),
            camera_philosophy=str(data.get("camera_philosophy", "")),
            quality_bar=str(data.get("quality_bar", "")),
            character_truths=character_truths,
            taboo_mistakes=[str(m) for m in data.get("taboo_mistakes", [])],
        )
        return {"constitution": constitution}

    def validate(self, result: dict[str, Any]) -> bool:
        constitution = result.get("constitution")
        if not isinstance(constitution, FilmConstitution):
            return False
        return bool(constitution.theme and constitution.tone)
