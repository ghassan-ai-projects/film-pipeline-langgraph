"""CharacterBibleAgent — produces CharacterBible from Script + FilmConstitution."""

from __future__ import annotations

import json
from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.character import (
    CharacterBible,
    CharacterIdentity,
    EmotionalArc,
    RelationshipMap,
    VoiceRules,
    WardrobeRules,
)


class CharacterBibleAgent(BaseAgent):
    """Produces a CharacterBible from the script and film constitution.

    Output artifact: ``CharacterBible``
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
            "character_id": str(state.get("character_id", "")),
            "character_name": str(state.get("character_name", "")),
            "script_content": str(state.get("script_content", "")),
            "constitution_content": str(state.get("constitution_content", "")),
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        """Parse model output into a CharacterBible artifact."""
        data = _normalize_model_output(model_output)
        character_id = str(data.get("character_id", ""))
        identity_data = _section_dict(data, "visual_identity", "identity")
        voice_data = _section_dict(data, "voice_rules", "voice")
        wardrobe_data = _section_dict(data, "wardrobe_rules", "wardrobe")
        arc_data = _as_dict(data.get("emotional_arc", {}))
        relationships = _as_list(data.get("relationship_map", data.get("relationships", [])))
        bible = CharacterBible(
            character_id=character_id,
            project_id=str(data.get("project_id", "")),
            visual_identity=_build_visual_identity(character_id, identity_data),
            voice_rules=_build_voice_rules(voice_data),
            wardrobe_rules=_build_wardrobe_rules(wardrobe_data),
            emotional_arc=_build_emotional_arc(arc_data),
            relationship_map=[_build_relationship(r) for r in relationships],
            reference_assets=[str(a) for a in data.get("reference_assets", [])],
            must_not_change=[str(m) for m in data.get("must_not_change", [])],
        )
        return {"character_bible": bible}

    def validate(self, result: dict[str, Any]) -> bool:
        bible = result.get("character_bible")
        if not isinstance(bible, CharacterBible):
            return False
        return bool(bible.character_id and bible.visual_identity.identity_block)


def _as_dict(value: Any) -> dict[str, Any]:
    """Coerce an optional or mistyped section to an empty dict."""
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    """Coerce an optional or mistyped section to an empty list."""
    if not isinstance(value, list):
        return []
    return value


def _section_dict(data: dict[str, Any], primary_key: str, fallback_key: str) -> dict[str, Any]:
    """Read a dict section honoring the legacy two-key fallback order."""
    raw = data.get(primary_key, data.get(fallback_key, {}))
    return _as_dict(raw)


def _build_visual_identity(character_id: str, identity_data: dict[str, Any]) -> CharacterIdentity:
    """Build the CharacterIdentity sub-model from raw identity fields."""
    return CharacterIdentity(
        character_id=character_id,
        name=str(identity_data.get("name", "")),
        role=str(identity_data.get("role", "")),
        age=str(identity_data.get("age", "")),
        physical_description=str(identity_data.get("physical_description", "")),
        identity_block=str(identity_data.get("identity_block", "")),
    )


def _build_voice_rules(voice_data: dict[str, Any]) -> VoiceRules:
    """Build the VoiceRules sub-model from raw voice fields."""
    return VoiceRules(
        cadence=str(voice_data.get("cadence", "")),
        vocabulary=[str(v) for v in voice_data.get("vocabulary", [])],
        forbidden_phrasings=[str(p) for p in voice_data.get("forbidden_phrasings", [])],
        signature_moves=[str(m) for m in voice_data.get("signature_moves", [])],
    )


def _build_wardrobe_rules(wardrobe_data: dict[str, Any]) -> WardrobeRules:
    """Build the WardrobeRules sub-model from raw wardrobe fields."""
    return WardrobeRules(
        baseline=str(wardrobe_data.get("baseline", "")),
        act_variants={str(k): str(v) for k, v in wardrobe_data.get("act_variants", {}).items()},
    )


def _build_emotional_arc(arc_data: dict[str, Any]) -> EmotionalArc:
    """Build the EmotionalArc sub-model from raw arc fields."""
    return EmotionalArc(
        start_state=str(arc_data.get("start_state", "")),
        midpoint_state=str(arc_data.get("midpoint_state", "")),
        end_state=str(arc_data.get("end_state", "")),
        key_turning_points=[str(t) for t in arc_data.get("key_turning_points", [])],
    )


def _build_relationship(entry: dict[str, Any]) -> RelationshipMap:
    """Build one RelationshipMap entry from a raw mapping."""
    return RelationshipMap(
        other_character_id=str(entry.get("other_character_id", "")),
        relation=str(entry.get("relation", "")),
        evolution=str(entry.get("evolution", "")),
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
    # Try nested keys
    for key in ("character_bible", "data", "output"):
        candidate = model_output.get(key)
        if isinstance(candidate, dict):
            return candidate
    return model_output
