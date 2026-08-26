"""EnvironmentBibleAgent — produces EnvironmentBible from Script + FilmConstitution."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.agents.impl._model_output import as_dict, as_list, normalize_model_output
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
        """Parse model output into an EnvironmentBible artifact."""
        data = normalize_model_output(model_output, artifact_key="environment_bible")
        zones = as_list(data.get("zones", []))
        viewpoints = as_list(data.get("viewpoints", []))
        lighting_states = as_list(data.get("lighting_states", []))
        palette = as_list(data.get("color_palette", []))
        fingerprint_data = as_dict(data.get("fingerprint", {}))
        bible = EnvironmentBible(
            environment_id=str(data.get("environment_id", "")),
            project_id=str(data.get("project_id", "")),
            name=str(data.get("name", "")),
            locked_prompt_block=str(data.get("locked_prompt_block", "")),
            invariants=[str(i) for i in data.get("invariants", []) if isinstance(i, str)],
            zones=[_build_zone(z) for z in zones],
            viewpoints=[_build_viewpoint(v) for v in viewpoints],
            lighting_states=[_build_lighting_state(ls) for ls in lighting_states],
            color_palette=[str(c) for c in palette],
            fingerprint=EnvironmentFingerprint(text=str(fingerprint_data.get("text", ""))),
            reference_assets=[str(r) for r in data.get("reference_assets", [])],
            must_not_change=[str(m) for m in data.get("must_not_change", [])],
        )
        return {"environment_bible": bible}

    def validate(self, result: dict[str, Any]) -> bool:
        bible = result.get("environment_bible")
        if not isinstance(bible, EnvironmentBible):
            return False
        return bool(bible.environment_id and bible.locked_prompt_block and bible.fingerprint.text)


def _build_zone(entry: dict[str, Any]) -> EnvironmentZone:
    """Build one EnvironmentZone entry from a raw mapping."""
    return EnvironmentZone(
        zone_id=str(entry.get("zone_id", "")),
        description=str(entry.get("description", "")),
        allowed_viewpoints=[str(v) for v in entry.get("allowed_viewpoints", [])],
    )


def _build_viewpoint(entry: dict[str, Any]) -> Viewpoint:
    """Build one Viewpoint entry from a raw mapping."""
    return Viewpoint(
        viewpoint_id=str(entry.get("viewpoint_id", "")),
        description=str(entry.get("description", "")),
        lens=str(entry.get("lens", "")),
        framing=str(entry.get("framing", "")),
    )


def _build_lighting_state(entry: dict[str, Any]) -> LightingState:
    """Build one LightingState entry from a raw mapping."""
    return LightingState(
        state_id=str(entry.get("state_id", "")),
        description=str(entry.get("description", "")),
        shadow_direction=str(entry.get("shadow_direction", "")),
        color_temperature=str(entry.get("color_temperature", "")),
        primary_source=str(entry.get("primary_source", "")),
    )
