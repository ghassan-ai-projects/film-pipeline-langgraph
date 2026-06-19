"""Tests for concrete validator implementations."""

from __future__ import annotations

from film_pipeline.schemas._base import ValidationStatus
from film_pipeline.validation.impl.dialogue_voice import DialogueVoiceValidator
from film_pipeline.validation.impl.script_structure import ScriptStructureValidator

# ── ScriptStructureValidator ─────────────────────────────────────────────────


class TestScriptStructureValidator:
    def test_empty_script_blocks(self) -> None:
        v = ScriptStructureValidator()
        report = v.run({"scenes": []})
        assert report.status == ValidationStatus.BLOCKED
        assert any(i.code == "missing_scene_intent" for i in report.blocking_issues)

    def test_valid_script_passes(self) -> None:
        v = ScriptStructureValidator()
        artifact = {
            "scenes": [
                {
                    "scene_id": "sc_001",
                    "scene_heading": "INT. ROOM — DAY",
                    "action_lines": ["A door creaks open.", "She steps inside."],
                    "dialogue": [
                        {
                            "character_id": "alex",
                            "line": "I can't believe you followed me here.",
                            "direction": "(angry)",
                        }
                    ],
                    "intent_ref": "s_001",
                },
                {
                    "scene_id": "sc_002",
                    "scene_heading": "EXT. STREET — NIGHT",
                    "action_lines": ["Rain pours."],
                    "dialogue": [
                        {
                            "character_id": "jordan",
                            "line": "You left me no choice. We need to fight this together.",
                            "direction": "",
                        }
                    ],
                    "intent_ref": "s_002",
                },
            ]
        }
        report = v.run(artifact)
        assert report.status in (ValidationStatus.PASS, ValidationStatus.PASS_WITH_NOTES)

    def test_missing_intent_refs_blocks(self) -> None:
        v = ScriptStructureValidator()
        artifact = {
            "scenes": [
                {
                    "scene_id": "sc_001",
                    "scene_heading": "INT. ROOM",
                    "action_lines": ["Action."],
                    "dialogue": [],
                    "intent_ref": "",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "missing_scene_intent" for i in report.blocking_issues)

    def test_dense_dialogue_warns(self) -> None:
        v = ScriptStructureValidator()
        artifact = {
            "scenes": [
                {
                    "scene_id": "sc_001",
                    "scene_heading": "INT. ROOM",
                    "action_lines": [],
                    "dialogue": [
                        {"character_id": f"c{i}", "line": f"Line {i}", "direction": ""}
                        for i in range(16)
                    ],
                    "intent_ref": "s_001",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "dialogue_dense" for i in report.warnings)

    def test_scoring_no_issues_is_100(self) -> None:
        v = ScriptStructureValidator()
        raw = {"scenes_count": 3, "issues": []}
        assert v.extract_score(raw) == 100.0

    def test_scoring_blocking_reduces_score(self) -> None:
        v = ScriptStructureValidator()
        raw = {
            "scenes_count": 1,
            "issues": [
                {"code": "missing_scene_intent", "severity": "blocking", "message": "x"},
            ],
        }
        assert v.extract_score(raw) == 75.0

    def test_many_action_lines_warns(self) -> None:
        v = ScriptStructureValidator()
        artifact = {
            "scenes": [
                {
                    "scene_id": "sc_001",
                    "scene_heading": "INT. ROOM",
                    "action_lines": [f"Action line {i}" for i in range(12)],
                    "dialogue": [],
                    "intent_ref": "s_001",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "scene_too_long" for i in report.warnings)

    def test_no_conflict_detection(self) -> None:
        """Multiple scenes with no conflict keywords triggers blocking."""
        v = ScriptStructureValidator()
        artifact = {
            "scenes": [
                {
                    "scene_id": "sc_001",
                    "scene_heading": "INT. A",
                    "action_lines": ["Peaceful morning."],
                    "dialogue": [{"character_id": "x", "line": "Nice weather.", "direction": ""}],
                    "intent_ref": "s_001",
                },
                {
                    "scene_id": "sc_002",
                    "scene_heading": "INT. B",
                    "action_lines": ["Quiet afternoon."],
                    "dialogue": [{"character_id": "y", "line": "I agree.", "direction": ""}],
                    "intent_ref": "s_002",
                },
            ]
        }
        report = v.run(artifact)
        # Both scenes lack conflict keywords → >50% → blocking
        assert any(i.code == "no_conflict" for i in report.blocking_issues)


# ── DialogueVoiceValidator ───────────────────────────────────────────────────


class TestDialogueVoiceValidator:
    def test_no_dialogue_is_clean(self) -> None:
        v = DialogueVoiceValidator()
        report = v.run({"scenes": []})
        assert report.status == ValidationStatus.PASS
        assert report.score == 100.0

    def test_exposition_heavy_warns(self) -> None:
        v = DialogueVoiceValidator()
        artifact = {
            "scenes": [
                {
                    "scene_id": "sc_001",
                    "scene_heading": "INT. ROOM",
                    "action_lines": [],
                    "dialogue": [
                        {
                            "character_id": "a",
                            "line": "As you know, the plan is risky.",
                            "direction": "",
                        },
                        {
                            "character_id": "a",
                            "line": "Let me explain why we must act now.",
                            "direction": "",
                        },
                        {"character_id": "b", "line": "Fine.", "direction": ""},
                    ],
                    "intent_ref": "s_001",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "exposition_heavy" for i in report.warnings)

    def test_generic_dialogue_warns(self) -> None:
        v = DialogueVoiceValidator()
        artifact = {
            "scenes": [
                {
                    "scene_id": "sc_001",
                    "scene_heading": "INT. ROOM",
                    "action_lines": [],
                    "dialogue": [
                        {"character_id": "a", "line": "I'm fine.", "direction": ""},
                        {"character_id": "b", "line": "Ok.", "direction": ""},
                        {"character_id": "a", "line": "Let's go.", "direction": ""},
                    ],
                    "intent_ref": "s_001",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "generic_dialogue" for i in report.warnings)

    def test_voice_differentiation_detected(self) -> None:
        v = DialogueVoiceValidator()
        artifact = {
            "scenes": [
                {
                    "scene_id": "sc_001",
                    "scene_heading": "INT. ROOM",
                    "action_lines": [],
                    "dialogue": [
                        {"character_id": "a", "line": "Hi.", "direction": ""},
                        {"character_id": "b", "line": "Hi.", "direction": ""},
                    ],
                    "intent_ref": "s_001",
                }
            ]
        }
        report = v.run(artifact)
        # Characters with identical line lengths trigger voice_inconsistency
        assert any(i.code == "voice_inconsistency" for i in report.blocking_issues)

    def test_distinct_voices_pass(self) -> None:
        v = DialogueVoiceValidator()
        artifact = {
            "scenes": [
                {
                    "scene_id": "sc_001",
                    "scene_heading": "INT. ROOM",
                    "action_lines": [],
                    "dialogue": [
                        {
                            "character_id": "a",
                            "line": "The quantum entanglement matrix has destabilized.",
                            "direction": "",
                        },
                        {"character_id": "b", "line": "What?", "direction": ""},
                    ],
                    "intent_ref": "s_001",
                }
            ]
        }
        report = v.run(artifact)
        # Long line vs short line = distinct voices, should not trigger voice_inconsistency
        assert not any(i.code == "voice_inconsistency" for i in report.blocking_issues)
