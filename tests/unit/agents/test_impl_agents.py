"""Tests for concrete agent implementations."""

from __future__ import annotations

from film_pipeline.agents.impl.constitution_agent import ConstitutionAgent
from film_pipeline.agents.impl.development_agent import DevelopmentAgent
from film_pipeline.agents.impl.intake_agent import IntakeAgent
from film_pipeline.agents.impl.screenwriter_agent import ScreenwriterAgent
from film_pipeline.schemas._base import AgentFamily, AgentRole, FilmType
from film_pipeline.schemas.film_constitution import FilmConstitution
from film_pipeline.schemas.handoff import AgentRegistration
from film_pipeline.schemas.kb import KBContextPacket
from film_pipeline.schemas.project import ProjectProfile
from film_pipeline.schemas.script import Script
from film_pipeline.schemas.story_bible import SceneList, StoryBible, Treatment


def _make_kb() -> KBContextPacket:
    return KBContextPacket(
        kb_context_id="kbctx:test:v1",
        project_id="test-proj",
        phase="constitution",
        agent_id="test-agent",
        task="Test task",
    )


# ── ConstitutionAgent ────────────────────────────────────────────────────────


class TestConstitutionAgent:
    def test_execute_produces_constitution(self) -> None:
        agent = ConstitutionAgent(_make_contract("film-constitution-agent"))
        output = {
            "constitution": {
                "project_id": "p1",
                "theme": "Redemption through sacrifice",
                "tone": "melancholic, painterly",
                "emotional_promise": "Catharsis",
                "visual_language": "wide, shallow depth of field",
                "camera_philosophy": "observational, breath-paced",
                "quality_bar": "Every frame must feel like a painting.",
                "character_truths": [
                    {"character_id": "elara", "truth": "She cannot lie."},
                ],
                "taboo_mistakes": ["Deus ex machina endings"],
            }
        }
        result = agent.execute(output)
        assert isinstance(result["constitution"], FilmConstitution)
        c: FilmConstitution = result["constitution"]
        assert c.theme == "Redemption through sacrifice"
        assert c.tone == "melancholic, painterly"
        assert len(c.character_truths) == 1
        assert c.character_truths[0].character_id == "elara"

    def test_execute_flat_keys(self) -> None:
        agent = ConstitutionAgent(_make_contract("film-constitution-agent"))
        output = {
            "project_id": "p2",
            "theme": "Hope",
            "tone": "dark",
            "emotional_promise": "uplift",
            "visual_language": "handheld",
            "camera_philosophy": "intimate",
            "quality_bar": "high",
            "character_truths": [],
            "taboo_mistakes": [],
        }
        result = agent.execute(output)
        assert isinstance(result["constitution"], FilmConstitution)

    def test_validate_rejects_empty_theme(self) -> None:
        agent = ConstitutionAgent(_make_contract("film-constitution-agent"))
        output = {
            "constitution": {
                "project_id": "p1",
                "theme": "",
                "tone": "cool",
                "emotional_promise": "",
                "visual_language": "",
                "camera_philosophy": "",
                "quality_bar": "",
                "character_truths": [],
                "taboo_mistakes": [],
            }
        }
        result = agent.execute(output)
        assert not agent.validate(result)

    def test_validate_rejects_missing_constitution(self) -> None:
        agent = ConstitutionAgent(_make_contract("film-constitution-agent"))
        assert not agent.validate({})

    def test_prepare_extracts_idea_from_state(self) -> None:
        agent = ConstitutionAgent(_make_contract("film-constitution-agent"))
        inputs = agent.prepare(
            {"project_id": "p1", "idea": "A robot learns to paint."},
            _make_kb(),
            "Create constitution",
        )
        assert inputs["idea"] == "A robot learns to paint."
        assert inputs["project_id"] == "p1"


# ── DevelopmentAgent ─────────────────────────────────────────────────────────


