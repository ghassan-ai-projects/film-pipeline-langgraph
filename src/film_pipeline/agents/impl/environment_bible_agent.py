"""EnvironmentBibleAgent — produces EnvironmentBible from Script + FilmConstitution."""

from __future__ import annotations

import json
from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.environment import (
    EnvironmentBible,
    EnvironmentFingerprint,
    EnvironmentZone,
    LightingState,
    Viewpoint,
)


class EnvironmentBibleAgent(BaseAgent):
    """Produces an EnvironmentBible from the script and film constitution.

    Output artifact: ``EnvironmentBible``
    """

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: object,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context
        return {
            "project_id": str(state.get("project_id", "")),
            "environment_id": str(state.get("environment_id", "")),
            "environment_name": str(state.get("environment_name", "")),
            "script_content": str(state.get("script_content", "")),
            "constitution_content": str(state.get("constitution_content", "")),
            "visual_language": str(state.get("visual_language", "")),
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        data = _normalize_model_output(model_output)

        zones_data = data.get("zones", [])
        if not isinstance(zones_data, list):
            zones_data = []

        viewpoints_data = data.get("viewpoints", [])
        if not isinstance(viewpoints_data, list):
            viewpoints_data = []

        lighting_data = data.get("lighting_states", [])
        if not isinstance(lighting_data, list):
            lighting_data = []

        palette = data.get("color_palette", [])
        if not isinstance(palette, list):
            palette = []

        fingerprint_data = data.get("fingerprint", {})
        if not isinstance(fingerprint_data, dict):
            fingerprint_data = {}

        bible = EnvironmentBible(
            environment_id=str(data.get("environment_id", "")),
            project_id=str(data.get("project_id", "")),
            name=str(data.get("name", "")),
            locked_prompt_block=str(data.get("locked_prompt_block", "")),
            invariants=[str(i) for i in data.get("invariants", []) if isinstance(i, str)],
            zones=[
                EnvironmentZone(
                    zone_id=str(z.get("zone_id", "")),
                    description=str(z.get("description", "")),
                    allowed_viewpoints=[str(v) for v in z.get("allowed_viewpoints", [])],
                )
                for z in zones_data
            ],
            viewpoints=[
                Viewpoint(
                    viewpoint_id=str(v.get("viewpoint_id", "")),
                    description=str(v.get("description", "")),
                    lens=str(v.get("lens", "")),
                    framing=str(v.get("framing", "")),
                )
                for v in viewpoints_data
            ],
            lighting_states=[
                LightingState(
                    state_id=str(ls.get("state_id", "")),
                    description=str(ls.get("description", "")),
                    shadow_direction=str(ls.get("shadow_direction", "")),
                    color_temperature=str(ls.get("color_temperature", "")),
                    primary_source=str(ls.get("primary_source", "")),
                )
                for ls in lighting_data
            ],
            color_palette=[str(c) for c in palette],
            fingerprint=EnvironmentFingerprint(
                text=str(fingerprint_data.get("text", "")),
            ),
            reference_assets=[str(r) for r in data.get("reference_assets", [])],
            must_not_change=[str(m) for m in data.get("must_not_change", [])],
        )
        return {"environment_bible": bible}

    def validate(self, result: dict[str, Any]) -> bool:
        bible = result.get("environment_bible")
        if not isinstance(bible, EnvironmentBible):
            return False
        return bool(bible.environment_id and bible.locked_prompt_block and bible.fingerprint.text)


def _normalize_model_output(model_output: dict[str, Any] | str) -> dict[str, Any]:
    """Handle both raw JSON strings and already-parsed dicts."""
    if isinstance(model_output, str):
        try:
            model_output = json.loads(model_output)
        except (json.JSONDecodeError, TypeError):
            return {}
    if not isinstance(model_output, dict):
        return {}
    for key in ("environment_bible", "data", "output"):
        candidate = model_output.get(key)
        if isinstance(candidate, dict):
            return candidate
    return model_output
