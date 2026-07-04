"""Tests for the phase reading builders (Review tab reading pane)."""

from __future__ import annotations

from film_pipeline.tui.view_models import PhaseReading, build_phase_reading


def _script_body() -> dict[str, object]:
    return {
        "schema_version": "v1",
        "scenes": [
            {
                "scene_id": "sc_001",
                "scene_heading": "EXT. FIELD - DAWN",
                "action_lines": ["A courier runs through wet grass."],
                "dialogue": [
                    {
                        "character_id": "mara",
                        "line": "They have to know before nightfall.",
                        "direction": "breathless",
                    }
                ],
                "intent_ref": "s_001",
            }
        ],
        "total_scenes": 1,
        "total_dialogue_lines": 1,
    }


def _matrix_body() -> dict[str, object]:
    return {
        "rows": [
            {
                "shot_id": "shot_0001",
                "scene_id": "sc_001",
                "duration_seconds": 8,
                "priority": "standard",
                "story_function": "inciting image",
                "camera_profile": "wide_establishing",
                "lighting_state": "dawn haze",
                "characters": ["mara"],
                "environment": "field",
                "environment_state": "wet",
                "chaining": {"input_frame_ref": ""},
            },
            {
                "shot_id": "shot_0002",
                "scene_id": "sc_002",
                "duration_seconds": 12,
                "characters": [],
                "environment": "outpost",
                "chaining": {"input_frame_ref": "shot_0001_last_frame"},
            },
        ]
    }


def test_empty_reading_has_no_sections() -> None:
    reading = build_phase_reading("intake", {})
    assert isinstance(reading, PhaseReading)
    assert reading.sections == []
    assert "Nothing to read yet" in reading.headline


def test_script_reads_as_screenplay() -> None:
    reading = build_phase_reading("script", {"script": _script_body()})
    text = reading.as_text()
    assert "READ BEFORE APPROVING" in text
    assert "Screenplay" in text
    assert "EXT. FIELD - DAWN" in text
    assert "A courier runs through wet grass." in text
    assert "MARA (breathless)" in text
    assert "They have to know before nightfall." in text
    assert "1 scene(s)" in text


def test_shot_matrix_digest_lists_every_shot() -> None:
    reading = build_phase_reading("shot_bible", {"shot_matrix": _matrix_body()})
    text = reading.as_text()
    assert "2 shot(s), 20s planned total" in text
    assert "[shot_0001]" in text
    assert "wide_establishing (dawn haze)" in text
    assert "characters: mara" in text
    assert "chained from: shot_0001_last_frame" in text


def test_prompts_section_shows_full_prompt() -> None:
    prompts = [
        {
            "shot_id": "shot_0001",
            "provider": "mock-video-provider",
            "model": "mock-fast",
            "duration_seconds": 8,
            "prompt": "Wide establishing shot of the field at dawn.",
        }
    ]
    reading = build_phase_reading("gen_planning", {}, prompts=prompts)
    text = reading.as_text()
    assert "Generation Prompts" in text
    assert "[shot_0001]  mock-video-provider / mock-fast  ·  8s" in text
    assert "Wide establishing shot of the field at dawn." in text


def test_constitution_and_treatment_and_scene_list_are_readable() -> None:
    bodies: dict[str, dict[str, object]] = {
        "film_constitution": {
            "theme": "Hope against despair.",
            "tone": "Grounded",
            "character_truths": [
                {"character_id": "mara", "truth": "Fears abandonment.", "must_not_change": True}
            ],
        },
        "treatment": {
            "text": "A courier crosses three locations.",
            "themes": ["urgency", "trust"],
            "act_map": {"act1_setup": "The warning arrives."},
        },
        "scene_list": {
            "scenes": [
                {
                    "scene_id": "s_001",
                    "dramatic_function": "Establish stakes.",
                    "conflict": "Courier vs. time",
                    "outcome": "She sets off.",
                }
            ]
        },
    }
    text = build_phase_reading("development", bodies).as_text()
    assert "Theme:" in text
    assert "mara: Fears abandonment. (locked)" in text
    assert "Themes: urgency, trust" in text
    assert "Act1 Setup: The warning arrives." in text
    assert "[s_001]" in text
    assert "conflict: Courier vs. time" in text


