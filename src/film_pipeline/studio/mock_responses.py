"""Canned agent responses for mock runtime execution.

The demo film must be internally consistent: the structure-extractor brief,
the shot-design matrix, and the provider plan are three views of one film.
``_demo_movements`` is the authority — the matrix rows and plan groups are
generated from it so Gate A (shot counts per movement), the runtime tolerance
check, and planning completeness all pass on the mock happy path.
"""

from __future__ import annotations

from typing import Any

_SEEDANCE_RATE_USD_PER_SECOND = 0.18

# The demo film's single source of truth: per-movement shot durations.
# Constraints baked into these numbers:
#   - total runtime 104s == 16 shots x 6.5s (standard pacing), so
#     ``brief_runtime_inconsistent`` passes;
#   - row durations sum to 104s, so Gate A's runtime tolerance passes;
#   - counts match ``structure-extractor-agent``'s canned brief movements.
_DEMO_MOVEMENT_DURATIONS: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("act_1", (6, 6, 7, 6, 7)),
    ("act_2", (6, 7, 6, 7, 6)),
    ("act_3", (6, 6, 7, 7, 7, 7)),
)

_DEMO_RUNTIME_SECONDS = 104

_STORY_FUNCTIONS: tuple[str, ...] = (
    "inciting image",
    "conflict_introduction",
    "escalation",
    "turning_point",
    "revelation",
)

_CAMERA_PROFILES: tuple[str, ...] = (
    "wide_establishing",
    "medium_two_shot",
    "close_on_eyes",
)


def _demo_shot_rows() -> list[dict[str, Any]]:
    """Build matrix rows matching the demo execution brief exactly."""
    rows: list[dict[str, Any]] = []
    order = 0
    for movement_id, durations in _DEMO_MOVEMENT_DURATIONS:
        previous_shot = ""
        for index, seconds in enumerate(durations, start=1):
            order += 1
            shot_id = f"shot_{order:04d}"
            row: dict[str, Any] = {
                "shot_id": shot_id,
                "act_id": movement_id,
                "sequence_id": f"seq_{order:03d}",
                # Both script scenes stay covered across the film.
                "scene_id": "sc_001" if index % 2 == 1 else "sc_002",
                "scene_intent_ref": f"s_{(order - 1) % 2 + 1:03d}",
                "duration_seconds": seconds,
                "story_function": _STORY_FUNCTIONS[(order - 1) % len(_STORY_FUNCTIONS)],
                "characters": ["mara"] if index % 2 == 1 else ["mara", "elias"],
                "environment": "wasteland" if index % 2 == 1 else "outpost_exterior",
                "camera_profile": _CAMERA_PROFILES[(order - 1) % len(_CAMERA_PROFILES)],
                "prompt_ref": "",
                "generation_order": order - 1,
                "chaining": {},
            }
            if previous_shot:
                row["chaining"] = {"input_frame_ref": f"{previous_shot}_last_frame"}
            rows.append(row)
            previous_shot = shot_id
    return rows