class TestDevelopmentAgent:
    def test_execute_produces_treatment_and_scenes(self) -> None:
        agent = DevelopmentAgent(_make_contract("treatment-agent"))
        output = {
            "development": {
                "treatment": {
                    "text": "A sweeping tale of redemption...",
                    "themes": ["hope", "sacrifice"],
                    "act_map": {
                        "act1_setup": "The fall",
                        "act2_confrontation": "The climb",
                        "act3_resolution": "The summit",
                    },
                },
                "scenes": [
                    {
                        "scene_id": "s_001",
                        "dramatic_function": "Establish the world.",
                        "emotional_shift": "curiosity → awe",
                        "conflict": "internal doubt",
                        "outcome": "protagonist commits.",
                    },
                    {
                        "scene_id": "s_002",
                        "dramatic_function": "Introduce antagonist.",
                        "emotional_shift": "trust → suspicion",
                        "conflict": "hidden agenda",
                        "outcome": "tension set.",
                    },
                ],
            }
        }
        result = agent.execute(output)
        assert isinstance(result["treatment"], Treatment)
        assert isinstance(result["scene_list"], SceneList)
        assert result["treatment"].text.startswith("A sweeping tale")
        assert len(result["scene_list"].scenes) == 2
        assert result["scene_list"].scenes[0].scene_id == "s_001"

    def test_validate_rejects_empty_scenes(self) -> None:
        agent = DevelopmentAgent(_make_contract("treatment-agent"))
        output = {
            "development": {
                "treatment": {"text": "Story here", "themes": [], "act_map": {}},
                "scenes": [],
            }
        }
        result = agent.execute(output)
        assert not agent.validate(result)

    def test_validate_rejects_missing_treatment(self) -> None:
        agent = DevelopmentAgent(_make_contract("treatment-agent"))
        assert not agent.validate({})


# ── ScreenwriterAgent ────────────────────────────────────────────────────────


class TestScreenwriterAgent:
    def test_execute_produces_bible_and_script(self) -> None:
        agent = ScreenwriterAgent(_make_contract("screenwriter-agent"))
        output = _make_screenwriter_output()
        result = agent.execute(output)
        assert isinstance(result["story_bible"], StoryBible)
        assert isinstance(result["script"], Script)
        bible: StoryBible = result["story_bible"]
        script: Script = result["script"]
        assert bible.logline.text == "A broken pilot must fly one last mission."
        assert script.total_scenes == 1
        assert script.total_dialogue_lines == 1
        assert script.scenes[0].dialogue[0].character_id == "mara"

    def test_execute_flat_keys(self) -> None:
        agent = ScreenwriterAgent(_make_contract("screenwriter-agent"))
        output = _make_flat_screenwriter_output()
        result = agent.execute(output)
        assert isinstance(result["story_bible"], StoryBible)
        assert isinstance(result["script"], Script)

    def test_validate_rejects_empty_script(self) -> None:
        agent = ScreenwriterAgent(_make_contract("screenwriter-agent"))
        output = {
            "script_output": {
                "story_bible": {
                    "logline": "",
                    "hook": "",
                    "premise": "",
                    "dramatic_question": "",
                    "act_map": {"act1_setup": "", "act2_confrontation": "", "act3_resolution": ""},
                    "treatment_text": "",
                    "themes": [],
                    "scene_list": [],
                    "setup_payoff_map": [],
                    "unresolved_threads": [],
                    "theme_map": [],
                    "project_id": "p1",
                },
                "script": {"project_id": "p1", "title": "", "scenes": []},
            }
        }
        result = agent.execute(output)
        assert not agent.validate(result)


def _make_screenwriter_output() -> dict[str, object]:
    return {
        "script_output": {
            "story_bible": {
                "project_id": "p1",
                "logline": "A broken pilot must fly one last mission.",
                "hook": "",
                "premise": "What if your last flight was your first real choice?",
                "dramatic_question": "Will she choose duty or freedom?",
                "act_map": {
                    "act1_setup": "Crash landing",
                    "act2_confrontation": "The mission",
                    "act3_resolution": "The choice",
                },
                "treatment_text": "Mara, a disgraced pilot...",
                "themes": ["redemption", "freedom"],
                "scene_list": [
                    {
                        "scene_id": "s_001",
                        "dramatic_function": "Opening image",
                        "emotional_shift": "despair → hope",
                        "conflict": "Mara vs. her past",
                        "outcome": "She accepts the mission.",
                    }
                ],
                "setup_payoff_map": [],
                "unresolved_threads": [],
                "theme_map": [],
            },
            "script": {
                "project_id": "p1",
                "title": "Final Approach",
                "scenes": [
                    {
                        "scene_id": "sc_001",
                        "scene_heading": "INT. COCKPIT — NIGHT",
                        "action_lines": ["Rain taps the windshield."],
                        "dialogue": [
                            {
                                "character_id": "mara",
                                "line": "Tower, this is Nightbird. Requesting final approach.",
                                "direction": "(steady)",
                            }
                        ],
                        "intent_ref": "s_001",
                    }
                ],
            },
        }
    }


