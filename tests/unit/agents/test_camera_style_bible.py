"""Tests for CameraBibleAgent + StyleBibleAgent."""

from __future__ import annotations

import json
from typing import Any

from film_pipeline.agents.impl.camera_bible_agent import CameraBibleAgent
from film_pipeline.agents.impl.style_bible_agent import StyleBibleAgent
from film_pipeline.schemas._base import AgentFamily, AgentRole
from film_pipeline.schemas.camera import CameraLanguageBible
from film_pipeline.schemas.handoff import AgentRegistration
from film_pipeline.schemas.style import StyleBible


def _camera_agent() -> CameraBibleAgent:
    return CameraBibleAgent(
        AgentRegistration(
            agent_id="camera-bible-agent",
            family=AgentFamily.DEVELOPMENT,
            role=AgentRole.CREATOR,
            capabilities=["camera_design"],
            input_artifacts=["film_constitution"],
            output_artifacts=["camera_language_bible"],
        )
    )


def _style_agent() -> StyleBibleAgent:
    return StyleBibleAgent(
        AgentRegistration(
            agent_id="style-bible-agent",
            family=AgentFamily.DEVELOPMENT,
            role=AgentRole.CREATOR,
            capabilities=["style_definition"],
            input_artifacts=["film_constitution"],
            output_artifacts=["style_bible"],
        )
    )


class TestCameraBibleAgent:
    def test_execute_produces_valid_bible(self) -> None:
        agent = _camera_agent()
        output = {
            "project_id": "test",
            "profiles": [
                {
                    "profile_id": "observational",
                    "use_case": "Dialogue scenes",
                    "lens": "35mm prime",
                    "framing": "Rule of thirds, left-weighted",
                    "movement": "Static, occasional slow push-in",
                    "depth_of_field": "Shallow, f/2.0",
                    "composition_rules": ["Rule of thirds"],
                    "transition_rules": ["Cut on action"],
                    "emotional_meaning": "Intimate, observational",
                }
            ],
            "default_profile_id": "observational",
        }
        result = agent.execute(output)
        bible = result["camera_bible"]
        assert isinstance(bible, CameraLanguageBible)
        assert len(bible.profiles) == 1
        assert bible.profiles[0].lens == "35mm prime"

    def test_validate_fails_for_empty_profiles(self) -> None:
        agent = _camera_agent()
        result = agent.execute({"project_id": "test", "profiles": []})
        assert agent.validate(result) is False

    def test_prepare_returns_camera_context(self) -> None:
        agent = _camera_agent()

        prepared = agent.prepare(
            {"project_id": "p1", "camera_philosophy": "patient observational framing"},
            kb_context=object(),
            task="build camera bible",
        )

        assert prepared == {
            "project_id": "p1",
            "camera_philosophy": "patient observational framing",
            "task": "build camera bible",
        }

    def test_execute_accepts_json_string_and_nested_data(self) -> None:
        agent = _camera_agent()
        payload: Any = json.dumps(
            {
                "data": {
                    "project_id": "p1",
                    "profiles": [
                        {
                            "profile_id": "wide",
                            "composition_rules": ["negative space", 9],
                            "transition_rules": ["hard cut", None],
                        }
                    ],
                    "default_profile_id": "wide",
                }
            }
        )

        bible = agent.execute(payload)["camera_bible"]

        assert bible.project_id == "p1"
        assert bible.profiles[0].composition_rules == ["negative space", "9"]
        assert bible.profiles[0].transition_rules == ["hard cut", "None"]

    def test_execute_rejects_malformed_camera_shapes(self) -> None:
        agent = _camera_agent()

        invalid_json: Any = "{not json"
        non_dict: Any = ["not", "a", "dict"]
        malformed = agent.execute(
            {
                "camera_bible": "wrong type",
                "profiles": "not a list",
            }
        )["camera_bible"]

        assert agent.execute(invalid_json)["camera_bible"].profiles == []
        assert agent.execute(non_dict)["camera_bible"].profiles == []
        assert malformed.profiles == []
        assert agent.validate({"camera_bible": object()}) is False


class TestStyleBibleAgent:
    def test_execute_produces_valid_bible(self) -> None:
        agent = _style_agent()
        output = {
            "project_id": "test",
            "color_palette": ["#1a1a2e", "#e94560"],
            "texture": "gritty",
            "grain": "16mm",
            "visual_mood": "melancholic",
            "reference_stills": [],
            "must_not_change": ["color_palette"],
        }
        result = agent.execute(output)
        bible = result["style_bible"]
        assert isinstance(bible, StyleBible)
        assert len(bible.color_palette) == 2

    def test_validate_passes(self) -> None:
        agent = _style_agent()
        output = {
            "project_id": "test",
            "color_palette": ["#000"],
            "visual_mood": "dark",
        }
        result = agent.execute(output)
        assert agent.validate(result) is True

    def test_prepare_returns_style_context(self) -> None:
        agent = _style_agent()

        prepared = agent.prepare(
            {
                "project_id": "p1",
                "visual_language": "grounded naturalism",
                "tone": "uneasy",
                "palette_hint": "steel, amber",
            },
            kb_context=object(),
            task="build style bible",
        )

        assert prepared == {
            "project_id": "p1",
            "visual_language": "grounded naturalism",
            "tone": "uneasy",
            "palette_hint": "steel, amber",
            "task": "build style bible",
        }

    def test_execute_accepts_json_string_and_nested_output(self) -> None:
        agent = _style_agent()
        payload: Any = json.dumps(
            {
                "output": {
                    "project_id": "p1",
                    "color_palette": ["#101820", 42],
                    "visual_mood": "restrained",
                    "reference_stills": ["still-1", 7],
                    "must_not_change": ["mood", None],
                }
            }
        )

        bible = agent.execute(payload)["style_bible"]

        assert bible.project_id == "p1"
        assert bible.color_palette == ["#101820", "42"]
        assert bible.reference_stills == ["still-1", "7"]
        assert bible.must_not_change == ["mood", "None"]

    def test_execute_rejects_malformed_style_shapes(self) -> None:
        agent = _style_agent()

        invalid_json: Any = "{not json"
        non_dict: Any = ("not", "a", "dict")
        malformed = agent.execute(
            {
                "style_bible": "wrong type",
                "project_id": "p1",
                "color_palette": "not a list",
            }
        )["style_bible"]

        assert agent.execute(invalid_json)["style_bible"].project_id == ""
        assert agent.execute(non_dict)["style_bible"].project_id == ""
        assert malformed.color_palette == []
        assert agent.validate({"style_bible": object()}) is False
        assert agent.validate(agent.execute({"project_id": "", "visual_mood": "moody"})) is False
        assert agent.validate(agent.execute({"project_id": "p1", "color_palette": []})) is False
