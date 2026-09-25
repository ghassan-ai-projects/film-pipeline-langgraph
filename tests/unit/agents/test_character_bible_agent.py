"""Tests for CharacterBibleAgent — produces CharacterBible from model output."""

from __future__ import annotations

import json
from typing import Any

from film_pipeline.agents.impl.character_bible_agent import CharacterBibleAgent
from film_pipeline.schemas.base import AgentFamily, AgentRole
from film_pipeline.schemas.character import CharacterBible
from film_pipeline.schemas.handoff import AgentRegistration


def _make_agent() -> CharacterBibleAgent:
    return CharacterBibleAgent(
        AgentRegistration(
            agent_id="character-bible-agent",
            family=AgentFamily.DEVELOPMENT,
            role=AgentRole.CREATOR,
            capabilities=["character_development"],
            input_artifacts=["script", "film_constitution"],
            output_artifacts=["character_bible"],
        )
    )


_VALID_OUTPUT: dict[str, Any] = {
    "character_id": "leo",
    "project_id": "test-project",
    "visual_identity": {
        "character_id": "leo",
        "name": "Leo Marchetti",
        "role": "protagonist",
        "age": "mid-40s",
        "physical_description": "Tall, weathered face, sharp eyes.",
        "identity_block": (
            "A tall man in his mid-40s with a weathered face and sharp, observant eyes. "
            "Dark hair graying at the temples. Dresses in worn but well-tailored suits. "
            "Carries himself with the quiet confidence of someone who has seen too much."
        ),
    },
    "voice_rules": {
        "cadence": "measured, deliberate",
        "vocabulary": ["justice", "choice", "consequence"],
        "forbidden_phrasings": ["I don't know", "whatever"],
        "signature_moves": ["pausing before responding", "repeating the question"],
    },
    "wardrobe_rules": {
        "baseline": "Worn charcoal suit, white shirt with top button undone.",
        "act_variants": {"act_1": "Pristine navy suit", "act_3": "Torn jacket, bloodstained shirt"},
    },
    "emotional_arc": {
        "start_state": "detached and cynical",
        "midpoint_state": "vulnerable, questioning his methods",
        "end_state": "at peace, having chosen humanity over justice",
        "key_turning_points": [
            "Witnesses the death of an innocent",
            "Confronts his former partner",
        ],
    },
    "relationship_map": [
        {
            "other_character_id": "maya",
            "relation": "estranged daughter",
            "evolution": "From hostility to tentative reconciliation",
        },
    ],
    "reference_assets": ["ref-leo-front"],
    "must_not_change": [
        "identity_block",
        "role as protagonist",
        "moral ambiguity",
    ],
}


class TestCharacterBibleAgent:
    def test_execute_produces_valid_bible(self) -> None:
        agent = _make_agent()
        result = agent.execute(_VALID_OUTPUT)
        bible = result["character_bible"]
        assert isinstance(bible, CharacterBible)
        assert bible.character_id == "leo"
        assert bible.visual_identity.identity_block.startswith("A tall man")
        assert bible.voice_rules.cadence == "measured, deliberate"
        assert len(bible.relationship_map) == 1
        assert bible.relationship_map[0].other_character_id == "maya"

    def test_validate_passes_for_valid_bible(self) -> None:
        agent = _make_agent()
        result = agent.execute(_VALID_OUTPUT)
        assert agent.validate(result) is True

    def test_validate_fails_for_empty_identity_block(self) -> None:
        agent = _make_agent()
        output = dict(_VALID_OUTPUT)
        output["visual_identity"] = dict(output["visual_identity"])
        output["visual_identity"]["identity_block"] = ""
        result = agent.execute(output)
        assert agent.validate(result) is False

    def test_execute_handles_nested_output(self) -> None:
        agent = _make_agent()
        result = agent.execute({"character_bible": _VALID_OUTPUT})
        bible = result["character_bible"]
        assert bible.character_id == "leo"

    def test_execute_handles_raw_string(self) -> None:
        agent = _make_agent()
        payload: Any = json.dumps({"data": _VALID_OUTPUT})

        result = agent.execute(payload)
        bible = result["character_bible"]
        assert bible.character_id == "leo"
        assert bible.visual_identity.identity_block.startswith("A tall man")

    def test_execute_handles_malformed_model_output_shapes(self) -> None:
        agent = _make_agent()
        invalid_json: Any = "{not json"
        non_dict: Any = 42

        empty_from_json = agent.execute(invalid_json)["character_bible"]
        empty_from_non_dict = agent.execute(non_dict)["character_bible"]
        malformed = agent.execute(
            {
                "output": {
                    "character_id": "leo",
                    "project_id": "p1",
                    "identity": "wrong type",
                    "voice": "wrong type",
                    "wardrobe": "wrong type",
                    "emotional_arc": "wrong type",
                    "relationships": "wrong type",
                    "reference_assets": [1, "ref"],
                    "must_not_change": [None, "identity"],
                }
            }
        )["character_bible"]

        assert empty_from_json.character_id == ""
        assert empty_from_non_dict.character_id == ""
        assert malformed.character_id == "leo"
        assert malformed.visual_identity.identity_block == ""
        assert malformed.voice_rules.vocabulary == []
        assert malformed.wardrobe_rules.act_variants == {}
        assert malformed.relationship_map == []
        assert malformed.reference_assets == ["1", "ref"]
        assert malformed.must_not_change == ["None", "identity"]
        assert agent.validate({"character_bible": object()}) is False

    def test_execute_handles_empty_input(self) -> None:
        agent = _make_agent()
        result = agent.execute({})
        bible = result["character_bible"]
        assert isinstance(bible, CharacterBible)
        assert bible.character_id == ""  # empty but structurally valid

    def test_execute_handles_minimal_input(self) -> None:
        agent = _make_agent()
        result = agent.execute(
            {
                "character_id": "min",
                "project_id": "p",
                "visual_identity": {"identity_block": "A minimal character."},
                "voice_rules": {},
                "wardrobe_rules": {},
                "emotional_arc": {"start_state": "x", "midpoint_state": "y", "end_state": "z"},
            }
        )
        bible = result["character_bible"]
        assert bible.character_id == "min"
        assert bible.visual_identity.identity_block == "A minimal character."

    def test_prepare_returns_context_dict(self) -> None:
        agent = _make_agent()
        ctx = agent.prepare(
            {
                "project_id": "test",
                "character_id": "leo",
                "character_name": "Leo",
                "script_content": "SCENE 1",
                "constitution_content": "Theme: justice",
            },
            None,
            "create character bible",
        )
        assert ctx["project_id"] == "test"
        assert ctx["character_id"] == "leo"
        assert ctx["script_content"] == "SCENE 1"