def test_reference_index_shows_image_prompts() -> None:
    body = {
        "entries": [
            {
                "reference_id": "ref_001",
                "subject_type": "character",
                "subject_id": "mara",
                "asset_type": "character_identity_sheet",
                "prompt_text": "Mara: weathered gear, tired eyes.",
                "tier": "fast",
                "quality_score": 85.0,
            }
        ]
    }
    text = build_phase_reading("visual_dev", {"reference_index": body}).as_text()
    assert "[ref_001] character: mara" in text
    assert "prompt: Mara: weathered gear, tired eyes." in text
    assert "quality score: 85.0" in text


def test_generation_ledger_rows_show_status_and_errors() -> None:
    body = {
        "rows": [
            {"shot_id": "shot_0001", "status": "completed", "output_refs": ["clips/a.mp4"]},
            {"shot_id": "shot_0002", "status": "failed", "blocking_reason": "provider timeout"},
        ]
    }
    text = build_phase_reading("generation", {"generation_ledger": body}).as_text()
    assert "[shot_0001]  completed  →  clips/a.mp4" in text
    assert "[shot_0002]  failed  (provider timeout)" in text


def test_profile_reading_shows_key_facts() -> None:
    body = {
        "identity": {"title": "Field Warning"},
        "film_type": "narrative",
        "target_runtime_seconds": 20,
        "aspect_ratio": "16:9",
        "delivery_modes": ["mp4"],
        "budget_cap_usd": None,
    }
    text = build_phase_reading("intake", {"project_profile": body}).as_text()
    assert "Title:          Field Warning" in text
    assert "Target runtime: 20s" in text
    assert "Budget cap:     none" in text


def test_unknown_artifacts_fall_back_to_generic_rendering() -> None:
    body = {
        "schema_version": "v1",
        "batch_id": "batch-001",
        "nested": {"estimated_cost_usd": 3.6},
        "items": [{"name": "clip"}, "plain"],
        "empty_list": [],
        "none_value": None,
    }
    text = build_phase_reading("gen_planning", {"mystery_artifact": body}).as_text()
    assert "Mystery Artifact" in text
    assert "batch id: batch-001" in text
    assert "estimated cost usd: 3.6" in text
    assert "• plain" in text
    assert "schema_version" not in text
    assert "empty list" not in text


def test_graph_state_is_never_shown() -> None:
    reading = build_phase_reading("intake", {"graph_state": {"state": {"huge": True}}})
    assert all(section.artifact_id != "graph_state" for section in reading.sections)


def test_empty_rendered_section_is_skipped() -> None:
    reading = build_phase_reading(
        "intake", {"project_constraints": {"schema_version": "v1", "note": None}}
    )
    assert "project_constraints" not in {section.artifact_id for section in reading.sections}


def test_delivery_manifest_is_readable() -> None:
    body = {
        "deliverables": [
            {"name": "master_mp4", "path": "output/film.mp4"},
            {"name": "stills", "path": "output/stills.zip"},
        ]
    }
    text = build_phase_reading("delivery", {"delivery_manifest": body}).as_text()
    assert "Delivery Manifest" in text
    assert "name: master_mp4" in text
    assert "path: output/film.mp4" in text


def test_script_tolerates_malformed_scenes_and_dialogue() -> None:
    body = {
        "scenes": [
            {"scene_heading": "EXT. FIELD - DAWN", "scene_id": "sc_001"},
            "not-a-scene",
            {
                "scene_heading": "EXT. ROAD - DAY",
                "dialogue": ["not-a-line", {"character_id": "mara", "line": "Hurry."}],
            },
        ],
        "total_scenes": 2,
        "total_dialogue_lines": 1,
    }
    text = build_phase_reading("script", {"script": body}).as_text()
    assert "EXT. FIELD - DAWN" in text
    assert "EXT. ROAD - DAY" in text
    assert "MARA" in text
    assert "Hurry." in text


def test_shot_matrix_empty_rows_is_skipped() -> None:
    reading = build_phase_reading("shot_bible", {"shot_matrix": {"rows": []}})
    assert "shot_matrix" not in {section.artifact_id for section in reading.sections}


def test_ledger_empty_rows_is_skipped() -> None:
    reading = build_phase_reading("generation", {"generation_ledger": {"rows": []}})
    assert "generation_ledger" not in {section.artifact_id for section in reading.sections}


def test_reference_entry_without_prompt_omits_prompt_line() -> None:
    body = {
        "entries": [
            {
                "reference_id": "ref_002",
                "subject_type": "environment",
                "subject_id": "outpost",
                "asset_type": "environment_sheet",
                "tier": "fast",
            }
        ]
    }
    text = build_phase_reading("visual_dev", {"reference_index": body}).as_text()
    assert "[ref_002] environment: outpost" in text
    assert "prompt:" not in text
    assert "tier: fast" in text