def _make_flat_screenwriter_output() -> dict[str, object]:
    return {
        "story_bible": {
            "project_id": "p2",
            "logline": "A logline.",
            "hook": "",
            "premise": "",
            "dramatic_question": "",
            "act_map": {"act1_setup": "A", "act2_confrontation": "B", "act3_resolution": "C"},
            "treatment_text": "",
            "themes": [],
            "scene_list": [],
            "setup_payoff_map": [],
            "unresolved_threads": [],
            "theme_map": [],
        },
        "script": {
            "project_id": "p2",
            "title": "T",
            "scenes": [
                {
                    "scene_id": "sc_001",
                    "scene_heading": "EXT. PARK",
                    "action_lines": [],
                    "dialogue": [{"character_id": "x", "line": "Hi", "direction": ""}],
                    "intent_ref": "",
                }
            ],
        },
    }


# ── IntakeAgent ──────────────────────────────────────────────────────────────


class TestIntakeAgent:
    def test_execute_produces_profile(self) -> None:
        agent = IntakeAgent(_make_contract("intake-classifier-agent"))
        output = {
            "intake": {
                "project_id": "p1",
                "title": "The Last Garden",
                "slug": "the-last-garden",
                "target_runtime_seconds": 300,
                "aspect_ratio": "16:9",
                "delivery_modes": ["mp4"],
                "provider_preferences": [],
                "human_owner": "",
            }
        }
        result = agent.execute(output)
        assert isinstance(result["profile"], ProjectProfile)
        p: ProjectProfile = result["profile"]
        assert p.identity.title == "The Last Garden"
        assert p.target_runtime_seconds == 300

    def test_validate_rejects_empty_title(self) -> None:
        agent = IntakeAgent(_make_contract("intake-classifier-agent"))
        output = {
            "intake": {
                "project_id": "p1",
                "title": "",
                "slug": "",
                "target_runtime_seconds": 0,
            }
        }
        result = agent.execute(output)
        assert not agent.validate(result)

    def test_execute_normalizes_invalid_one_second_runtime(self) -> None:
        agent = IntakeAgent(_make_contract("intake-classifier-agent"))
        output = {
            "intake": {
                "project_id": "p1",
                "title": "Signal Loss",
                "slug": "signal-loss",
                "target_runtime_seconds": 1,
            }
        }

        result = agent.execute(output)

        profile = result["profile"]
        assert isinstance(profile, ProjectProfile)
        assert profile.target_runtime_seconds == 300

    def test_execute_uses_minutes_when_seconds_missing(self) -> None:
        agent = IntakeAgent(_make_contract("intake-classifier-agent"))
        output = {
            "intake": {
                "project_id": "p1",
                "title": "Signal Loss",
                "slug": "signal-loss",
                "target_runtime_minutes": 7,
            }
        }

        result = agent.execute(output)

        profile = result["profile"]
        assert isinstance(profile, ProjectProfile)
        assert profile.target_runtime_seconds == 420

    def test_execute_coerces_valid_film_type(self) -> None:
        agent = IntakeAgent(_make_contract("intake-classifier-agent"))
        output = {
            "intake": {
                "project_id": "p1",
                "title": "Signal Loss",
                "slug": "signal-loss",
                "film_type": "short_drama",
                "target_runtime_seconds": 300,
            }
        }

        result = agent.execute(output)

        profile = result["profile"]
        assert isinstance(profile, ProjectProfile)
        assert profile.film_type == FilmType.SHORT_DRAMA


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_contract(agent_id: str) -> AgentRegistration:
    return AgentRegistration(
        agent_id=agent_id,
        family=AgentFamily.DEVELOPMENT,
        role=AgentRole.CREATOR,
        capabilities=[],
        input_artifacts=[],
        output_artifacts=[],
        allowed_kb_domains=[],
        blocked_kb_domains=[],
        reviewed_by=[],
        failure_modes=[],
    )
