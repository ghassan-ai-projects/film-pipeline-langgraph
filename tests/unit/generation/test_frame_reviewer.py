"""Tests for frame_reviewer — Gemini per-frame validation."""

from __future__ import annotations

import json
from pathlib import Path

from film_pipeline.generation.frame_reviewer import (
    review_frame,
    should_review_frame,
)

from ._helpers import _mock_opener


def _make_png(tmp_path: Path, name: str = "test.png") -> Path:
    """Create a small valid PNG for testing."""
    from PIL import Image

    path = tmp_path / name
    img = Image.new("RGB", (512, 512), (100, 150, 200))
    for x in range(0, 512, 64):
        for y in range(0, 512, 64):
            img.putpixel((x, y), (x % 256, y % 256, (x + y) % 256))
    img.save(path)
    return path


class TestShouldReviewFrame:
    def test_front_face_always_reviewed(self) -> None:
        assert (
            should_review_frame({"subject_type": "character", "frame_role": "front-face"}) is True
        )

    def test_environment_wide_establishing_skipped(self) -> None:
        assert (
            should_review_frame({"subject_type": "environment", "frame_role": "wide-establishing"})
            is False
        )

    def test_environment_lighting_variant_skipped(self) -> None:
        assert (
            should_review_frame(
                {"subject_type": "environment", "frame_role": "lighting-cool-night"}
            )
            is False
        )

    def test_character_detail_insets_skipped(self) -> None:
        assert (
            should_review_frame({"subject_type": "character", "frame_role": "detail-eyes"}) is False
        )

    def test_character_expression_first_three_reviewed(self) -> None:
        for i in range(3):
            assert (
                should_review_frame(
                    {"subject_type": "character", "frame_role": "expression-tired"}, frame_index=i
                )
                is True
            )

    def test_scale_sheet_reviewed_once(self) -> None:
        entry = {"subject_type": "character", "asset_type": "scale_sheet"}
        assert should_review_frame(entry, frame_index=0) is True


class TestReviewFrame:
    def test_passing_review(self, tmp_path: Path) -> None:
        png = _make_png(tmp_path)
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "frame_id": "ref-001",
                                        "scores": {
                                            "subject": {"score": 9, "max": 10, "notes": "clear"},
                                            "prompt_match": {"score": 8, "max": 10, "notes": ""},
                                            "artifacts": {"score": 9, "max": 10, "notes": ""},
                                            "technical": {"score": 8, "max": 10, "notes": ""},
                                        },
                                        "total": 34,
                                        "passed": True,
                                        "actionable_feedback": "",
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }
        result = review_frame(
            png,
            "test prompt",
            model="test-model",
            http_opener=_mock_opener(response),
            api_key="test-key",
        )
        assert result.passed is True
        assert result.total == 34.0
        assert result.scores["subject"]["score"] == 9

    def test_failing_review(self, tmp_path: Path) -> None:
        png = _make_png(tmp_path)
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "frame_id": "ref-002",
                                        "scores": {
                                            "subject": {
                                                "score": 3,
                                                "max": 10,
                                                "notes": "face not visible",
                                            },
                                            "prompt_match": {"score": 4, "max": 10, "notes": ""},
                                            "artifacts": {"score": 5, "max": 10, "notes": ""},
                                            "technical": {"score": 5, "max": 10, "notes": ""},
                                        },
                                        "total": 17,
                                        "passed": False,
                                        "actionable_feedback": "Face is obscured.",
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }
        result = review_frame(
            png,
            "test prompt",
            model="test-model",
            http_opener=_mock_opener(response),
            api_key="test-key",
        )
        assert result.passed is False
        assert result.total == 17.0
        assert result.actionable_feedback == "Face is obscured."

    def test_markdown_fence_stripped(self, tmp_path: Path) -> None:
        png = _make_png(tmp_path)
        json_text = json.dumps(
            {
                "frame_id": "ref-003",
                "scores": {
                    "subject": {"score": 8, "max": 10, "notes": ""},
                    "prompt_match": {"score": 7, "max": 10, "notes": ""},
                    "artifacts": {"score": 8, "max": 10, "notes": ""},
                    "technical": {"score": 7, "max": 10, "notes": ""},
                },
                "total": 30,
                "passed": True,
                "actionable_feedback": "",
            }
        )
        response = {
            "candidates": [{"content": {"parts": [{"text": f"```json\n{json_text}\n```"}]}}]
        }
        result = review_frame(
            png,
            "test prompt",
            model="test-model",
            http_opener=_mock_opener(response),
            api_key="test-key",
        )
        assert result.passed is True
        assert result.total == 30.0

    def test_no_candidates_returns_error(self, tmp_path: Path) -> None:
        png = _make_png(tmp_path)
        result = review_frame(
            png,
            "test prompt",
            model="test-model",
            http_opener=_mock_opener({"candidates": []}),
            api_key="test-key",
        )
        assert result.passed is False
        assert result.error is not None

    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        result = review_frame(
            tmp_path / "nonexistent.png",
            "test prompt",
            model="test-model",
            api_key="test-key",
        )
        assert result.passed is False
        assert "Cannot read image" in (result.error or "")
