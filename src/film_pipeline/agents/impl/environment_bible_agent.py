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
        """Parse model output into an EnvironmentBible artifact."""
        data = _normalize_model_output(model_output)
        zones = _as_list(data.get("zones", []))
        viewpoints = _as_list(data.get("viewpoints", []))
        lighting_states = _as_list(data.get("lighting_states", []))
        palette = _as_list(data.get("color_palette", []))
        fingerprint_data = _as_dict(data.get("fingerprint", {}))
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


def _as_dict(value: Any) -> dict[str, Any]:
    """Coerce an optional or mistyped section to an empty dict."""
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    """Coerce an optional or mistyped section to an empty list."""
    if not isinstance(value, list):
        return []
    return value


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
