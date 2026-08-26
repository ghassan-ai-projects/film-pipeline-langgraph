"""CameraBibleAgent — produces CameraLanguageBible from FilmConstitution."""

from __future__ import annotations

import json
from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.camera import CameraLanguageBible, CameraProfile


class CameraBibleAgent(BaseAgent):
    """Produces a CameraLanguageBible from the film constitution.

    Output artifact: ``CameraLanguageBible``
    """

    def prepare(self, state: dict[str, Any], kb_context: object, task: str) -> dict[str, Any]:
        _ = kb_context
        return {
            "project_id": str(state.get("project_id", "")),
            "camera_philosophy": str(state.get("camera_philosophy", "")),
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        data = _normalize_model_output(model_output)
        profiles_data = data.get("profiles", [])
        if not isinstance(profiles_data, list):
            profiles_data = []

        bible = CameraLanguageBible(
            project_id=str(data.get("project_id", "")),
            profiles=[_build_camera_profile(p) for p in profiles_data],
            default_profile_id=str(data.get("default_profile_id", "")),
        )
        return {"camera_bible": bible}

    def validate(self, result: dict[str, Any]) -> bool:
        bible = result.get("camera_bible")
        if not isinstance(bible, CameraLanguageBible):
            return False
        return len(bible.profiles) > 0


def _build_camera_profile(profile_data: dict[str, Any]) -> CameraProfile:
    """Build one CameraProfile from raw profile fields."""
    return CameraProfile(
        profile_id=str(profile_data.get("profile_id", "")),
        use_case=str(profile_data.get("use_case", "")),
        lens=str(profile_data.get("lens", "")),
        framing=str(profile_data.get("framing", "")),
        movement=str(profile_data.get("movement", "")),
        depth_of_field=str(profile_data.get("depth_of_field", "")),
        composition_rules=[str(r) for r in profile_data.get("composition_rules", [])],
        transition_rules=[str(t) for t in profile_data.get("transition_rules", [])],
        emotional_meaning=str(profile_data.get("emotional_meaning", "")),
    )


def _normalize_model_output(model_output: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(model_output, str):
        try:
            model_output = json.loads(model_output)
        except (json.JSONDecodeError, TypeError):
            return {}
    if not isinstance(model_output, dict):
        return {}
    for key in ("camera_bible", "data", "output"):
        candidate = model_output.get(key)
        if isinstance(candidate, dict):
            return candidate
    return model_output
