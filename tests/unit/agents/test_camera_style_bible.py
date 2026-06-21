"""Tests for CameraBibleAgent + StyleBibleAgent."""

from __future__ import annotations

from film_pipeline.agents.impl.camera_bible_agent import CameraBibleAgent
from film_pipeline.agents.impl.style_bible_agent import StyleBibleAgent
from film_pipeline.schemas._base import AgentFamily, AgentRole
from film_pipeline.schemas.camera import CameraLanguageBible
from film_pipeline.schemas.handoff import AgentRegistration
from film_pipeline.schemas.style import StyleBible


class TestCameraBibleAgent:
    def test_execute_produces_valid_bible(self) -> None:
        agent = CameraBibleAgent(
            AgentRegistration(
                agent_id="camera-bible-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["camera_design"],
                input_artifacts=["film_constitution"],
                output_artifacts=["camera_language_bible"],
            )
        )
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
        agent = CameraBibleAgent(
            AgentRegistration(
                agent_id="camera-bible-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["camera_design"],
                input_artifacts=["film_constitution"],
                output_artifacts=["camera_language_bible"],
            )
        )
        result = agent.execute({"project_id": "test", "profiles": []})
        assert agent.validate(result) is False


class TestStyleBibleAgent:
    def test_execute_produces_valid_bible(self) -> None:
        agent = StyleBibleAgent(
            AgentRegistration(
                agent_id="style-bible-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["style_definition"],
                input_artifacts=["film_constitution"],
                output_artifacts=["style_bible"],
            )
        )
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
        agent = StyleBibleAgent(
            AgentRegistration(
                agent_id="style-bible-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["style_definition"],
                input_artifacts=["film_constitution"],
                output_artifacts=["style_bible"],
            )
        )
        output = {
            "project_id": "test",
            "color_palette": ["#000"],
            "visual_mood": "dark",
        }
        result = agent.execute(output)
        assert agent.validate(result) is True
