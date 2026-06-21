"""Tests for prompt_builder — structured prompt assembly from domain data."""

from __future__ import annotations

from typing import Any

from film_pipeline.generation.prompt_builder import build_structured_prompt

# ── Fixtures ──────────────────────────────────────────────────────────────


def _char_bible() -> dict[str, Any]:
    return {
        "visual_identity": {
            "character_id": "leo",
            "name": "Leo Marchetti",
            "identity_block": (
                "A man in his early 40s, Mediterranean features, short dark hair with grey "
                "at the temples, a weathered face with deep-set brown eyes and a faint scar "
                "across his left eyebrow. Medium build, 1.78m, carries tension in his shoulders."
            ),
        }
    }


def _constitution() -> dict[str, Any]:
    return {
        "visual_language": "painterly natural light, soft key from above-left",
        "camera_philosophy": "observational, intimate close-up distance",
        "tone": "melancholic, painterly",
        "character_truths": [
            {"character_id": "leo", "truth": "Leo carries his past in his posture."}
        ],
    }


def _char_entry(frame_role: str = "front-face", expression: str = "neutral") -> dict[str, Any]:
    return {
        "subject_type": "character",
        "subject_id": "leo",
        "frame_role": frame_role,
        "expression": expression,
        "prompt_text": "",
    }


def _env_entry(frame_role: str = "wide-establishing") -> dict[str, Any]:
    return {
        "subject_type": "environment",
        "subject_id": "studio",
        "frame_role": frame_role,
        "lighting": "cool night",
        "prompt_text": "",
    }


# ── Character prompt tests ────────────────────────────────────────────────


class TestCharacterPrompt:
    def test_full_character_prompt_with_bible(self) -> None:
        prompt = build_structured_prompt(
            _char_entry("front-face", "neutral"),
            character_bible=_char_bible(),
            constitution=_constitution(),
        )
        assert "Mediterranean features" in prompt
        assert "scar across his left eyebrow" in prompt
        assert "1.78m" in prompt
        assert "Front face, looking at camera" in prompt
        assert "painterly natural light" in prompt
        assert "observational" in prompt
        assert "intimate close-up" in prompt
        assert "Same person as in all other frames" in prompt
        assert "Consistent facial features" in prompt

    def test_falls_back_to_constitution_truths_without_bible(self) -> None:
        prompt = build_structured_prompt(
            _char_entry("front-face"),
            character_bible=None,
            constitution=_constitution(),
        )
        assert "Leo carries his past" in prompt

    def test_falls_back_to_prompt_text_when_no_bible_no_truths(self) -> None:
        entry = {**_char_entry(), "prompt_text": "A tall figure in shadow."}
        prompt = build_structured_prompt(entry, character_bible=None, constitution=None)
        assert "A tall figure in shadow" in prompt

    def test_falls_back_to_subject_id_as_last_resort(self) -> None:
        prompt = build_structured_prompt(_char_entry(), character_bible=None, constitution=None)
        assert "leo" in prompt.lower()

    def test_frame_role_front_face(self) -> None:
        prompt = build_structured_prompt(_char_entry("front-face"), character_bible=_char_bible())
        assert "Front face, looking at camera" in prompt

    def test_frame_role_3_4_left(self) -> None:
        prompt = build_structured_prompt(_char_entry("3-4-left"), character_bible=_char_bible())
        assert "Three-quarter angle facing left" in prompt

    def test_frame_role_profile_right(self) -> None:
        prompt = build_structured_prompt(
            _char_entry("profile-right"), character_bible=_char_bible()
        )
        assert "Right profile" in prompt

    def test_unknown_frame_role_uses_title_case(self) -> None:
        prompt = build_structured_prompt(_char_entry("dutch-angle"), character_bible=_char_bible())
        assert "Dutch Angle." in prompt

    def test_expression_neutral_is_omitted_from_blocks(self) -> None:
        prompt = build_structured_prompt(
            _char_entry("front-face", "neutral"), character_bible=_char_bible()
        )
        # "Neutral expression" should NOT appear as a separate block
        # (it's implied by the absence of an explicit expression block)
        assert "Neutral expression." not in prompt
        assert "Relaxed face" not in prompt

    def test_expression_frustrated_appears(self) -> None:
        prompt = build_structured_prompt(
            _char_entry("front-face", "frustrated"), character_bible=_char_bible()
        )
        assert "Frustrated expression" in prompt
        assert "Furrowed brow" in prompt

    def test_identity_reinforcement_standard(self) -> None:
        prompt = build_structured_prompt(_char_entry("3-4-left"), character_bible=_char_bible())
        assert "Same person as in all other frames" in prompt

    def test_identity_reinforcement_i2i_active(self) -> None:
        prompt = build_structured_prompt(
            _char_entry("3-4-left"),
            character_bible=_char_bible(),
            identity_state={"i2i_active": True, "anchor_frame_path": "/tmp/anchor.png"},
        )
        assert "Same person as the anchor frame" in prompt
        assert "Identical facial structure" in prompt
        assert "No variation in identity" in prompt

    def test_global_negatives_appended(self) -> None:
        prompt = build_structured_prompt(_char_entry(), character_bible=_char_bible())
        assert "No text. No logos. No 2D animation" in prompt
        assert "No cartoon" in prompt
        assert "Photorealistic only" in prompt
        assert "No watermarks. No grain" in prompt

    def test_character_prompt_does_not_contain_no_people(self) -> None:
        prompt = build_structured_prompt(_char_entry(), character_bible=_char_bible())
        assert "No people" not in prompt
        assert "No other characters visible" in prompt