def _demo_shot_groups() -> list[dict[str, Any]]:
    """Build a provider-plan entry for every demo matrix row."""
    groups: list[dict[str, Any]] = []
    order = 0
    for _movement_id, durations in _DEMO_MOVEMENT_DURATIONS:
        for seconds in durations:
            groups.append(
                {
                    "shot_id": f"shot_{order + 1:04d}",
                    "provider": "seedance",
                    "model": "2.0",
                    "mode": "test",
                    "priority": order,
                    "estimated_cost_usd": round(seconds * _SEEDANCE_RATE_USD_PER_SECOND, 2),
                }
            )
            order += 1
    return groups


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
                            (
                                "She climbs out slowly, her hand never leaving the hatch "
                                "handle, every muscle tense with the struggle to trust "
                                "the silence."
                            ),
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
                            (
                                "Mara spots smoke on the horizon. She approaches "
                                "cautiously, tension in every step of the standoff."
                            ),
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
        "structure-extractor-agent": {
            "execution_brief": {
                "project_id": "demo",
                # 16 shots x 6.5s standard pacing = 104s; matches the canned
                # matrix rows exactly (see _DEMO_MOVEMENT_DURATIONS).
                "target_runtime_seconds": _DEMO_RUNTIME_SECONDS,
                "movements": [
                    {
                        "movement_id": "act_1",
                        "shot_count": 5,
                        "duration_range_seconds": [6, 7],
                        "description": "Setup",
                    },
                    {
                        "movement_id": "act_2",
                        "shot_count": 5,
                        "duration_range_seconds": [6, 7],
                        "description": "Confrontation",
                    },
                    {
                        "movement_id": "act_3",
                        "shot_count": 6,
                        "duration_range_seconds": [6, 7],
                        "description": "Resolution",
                    },
                ],
                "mandatory_anchors": ["mara", "elias"],
                "environment_progression": ["wasteland", "outpost"],
                "pacing_style": "standard",
            }
        },
        "orchestrator-agent": {
            "orchestrator_decision": {
                "action": "approve",
                "feedback": "Looks good — proceed.",
                "preserve": [],
                "reasoning": "No blocking issues detected.",
                "quality_score": 4,
                "critical_issues": [],
            }
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
                "rows": _demo_shot_rows(),
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
                    "estimated_cost_usd": 18.72,
                    "clip_count": 16,
                    "notes": "16 demo clips at $0.18/s (Seedance), 104s total runtime.",
                },
                "shot_groups": _demo_shot_groups(),
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
        # --- Visual-development bible creators ---------------------------
        # These four are invoked through MCP, not a graph phase, so their
        # canned payloads are inert to the graph path. They are the single
        # mock authority for those tools — the tools previously carried their
        # own copies, keyed at call time by the ids below.
        "camera-bible-agent": {
            "camera_bible": {
                "project_id": "demo",
                "profiles": [
                    {
                        "profile_id": "default",
                        "use_case": "General shots",
                        "lens": "35mm prime",
                        "framing": "Rule of thirds",
                        "movement": "Static or slow push-in",
                        "depth_of_field": "Shallow, f/2.0",
                        "composition_rules": ["Rule of thirds"],
                        "transition_rules": ["Cut on action"],
                        "emotional_meaning": "Observational, intimate",
                    }
                ],
                "default_profile_id": "default",
            }
        },
        "character-bible-agent": {
            "character_bible": {
                "character_id": "lead",
                "project_id": "demo",
                "visual_identity": {
                    "character_id": "lead",
                    "name": "Lead",
                    "role": "protagonist",
                    "age": "unknown",
                    "physical_description": "Generated in mock mode.",
                    "identity_block": (
                        "A wiry figure in their 30s with a scar over the left brow — "
                        "generated in mock mode. Replace with real model output."
                    ),
                },
                "voice_rules": {
                    "cadence": "measured",
                    "vocabulary": [],
                    "forbidden_phrasings": [],
                    "signature_moves": [],
                },
                "wardrobe_rules": {"baseline": "", "act_variants": {}},
                "emotional_arc": {
                    "start_state": "unknown",
                    "midpoint_state": "unknown",
                    "end_state": "unknown",
                    "key_turning_points": [],
                },
                "relationship_map": [],
                "reference_assets": [],
                "must_not_change": ["identity_block"],
            }
        },
        "environment-bible-agent": {
            "environment_bible": {
                "environment_id": "wasteland",
                "project_id": "demo",
                "name": "Wasteland",
                "locked_prompt_block": "A vast, empty wasteland at dawn — generated in mock mode.",
                "invariants": [],
                "zones": [],
                "viewpoints": [],
                "lighting_states": [],
                "color_palette": ["#1a1a2e", "#e94560"],
                "fingerprint": {"text": "The Wasteland — mock mode."},
                "reference_assets": [],
                "must_not_change": ["locked_prompt_block"],
            }
        },
        "style-bible-agent": {
            "style_bible": {
                "project_id": "demo",
                "color_palette": ["#1a1a2e", "#e94560", "#0f3460", "#16213e"],
                "texture": "gritty, painterly",
                "grain": "subtle 16mm grain",
                "visual_mood": "melancholic, high-contrast",
                "reference_stills": [],
                "must_not_change": ["color_palette"],
            }
        },
    }
