"""Tests for concrete validator implementations."""

from __future__ import annotations

from film_pipeline.schemas._base import ValidationStatus
from film_pipeline.validation.impl.assembly import AssemblyValidator
from film_pipeline.validation.impl.delivery_completeness import DeliveryCompletenessValidator
from film_pipeline.validation.impl.dialogue_voice import DialogueVoiceValidator
from film_pipeline.validation.impl.prompt_readiness import PromptReadinessValidator
from film_pipeline.validation.impl.reference_usability import ReferenceUsabilityValidator
from film_pipeline.validation.impl.scene_continuity import SceneContinuityValidator
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


# ── ReferenceUsabilityValidator ──────────────────────────────────────────────


class TestReferenceUsabilityValidator:
    def test_empty_references_is_clean(self) -> None:
        v = ReferenceUsabilityValidator()
        report = v.run({"entries": []})
        assert report.status == ValidationStatus.PASS
        assert report.score == 100.0

    def test_low_quality_blocks(self) -> None:
        v = ReferenceUsabilityValidator()
        artifact = {
            "entries": [
                {
                    "reference_id": "ref-001",
                    "quality_score": 45,
                    "moderation_risk": "low",
                    "subject_type": "character",
                    "notes": "",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "low_resolution" for i in report.blocking_issues)

    def test_high_moderation_risk_blocks(self) -> None:
        v = ReferenceUsabilityValidator()
        artifact = {
            "entries": [
                {
                    "reference_id": "ref-001",
                    "quality_score": 90,
                    "moderation_risk": "high",
                    "subject_type": "character",
                    "notes": "",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "moderation_risk" for i in report.blocking_issues)

    def test_unknown_subject_type_blocks(self) -> None:
        v = ReferenceUsabilityValidator()
        artifact = {
            "entries": [
                {
                    "reference_id": "ref-001",
                    "quality_score": 90,
                    "moderation_risk": "low",
                    "subject_type": "animal",
                    "notes": "",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "wrong_subject" for i in report.blocking_issues)

    def test_poor_lighting_warns(self) -> None:
        v = ReferenceUsabilityValidator()
        artifact = {
            "entries": [
                {
                    "reference_id": "ref-001",
                    "quality_score": 90,
                    "moderation_risk": "low",
                    "subject_type": "character",
                    "notes": "Image is underexposed and dark.",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "poor_lighting" for i in report.warnings)

    def test_style_mismatch_warns(self) -> None:
        v = ReferenceUsabilityValidator()
        artifact = {
            "entries": [
                {
                    "reference_id": "ref-001",
                    "quality_score": 90,
                    "moderation_risk": "low",
                    "subject_type": "character",
                    "notes": "This reference doesn't match the target style.",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "non_matching_style" for i in report.warnings)

    def test_all_clean_passes(self) -> None:
        v = ReferenceUsabilityValidator()
        artifact = {
            "entries": [
                {
                    "reference_id": "ref-001",
                    "quality_score": 95,
                    "moderation_risk": "low",
                    "subject_type": "character",
                    "notes": "",
                },
                {
                    "reference_id": "ref-002",
                    "quality_score": 88,
                    "moderation_risk": "low",
                    "subject_type": "environment",
                    "notes": "",
                },
            ]
        }
        report = v.run(artifact)
        assert report.status == ValidationStatus.PASS
        assert report.score == 100.0

    def test_scoring_all_pass(self) -> None:
        v = ReferenceUsabilityValidator()
        raw = {
            "total_entries": 3,
            "low_res": 0,
            "high_moderation_risk": 0,
            "wrong_subject_count": 0,
            "poor_lighting_count": 0,
            "non_matching_style_count": 0,
            "issues": [],
        }
        assert v.extract_score(raw) == 100.0

    def test_scoring_with_blockers(self) -> None:
        v = ReferenceUsabilityValidator()
        raw = {
            "total_entries": 2,
            "low_res": 1,
            "high_moderation_risk": 1,
            "wrong_subject_count": 0,
            "poor_lighting_count": 0,
            "non_matching_style_count": 0,
            "issues": [],
        }
        score = v.extract_score(raw)
        assert score < 70.0


# ── PromptReadinessValidator ─────────────────────────────────────────────────


class TestPromptReadinessValidator:
    def test_empty_prompts_is_clean(self) -> None:
        v = PromptReadinessValidator()
        report = v.run({"entries": []})
        assert report.status == ValidationStatus.PASS
        assert report.score == 100.0

    def test_missing_role_and_task_blocks(self) -> None:
        v = PromptReadinessValidator()
        artifact = {
            "entries": [
                {
                    "prompt_id": "prompt-001",
                    "rctco": {"r": "", "c1": "", "t": {}, "c2": [], "o_schema_ref": ""},
                    "artifact_refs": ["artifact:script:sc_001:v1"],
                    "rendered_prompt": "short",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "malformed_rctco" for i in report.blocking_issues)

    def test_missing_artifact_refs_blocks(self) -> None:
        v = PromptReadinessValidator()
        artifact = {
            "entries": [
                {
                    "prompt_id": "prompt-001",
                    "rctco": {
                        "r": "Writer",
                        "c1": "Write a scene",
                        "c2": [],
                        "t": {},
                        "o_schema_ref": "scene_script",
                    },
                    "artifact_refs": [],
                    "rendered_prompt": "short",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "missing_refs" for i in report.blocking_issues)

    def test_prompt_too_long_blocks(self) -> None:
        v = PromptReadinessValidator()
        artifact = {
            "entries": [
                {
                    "prompt_id": "prompt-001",
                    "rctco": {
                        "r": "Writer",
                        "c1": "Write",
                        "c2": [],
                        "t": {},
                        "o_schema_ref": "scene_script",
                    },
                    "artifact_refs": ["ref"],
                    "rendered_prompt": "x" * 9000,
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "prompt_too_long" for i in report.blocking_issues)

    def test_ambiguous_constraints_warns(self) -> None:
        v = PromptReadinessValidator()
        artifact = {
            "entries": [
                {
                    "prompt_id": "prompt-001",
                    "rctco": {
                        "r": "Writer",
                        "c1": "Write",
                        "c2": ["Be creative", "If possible, add humor"],
                        "t": {"example_ref": "ex-001"},
                        "o_schema_ref": "scene_script",
                    },
                    "artifact_refs": ["ref"],
                    "rendered_prompt": "short",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "ambiguous_constraints" for i in report.warnings)

    def test_missing_examples_warns(self) -> None:
        v = PromptReadinessValidator()
        artifact = {
            "entries": [
                {
                    "prompt_id": "prompt-001",
                    "rctco": {
                        "r": "Writer",
                        "c1": "Write",
                        "c2": ["Be concise"],
                        "t": {},
                        "o_schema_ref": "scene_script",
                    },
                    "artifact_refs": ["ref"],
                    "rendered_prompt": "short",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "missing_examples" for i in report.warnings)

    def test_missing_schema_ref_blocks(self) -> None:
        v = PromptReadinessValidator()
        artifact = {
            "entries": [
                {
                    "prompt_id": "prompt-001",
                    "rctco": {"r": "Writer", "c1": "Write", "c2": [], "t": {}, "o_schema_ref": ""},
                    "artifact_refs": ["ref"],
                    "rendered_prompt": "short",
                }
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "malformed_rctco" for i in report.blocking_issues)

    def test_valid_prompt_passes(self) -> None:
        v = PromptReadinessValidator()
        artifact = {
            "entries": [
                {
                    "prompt_id": "prompt-001",
                    "rctco": {
                        "r": "Screenwriter",
                        "c1": "Write scene 1",
                        "c2": ["Keep dialogue natural", "Stay under 3 pages"],
                        "t": {"example_ref": "ex-001", "character_bible": "cb-001"},
                        "o_schema_ref": "scene_script",
                    },
                    "artifact_refs": ["artifact:script:sc_001:v1"],
                    "rendered_prompt": "Write a scene about...",
                }
            ]
        }
        report = v.run(artifact)
        assert report.status == ValidationStatus.PASS


# ── SceneContinuityValidator ─────────────────────────────────────────────────


class TestSceneContinuityValidator:
    def test_empty_shots_is_clean(self) -> None:
        v = SceneContinuityValidator()
        report = v.run({"shots": []})
        assert report.status == ValidationStatus.PASS
        assert report.score == 100.0

    def test_character_state_mismatch_blocks(self) -> None:
        v = SceneContinuityValidator()
        artifact = {
            "shots": [
                {
                    "shot_id": "S001",
                    "characters": [
                        {"character_id": "alex", "state": "angry", "position": "doorway"}
                    ],
                    "lighting": "warm",
                    "props": ["key"],
                    "wardrobe": {"alex": "red_jacket"},
                },
                {
                    "shot_id": "S002",
                    "characters": [{"character_id": "alex", "state": "calm", "position": "desk"}],
                    "lighting": "warm",
                    "props": ["key"],
                    "wardrobe": {"alex": "red_jacket"},
                },
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "character_state_mismatch" for i in report.blocking_issues)

    def test_prop_disappeared_blocks(self) -> None:
        v = SceneContinuityValidator()
        artifact = {
            "shots": [
                {
                    "shot_id": "S001",
                    "characters": [],
                    "lighting": "neutral",
                    "props": ["gun", "badge"],
                    "wardrobe": {},
                },
                {
                    "shot_id": "S002",
                    "characters": [],
                    "lighting": "neutral",
                    "props": ["badge"],
                    "wardrobe": {},
                },
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "prop_disappeared" for i in report.blocking_issues)

    def test_lighting_shift_warns(self) -> None:
        v = SceneContinuityValidator()
        artifact = {
            "shots": [
                {
                    "shot_id": "S001",
                    "characters": [],
                    "lighting": "daylight",
                    "props": [],
                    "wardrobe": {},
                },
                {
                    "shot_id": "S002",
                    "characters": [],
                    "lighting": "night",
                    "props": [],
                    "wardrobe": {},
                },
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "lighting_shift" for i in report.warnings)

    def test_wardrobe_drift_warns(self) -> None:
        v = SceneContinuityValidator()
        artifact = {
            "shots": [
                {
                    "shot_id": "S001",
                    "characters": [{"character_id": "alex", "state": "", "position": ""}],
                    "lighting": "",
                    "props": [],
                    "wardrobe": {"alex": "blue_suit"},
                },
                {
                    "shot_id": "S002",
                    "characters": [{"character_id": "alex", "state": "", "position": ""}],
                    "lighting": "",
                    "props": [],
                    "wardrobe": {"alex": "green_shirt"},
                },
            ]
        }
        report = v.run(artifact)
        assert any(i.code == "wardrobe_minor_drift" for i in report.warnings)

    def test_clean_sequence_passes(self) -> None:
        v = SceneContinuityValidator()
        artifact = {
            "shots": [
                {
                    "shot_id": "S001",
                    "characters": [],
                    "lighting": "daylight",
                    "props": ["cup"],
                    "wardrobe": {},
                },
                {
                    "shot_id": "S002",
                    "characters": [],
                    "lighting": "daylight",
                    "props": ["cup"],
                    "wardrobe": {},
                },
            ]
        }
        report = v.run(artifact)
        assert report.status == ValidationStatus.PASS
        assert report.score == 100.0


# ── AssemblyValidator ────────────────────────────────────────────────────────


class TestAssemblyValidator:
    def test_empty_assembly_blocks(self) -> None:
        v = AssemblyValidator()
        report = v.run({"cut_id": "cut-001", "clip_order": []})
        assert report.status == ValidationStatus.BLOCKED
        assert any(i.code == "missing_clips" for i in report.blocking_issues)
        assert report.score == 0.0

    def test_broken_transition_ref_blocks(self) -> None:
        v = AssemblyValidator()
        artifact = {
            "cut_id": "cut-001",
            "clip_order": [
                {"shot_id": "S001", "in_seconds": 0, "out_seconds": 5},
                {"shot_id": "S002", "in_seconds": 5, "out_seconds": 10},
            ],
            "transitions": [
                {"from_shot_id": "S001", "to_shot_id": "S999", "transition_type": "cut"},
            ],
            "missing_assets": [],
            "audio_plan": {"cue_points": [], "dialogue_track_refs": []},
        }
        report = v.run(artifact)
        assert any(i.code == "broken_transitions" for i in report.blocking_issues)

    def test_duplicate_shot_block(self) -> None:
        v = AssemblyValidator()
        artifact = {
            "cut_id": "cut-001",
            "clip_order": [
                {"shot_id": "S001", "in_seconds": 0, "out_seconds": 5},
                {"shot_id": "S001", "in_seconds": 5, "out_seconds": 10},
            ],
            "transitions": [],
            "missing_assets": [],
            "audio_plan": {"cue_points": [], "dialogue_track_refs": []},
        }
        report = v.run(artifact)
        assert any(i.code == "wrong_order" for i in report.blocking_issues)

    def test_reversed_in_out_blocks(self) -> None:
        v = AssemblyValidator()
        artifact = {
            "cut_id": "cut-001",
            "clip_order": [
                {"shot_id": "S001", "in_seconds": 10, "out_seconds": 5},
            ],
            "transitions": [],
            "missing_assets": [],
            "audio_plan": {"cue_points": [], "dialogue_track_refs": []},
        }
        report = v.run(artifact)
        assert any(i.code == "wrong_order" for i in report.blocking_issues)

    def test_missing_assets_blocks(self) -> None:
        v = AssemblyValidator()
        artifact = {
            "cut_id": "cut-001",
            "clip_order": [
                {"shot_id": "S001", "in_seconds": 0, "out_seconds": 5},
            ],
            "transitions": [],
            "missing_assets": ["clip_S002.mp4", "audio_track_01.wav"],
            "audio_plan": {"cue_points": [], "dialogue_track_refs": []},
        }
        report = v.run(artifact)
        assert any(i.code == "missing_clips" for i in report.blocking_issues)

    def test_valid_assembly_passes(self) -> None:
        v = AssemblyValidator()
        artifact = {
            "cut_id": "cut-001",
            "clip_order": [
                {"shot_id": "S001", "in_seconds": 0, "out_seconds": 5},
                {"shot_id": "S002", "in_seconds": 5, "out_seconds": 10},
            ],
            "transitions": [
                {"from_shot_id": "S001", "to_shot_id": "S002", "transition_type": "dissolve"},
            ],
            "missing_assets": [],
            "audio_plan": {
                "cue_points": [],
                "dialogue_track_refs": [],
                "music_track_refs": ["music_01"],
            },
            "color_plan": {"look": "warm_cinematic", "per_scene": {}},
        }
        report = v.run(artifact)
        assert report.status == ValidationStatus.PASS

    def test_unknown_transition_type_blocks(self) -> None:
        v = AssemblyValidator()
        artifact = {
            "cut_id": "cut-001",
            "clip_order": [
                {"shot_id": "S001", "in_seconds": 0, "out_seconds": 5},
                {"shot_id": "S002", "in_seconds": 5, "out_seconds": 10},
            ],
            "transitions": [
                {"from_shot_id": "S001", "to_shot_id": "S002", "transition_type": "flip"},
            ],
            "missing_assets": [],
            "audio_plan": {"cue_points": [], "dialogue_track_refs": []},
        }
        report = v.run(artifact)
        assert any(i.code == "broken_transitions" for i in report.blocking_issues)


# ── DeliveryCompletenessValidator ────────────────────────────────────────────


class TestDeliveryCompletenessValidator:
    def test_empty_package_blocks(self) -> None:
        v = DeliveryCompletenessValidator()
        report = v.run({"manifest": {"files": []}})
        assert report.status == ValidationStatus.BLOCKED
        assert any(i.code == "empty_package" for i in report.blocking_issues)
        assert report.score == 0.0

    def test_missing_required_files_blocks(self) -> None:
        v = DeliveryCompletenessValidator()
        artifact = {
            "manifest": {
                "files": [
                    {"path": "delivery/final_video.mp4", "kind": "video"},
                ],
                "subtitles": [],
                "stills": [],
                "validation_report_ref": "",
                "cost_report_ref": "",
                "credits_ref": "",
            }
        }
        report = v.run(artifact)
        assert any(i.code == "missing_required_asset" for i in report.blocking_issues)

    def test_missing_subtitles_warns(self) -> None:
        v = DeliveryCompletenessValidator()
        artifact = {
            "manifest": {
                "files": [
                    {"path": "delivery/final_video.mp4", "kind": "video"},
                ],
                "subtitles": [],
                "stills": ["still_01.png"],
                "validation_report_ref": "validation_report.json",
                "cost_report_ref": "cost_report.json",
                "credits_ref": "credits.txt",
            }
        }
        report = v.run(artifact)
        assert any(i.code == "missing_subtitles" for i in report.warnings)

    def test_missing_refs_blocks(self) -> None:
        v = DeliveryCompletenessValidator()
        artifact = {
            "manifest": {
                "files": [
                    {"path": "delivery/final_video.mp4", "kind": "video"},
                    {"path": "delivery/review_cut.mp4", "kind": "video"},
                    {"path": "delivery/subtitles.srt", "kind": "subtitle"},
                    {"path": "delivery/credits.txt", "kind": "text"},
                    {"path": "delivery/validation_report.json", "kind": "report"},
                    {"path": "delivery/cost_report.json", "kind": "report"},
                ],
                "subtitles": ["subtitles.srt"],
                "stills": ["still_01.png"],
                "validation_report_ref": "",
                "cost_report_ref": "",
                "credits_ref": "",
            }
        }
        report = v.run(artifact)
        # Should have 3 blocking issues for missing manifest refs (no missing files)
        blocking_codes = [i.code for i in report.blocking_issues]
        assert blocking_codes.count("missing_required_asset") == 3

    def test_complete_package_passes(self) -> None:
        v = DeliveryCompletenessValidator()
        artifact = {
            "manifest": {
                "files": [
                    {"path": "delivery/final_video.mp4", "kind": "video"},
                    {"path": "delivery/review_cut.mp4", "kind": "video"},
                    {"path": "delivery/subtitles.srt", "kind": "subtitle"},
                    {"path": "delivery/credits.txt", "kind": "text"},
                    {"path": "delivery/validation_report.json", "kind": "report"},
                    {"path": "delivery/cost_report.json", "kind": "report"},
                ],
                "subtitles": ["subtitles.srt"],
                "stills": ["still_01.png"],
                "validation_report_ref": "validation_report.json",
                "cost_report_ref": "cost_report.json",
                "credits_ref": "credits.txt",
            }
        }
        report = v.run(artifact)
        assert report.status == ValidationStatus.PASS
        assert report.score == 100.0
