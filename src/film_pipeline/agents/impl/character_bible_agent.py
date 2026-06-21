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
        data = _normalize_model_output(model_output)

        identity_data = data.get("visual_identity", data.get("identity", {}))
        if not isinstance(identity_data, dict):
            identity_data = {}

        voice_data = data.get("voice_rules", data.get("voice", {}))
        if not isinstance(voice_data, dict):
            voice_data = {}

        wardrobe_data = data.get("wardrobe_rules", data.get("wardrobe", {}))
        if not isinstance(wardrobe_data, dict):
            wardrobe_data = {}

        arc_data = data.get("emotional_arc", {})
        if not isinstance(arc_data, dict):
            arc_data = {}

        relationships_data = data.get("relationship_map", data.get("relationships", []))
        if not isinstance(relationships_data, list):
            relationships_data = []

        bible = CharacterBible(
            character_id=str(data.get("character_id", "")),
            project_id=str(data.get("project_id", "")),
            visual_identity=CharacterIdentity(
                character_id=str(data.get("character_id", "")),
                name=str(identity_data.get("name", "")),
                role=str(identity_data.get("role", "")),
                age=str(identity_data.get("age", "")),
                physical_description=str(identity_data.get("physical_description", "")),
                identity_block=str(identity_data.get("identity_block", "")),
            ),
            voice_rules=VoiceRules(
                cadence=str(voice_data.get("cadence", "")),
                vocabulary=[str(v) for v in voice_data.get("vocabulary", [])],
                forbidden_phrasings=[str(p) for p in voice_data.get("forbidden_phrasings", [])],
                signature_moves=[str(m) for m in voice_data.get("signature_moves", [])],
            ),
            wardrobe_rules=WardrobeRules(
                baseline=str(wardrobe_data.get("baseline", "")),
                act_variants={
                    str(k): str(v) for k, v in wardrobe_data.get("act_variants", {}).items()
                },
            ),
            emotional_arc=EmotionalArc(
                start_state=str(arc_data.get("start_state", "")),
                midpoint_state=str(arc_data.get("midpoint_state", "")),
                end_state=str(arc_data.get("end_state", "")),
                key_turning_points=[str(t) for t in arc_data.get("key_turning_points", [])],
            ),
            relationship_map=[
                RelationshipMap(
                    other_character_id=str(r.get("other_character_id", "")),
                    relation=str(r.get("relation", "")),
                    evolution=str(r.get("evolution", "")),
                )
                for r in relationships_data
            ],
            reference_assets=[str(a) for a in data.get("reference_assets", [])],
            must_not_change=[str(m) for m in data.get("must_not_change", [])],
        )
        return {"character_bible": bible}

    def validate(self, result: dict[str, Any]) -> bool:
        bible = result.get("character_bible")
        if not isinstance(bible, CharacterBible):
            return False
        if not bible.character_id:
            return False
        if not bible.visual_identity.identity_block:
            return False
        return True


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
