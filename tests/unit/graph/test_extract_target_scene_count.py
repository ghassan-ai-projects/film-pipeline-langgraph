"""Tests for extracting an explicit target scene count from state or idea text."""

from __future__ import annotations

import pytest

from film_pipeline.graph.nodes import _extract_target_scene_count


class TestExtractTargetSceneCount:
    def test_explicit_state_value_wins(self) -> None:
        assert _extract_target_scene_count({"target_scene_count": 12, "idea": "5 scenes"}) == 12

    def test_parses_digit_scenes(self) -> None:
        assert _extract_target_scene_count({"idea": "A 12-scene epic."}) == 12
        assert _extract_target_scene_count({"idea": "There are 8 scenes total."}) == 8

    def test_parses_number_word_scenes(self) -> None:
        assert _extract_target_scene_count({"idea": "Twelve scenes of wonder."}) == 12
        assert _extract_target_scene_count({"idea": "five scenes"}) == 5

    def test_ignores_invalid_or_missing(self) -> None:
        assert _extract_target_scene_count({"idea": "No scene count here."}) is None
        assert _extract_target_scene_count({}) is None

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Roughly 15 scenes, 3 minutes.", 15),
            ("The film has twenty scenes.", 20),
            ("12-scene structure", 12),
        ],
    )
    def test_various_forms(self, text: str, expected: int) -> None:
        assert _extract_target_scene_count({"idea": text}) == expected
