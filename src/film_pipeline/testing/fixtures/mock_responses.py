"""Canned agent responses for mock runtime execution."""

from __future__ import annotations

from typing import Any


def default_mock_responses() -> dict[str, dict[str, Any]]:
    """Return mock responses keyed by agent_id for unambiguous dispatch."""
    return {
        "intake-classifier-agent": {
            "intake": {
                "identity": {
                    "project_id": "demo",
                    "slug": "demo",
                    "title": "Demo Film",
                    "aliases": [],
                },
                # A compact 2-scene / 2-shot demo (~20s of footage). The runtime is
                # set to match that content so it satisfies the Story Scope Contract
                # floor — the old value (300s for 2 scenes) was the exact thin-output
                # mismatch the contract now guards against.
                "target_runtime_seconds": 20,
                "aspect_ratio": "16:9",
                "delivery_modes": ["mp4"],
                "classified_input": "A compact demo film project.",
            }
        },
        "film-constitution-agent": {
            "constitution": {
                "project_id": "demo",
                "theme": "Hope against despair in a fractured world.",
                "tone": "Grounded sci-fi with moments of wonder",
                "emotional_promise": "Audiences will leave feeling inspired and hopeful.",
                "visual_language": "Desaturated palette with neon accents",
                "camera_philosophy": (
                    "Handheld intimacy for character moments, sweeping steadicam for reveals"
                ),
                "quality_bar": "Every shot must serve character or theme.",
                "character_truths": [
                    {"character_id": "mara", "truth": "She fears abandonment more than death."},
                    {
                        "character_id": "elias",
                        "truth": "He will sacrifice anything to protect what he loves.",
                    },
                ],
                "taboo_mistakes": [
                    "Never show the antagonist's face until act 3.",
                    "No jump scares -- tension through atmosphere only.",
                ],
            }
        },
        "treatment-agent": {
            "treatment": {
                "text": (
                    "A lone survivor navigates a post-calamity world, discovering that the "
                    "real threat is not the environment but the remnants of human ambition."
                ),
                "themes": ["survival", "trust", "redemption"],
                "act_map": {
                    "act1_setup": "Mara emerges from shelter after a year underground.",
                    "act2_confrontation": (
                        "Mara discovers a faction hoarding pre-calamity technology."
                    ),
                    "act3_resolution": (
                        "Mara chooses to share the discovery rather than weaponize it."
                    ),
                },
            },
            "scenes": [
                {
                    "scene_id": "s_001",
                    "dramatic_function": "Establish world state and character motivation.",
                    "emotional_shift": "Fear -> cautious hope",
                    "conflict": "Mara vs. the unknown surface world",
                    "outcome": "Mara decides to venture further.",
                },
                {
                    "scene_id": "s_002",
                    "dramatic_function": "Introduce the faction and central conflict.",
                    "emotional_shift": "Curiosity -> distrust",
                    "conflict": "Mara's survival ethic vs. faction's power hoarding",
                    "outcome": "Mara learns of the technology cache.",
                },
            ],
        },
        "screenwriter-agent": {
            "story_bible": {
                "project_id": "demo",
                "logline": (
                    "A year after the collapse, one woman's discovery could rebuild "
                    "civilization or destroy what's left of it."
                ),
                "premise": {
                    "text": (
                        "In a world where trust is the rarest resource, a survivor must decide "
                        "whether to share her discovery or protect it from those who would "
                        "misuse it."
                    ),
                    "dramatic_question": "Can humanity rebuild without repeating its mistakes?",
                },
                "treatment_text": "Mara's journey from isolation to community.",
                "act_map": {
                    "act1_setup": "Mara emerges into a changed world.",
                    "act2_confrontation": "The faction reveals its true nature.",
                    "act3_resolution": "Mara's choice reshapes the future.",
                },
                "scenes": [
                    {
                        "scene_id": "s_001",
                        "dramatic_function": "Opening image.",
                        "emotional_shift": "Fear -> wonder",
                        "conflict": "Mara vs. agoraphobia",
                        "outcome": "Mara takes her first steps.",
                    }
                ],
                "setup_payoff_map": [
                    {
                        "setup_scene_id": "s_001",
                        "payoff_scene_id": "s_020",
                        "description": (
                            "Mara's fear of open spaces resolved when she defends the open field."
                        ),
                    }
                ],
                "unresolved_threads": ["The origin of the collapse."],
                "theme_map": ["survival -> community", "fear -> courage"],
            },
            "script": {
                "project_id": "demo",
                "title": "After the Fall",
                "scenes": [
                    {
                        "scene_id": "sc_001",
                        "scene_heading": "EXT. WASTELAND - DAWN",
                        "action_lines": [
                            (
                                "A hatch creaks open. MARA (30s) squints at the first "
                                "sunlight she's seen in a year."
                            ),
                            "She climbs out slowly, her hand never leaving the hatch handle.",
                        ],
                        "dialogue": [
                            {
                                "character_id": "mara",
                                "line": "It's still here.",
                                "direction": "whispers to herself",
                            }
                        ],
                        "intent_ref": "s_001",
                    },
                    {
                        "scene_id": "sc_002",
                        "scene_heading": "EXT. FACTION OUTPOST - DAY",
                        "action_lines": [
                            "Mara spots smoke on the horizon. She approaches cautiously.",
                        ],
                        "dialogue": [
                            {
                                "character_id": "elias",
                                "line": (
                                    "You're the first outsider in months. Don't make us regret it."
                                ),
                                "direction": "guarded, assessing",
                            }
                        ],
                        "intent_ref": "s_002",
                    },
                ],
                "total_scenes": 2,
                "total_dialogue_lines": 2,
            },
        },
        "reference-strategy-planner": {
            "visual_dev": {
                "project_id": "demo",
                "reference_entries": [
                    {
                        "reference_id": "ref_001",
                        "asset_path": "refs/mara_identity.png",
                        "asset_type": "character_identity_sheet",
                        "subject_type": "character",
                        "subject_id": "mara",
                        "approved_for": ["prompt_anchor"],
                        "quality_score": 85.0,
                        "notes": (
                            "Mara: weathered survival gear, tired eyes, determined expression."
                        ),
                    },
                    {
                        "reference_id": "ref_002",
                        "asset_path": "refs/wasteland_env.png",
                        "asset_type": "environment_establishing",
                        "subject_type": "environment",
                        "subject_id": "wasteland",
                        "approved_for": ["prompt_anchor"],
                        "quality_score": 80.0,
                        "notes": "Vast empty landscape at dawn, muted colors, distant ruins.",
                    },
                ],
            }
        },
        "shot-design-agent": {
            "shot_matrix": {
                "project_id": "demo",
                "rows": [
                    {
                        "shot_id": "shot_0001",
                        "act_id": "act1",
                        "sequence_id": "seq_001",
                        "scene_id": "sc_001",
                        "scene_intent_ref": "s_001",
                        "duration_seconds": 8,
                        "story_function": "inciting image",
                        "characters": ["mara"],
                        "environment": "wasteland",
                        "camera_profile": "wide_establishing",
                        "prompt_ref": "",
                        "generation_order": 0,
                        "chaining": {},
                    },
                    {
                        "shot_id": "shot_0002",
                        "act_id": "act1",
                        "sequence_id": "seq_002",
                        "scene_id": "sc_002",
                        "scene_intent_ref": "s_002",
                        "duration_seconds": 12,
                        "story_function": "conflict_introduction",
                        "characters": ["mara", "elias"],
                        "environment": "outpost_exterior",
                        "camera_profile": "medium_two_shot",
                        "prompt_ref": "",
                        "generation_order": 1,
                        "chaining": {"input_frame_ref": "shot_0001_last_frame"},
                    },
                ],
                "coverage_groups": [
                    {
                        "coverage_group_id": "cg_001",
                        "scene_id": "sc_001",
                        "story_moment": "Mara emerges",
                        "continuity_event": "hatch_opening",
                        "coverage_type": "emotional_reveal",
                        "required_angles": ["wide_master", "close_on_eyes"],
                        "editorial_intent": "Show scale of world vs. Mara's smallness.",
                    }
                ],
            }
        },
        "provider-planning-agent": {
            "generation_plan": {
                "cost_estimate": {
                    "project_id": "demo",
                    "batch_id": "batch-001",
                    "provider": "seedance",
                    "estimated_cost_usd": 3.60,
                    "clip_count": 2,
                    "notes": "2 test clips at $0.18/s, avg 10s each.",
                },
                "shot_groups": [
                    {
                        "shot_id": "shot_0001",
                        "provider": "seedance",
                        "model": "2.0",
                        "mode": "test",
                        "priority": 0,
                        "estimated_cost_usd": 1.44,
                    },
                    {
                        "shot_id": "shot_0002",
                        "provider": "seedance",
                        "model": "2.0",
                        "mode": "test",
                        "priority": 1,
                        "estimated_cost_usd": 2.16,
                    },
                ],
            }
        },
        "clip-validator": {
            "consensus": {
                "review_id": "qc-001",
                "artifact_refs": ["film_constitution", "script", "shot_matrix"],
                "reviewers": [
                    {
                        "model_id": "openrouter/gemini-flash-1.1",
                        "validator_id": "dialogue-voice",
                        "score": 88.0,
                        "status": "pass",
                    },
                    {
                        "model_id": "openrouter/gpt-4o-mini",
                        "validator_id": "script-structure",
                        "score": 92.0,
                        "status": "pass",
                    },
                ],
                "agreement_level": "high",
                "consensus_status": "pass",
                "shared_findings": [
                    "Script maintains consistent tone throughout.",
                    "Shot matrix coverage is adequate for the scene count.",
                ],
                "disagreements": [],
                "orchestrator_recommendation": "Proceed to assembly. All critical checks passed.",
            }
        },
        "failure-handling-agent": {
            "assembly": {
                "cut_id": "review-cut-v1",
                "project_id": "demo",
                "clip_order": [
                    {
                        "shot_id": "shot_0001",
                        "source_asset_ref": "gen/shot_0001.mp4",
                        "in_seconds": 0.0,
                        "out_seconds": 8.0,
                        "coverage_role": "master",
                    },
                    {
                        "shot_id": "shot_0002",
                        "source_asset_ref": "gen/shot_0002.mp4",
                        "in_seconds": 0.0,
                        "out_seconds": 12.0,
                        "coverage_role": "master",
                    },
                ],
                "transitions": [
                    {
                        "from_shot_id": "shot_0001",
                        "to_shot_id": "shot_0002",
                        "transition_type": "cut",
                        "duration_seconds": 0.0,
                    },
                ],
                "audio_plan": {
                    "music_track_refs": [],
                    "sfx_track_refs": [],
                    "dialogue_track_refs": [],
                },
                "color_plan": {"look": "desaturated with warm highlights", "per_scene": {}},
                "duration_total_seconds": 20.0,
            }
        },
    }