# ── Environment prompt tests ──────────────────────────────────────────────


class TestEnvironmentPrompt:
    def test_full_environment_prompt(self) -> None:
        prompt = build_structured_prompt(
            _env_entry("wide-establishing"),
            constitution=_constitution(),
        )
        assert "painterly natural light" in prompt
        assert "Wide establishing shot" in prompt
        assert "canonical view" in prompt
        assert "cool night" in prompt
        assert "melancholic" in prompt
        assert "observational" in prompt
        assert "Same location across all angles" in prompt
        assert "No characters visible" in prompt
        assert "No people" in prompt

    def test_environment_falls_back_to_prompt_text(self) -> None:
        entry = {**_env_entry(), "prompt_text": "A converted warehouse studio."}
        prompt = build_structured_prompt(entry, constitution=None)
        assert "A converted warehouse studio" in prompt

    def test_environment_falls_back_to_notes(self) -> None:
        entry = {**_env_entry(), "prompt_text": "", "notes": "Industrial loft."}
        prompt = build_structured_prompt(entry, constitution=None)
        assert "Industrial loft" in prompt

    def test_environment_falls_back_to_subject_id(self) -> None:
        entry = {**_env_entry(), "prompt_text": "", "notes": ""}
        prompt = build_structured_prompt(entry, constitution=None)
        assert "studio" in prompt.lower()

    def test_environment_lighting_variant(self) -> None:
        prompt = build_structured_prompt(
            _env_entry("lighting-golden-afternoon"),
            constitution=_constitution(),
        )
        assert "Golden afternoon light" in prompt
        assert "long shadows" in prompt

    def test_environment_negatives_include_no_people(self) -> None:
        prompt = build_structured_prompt(_env_entry(), constitution=_constitution())
        assert "No characters visible" in prompt
        assert "No people" in prompt

    def test_environment_reinforcement_always_present(self) -> None:
        prompt = build_structured_prompt(
            _env_entry("alt-angle-corner"), constitution=_constitution()
        )
        assert "Same location across all angles" in prompt
        assert "Consistent geometry" in prompt

    def test_environment_frame_role_wide_establishing(self) -> None:
        prompt = build_structured_prompt(
            _env_entry("wide-establishing"), constitution=_constitution()
        )
        assert "canonical view" in prompt

    def test_environment_frame_role_detail_texture(self) -> None:
        prompt = build_structured_prompt(_env_entry("detail-texture"), constitution=_constitution())
        assert "Extreme close-up" in prompt
        assert "Sharp focus on material detail" in prompt


# ── Generic / prop tests ──────────────────────────────────────────────────


class TestGenericPrompt:
    def test_prop_uses_prompt_text(self) -> None:
        entry = {
            "subject_type": "prop",
            "subject_id": "paintbrush",
            "prompt_text": "A worn wooden paintbrush with dried blue paint.",
        }
        prompt = build_structured_prompt(entry, constitution=_constitution())
        assert "worn wooden paintbrush" in prompt
        assert "Photorealistic" in prompt
        assert "No text. No logos" in prompt

    def test_prop_fallback_when_no_prompt_text(self) -> None:
        entry = {
            "subject_type": "prop",
            "subject_id": "paintbrush",
            "prompt_text": "",
            "asset_type": "prop_sheet",
        }
        prompt = build_structured_prompt(entry, constitution=None)
        assert "prop sheet" in prompt.lower()
        assert "paintbrush" in prompt

    def test_style_entry_includes_constitution_context(self) -> None:
        entry = {
            "subject_type": "style",
            "subject_id": "mood",
            "prompt_text": "Color palette reference.",
        }
        prompt = build_structured_prompt(entry, constitution=_constitution())
        assert "painterly natural light" in prompt
        assert "observational" in prompt
