"""Tests for EnvironmentBibleAgent."""

from __future__ import annotations

import json
from typing import Any

from film_pipeline.agents.impl.environment_bible_agent import EnvironmentBibleAgent
from film_pipeline.schemas.base import AgentFamily, AgentRole
from film_pipeline.schemas.environment import EnvironmentBible
from film_pipeline.schemas.handoff import AgentRegistration


def _make_agent() -> EnvironmentBibleAgent:
    return EnvironmentBibleAgent(
        AgentRegistration(
            agent_id="environment-bible-agent",
            family=AgentFamily.DEVELOPMENT,
            role=AgentRole.CREATOR,
            capabilities=["environment_design"],
            input_artifacts=["script", "film_constitution"],
            output_artifacts=["environment_bible"],
        )
    )


_VALID_OUTPUT: dict[str, Any] = {
    "environment_id": "studio",
    "project_id": "test-project",
    "name": "The Studio",
    "locked_prompt_block": (
        "A dimly lit artist's studio with tall windows, paint-splattered floors, "
        "and canvases stacked against exposed brick walls."
    ),
    "invariants": ["Tall windows on north wall", "Exposed brick"],
    "zones": [
        {
            "zone_id": "main_floor",
            "description": "Open workspace with easels and paint supplies.",
            "allowed_viewpoints": ["vp_wide", "vp_desk"],
        },
    ],
    "viewpoints": [
        {
            "viewpoint_id": "vp_wide",
            "description": "Wide establishing shot from entrance.",
            "lens": "24mm",
            "framing": "Full room visible",
        },
    ],
    "lighting_states": [
        {
            "state_id": "golden_afternoon",
            "description": "Warm afternoon light through tall windows.",
            "shadow_direction": "Long, eastward",
            "color_temperature": "3200K",
            "primary_source": "Window light",
        },
    ],
    "color_palette": ["#1a1a2e", "#e94560", "#0f3460", "#16213e"],
    "fingerprint": {
        "text": "A creative sanctuary — organized chaos with light as the central element."
    },
    "reference_assets": [],
    "must_not_change": ["locked_prompt_block", "Tall windows"],
}


class TestEnvironmentBibleAgent:
    def test_execute_produces_valid_bible(self) -> None:
        agent = _make_agent()
        result = agent.execute(_VALID_OUTPUT)
        bible = result["environment_bible"]
        assert isinstance(bible, EnvironmentBible)
        assert bible.environment_id == "studio"
        assert bible.locked_prompt_block.startswith("A dimly lit")
        assert len(bible.color_palette) == 4
        assert bible.fingerprint.text.startswith("A creative sanctuary")
        assert len(bible.zones) == 1
        assert bible.zones[0].zone_id == "main_floor"

    def test_validate_passes_for_valid_bible(self) -> None:
        agent = _make_agent()
        result = agent.execute(_VALID_OUTPUT)
        assert agent.validate(result) is True

    def test_validate_fails_for_empty_locked_block(self) -> None:
        agent = _make_agent()
        output = dict(_VALID_OUTPUT)
        output["locked_prompt_block"] = ""
        result = agent.execute(output)
        assert agent.validate(result) is False

    def test_validate_fails_for_empty_fingerprint(self) -> None:
        agent = _make_agent()
        output = dict(_VALID_OUTPUT)
        output["fingerprint"] = {"text": ""}
        result = agent.execute(output)
        assert agent.validate(result) is False

    def test_execute_handles_nested_output(self) -> None:
        agent = _make_agent()
        result = agent.execute({"environment_bible": _VALID_OUTPUT})
        bible = result["environment_bible"]
        assert bible.environment_id == "studio"

    def test_execute_handles_raw_string(self) -> None:
        agent = _make_agent()
        payload: Any = json.dumps({"data": _VALID_OUTPUT})

        result = agent.execute(payload)
        bible = result["environment_bible"]
        assert bible.environment_id == "studio"
        assert bible.fingerprint.text.startswith("A creative sanctuary")

    def test_execute_handles_malformed_model_output_shapes(self) -> None:
        agent = _make_agent()
        invalid_json: Any = "{not json"
        non_dict: Any = object()

        empty_from_json = agent.execute(invalid_json)["environment_bible"]
        empty_from_non_dict = agent.execute(non_dict)["environment_bible"]
        malformed = agent.execute(
            {
                "output": {
                    "environment_id": "studio",
                    "project_id": "p1",
                    "locked_prompt_block": "A real location block.",
                    "zones": "wrong type",
                    "viewpoints": "wrong type",
                    "lighting_states": "wrong type",
                    "color_palette": "wrong type",
                    "fingerprint": "wrong type",
                    "invariants": ["keep", 1],
                    "reference_assets": [1, "ref"],
                    "must_not_change": [None, "windows"],
                }
            }
        )["environment_bible"]

        assert empty_from_json.environment_id == ""
        assert empty_from_non_dict.environment_id == ""
        assert malformed.environment_id == "studio"
        assert malformed.zones == []
        assert malformed.viewpoints == []
        assert malformed.lighting_states == []
        assert malformed.color_palette == []
        assert malformed.fingerprint.text == ""
        assert malformed.invariants == ["keep"]
        assert malformed.reference_assets == ["1", "ref"]
        assert malformed.must_not_change == ["None", "windows"]
        assert agent.validate({"environment_bible": object()}) is False

    def test_execute_handles_empty_input(self) -> None:
        agent = _make_agent()
        result = agent.execute({})
        bible = result["environment_bible"]
        assert isinstance(bible, EnvironmentBible)
        assert bible.environment_id == ""  # structurally valid but empty

    def test_execute_handles_minimal_input(self) -> None:
        agent = _make_agent()
        result = agent.execute(
            {
                "environment_id": "min",
                "project_id": "p",
                "name": "Min",
                "locked_prompt_block": "A minimal space.",
                "fingerprint": {"text": "Minimal."},
            }
        )
        bible = result["environment_bible"]
        assert bible.environment_id == "min"
        assert bible.locked_prompt_block == "A minimal space."
        assert bible.color_palette == []  # optional field
