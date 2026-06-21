"""Tests for sheet_reviewer — composite validation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

from film_pipeline.generation.sheet_reviewer import review_composite_sheet


def _mock_opener(response_body: dict) -> Mock:
    resp = Mock()
    resp.read.return_value = json.dumps(response_body).encode("utf-8")
    resp.__enter__ = Mock(return_value=resp)
    resp.__exit__ = Mock(return_value=False)
    opener = Mock()
    opener.open.return_value = resp
    return opener


def _make_png(tmp_path: Path) -> Path:
    from PIL import Image
    p = tmp_path / "sheet.png"
    img = Image.new("RGB", (256, 256), (100, 150, 200))
    for x in range(0, 256, 64):
        for y in range(0, 256, 64):
            img.putpixel((x, y), (x % 256, y % 256, (x + y) % 256))
    img.save(p)
    return p


class TestReviewCompositeSheet:
    def test_passing_character_sheet(self, tmp_path: Path) -> None:
        png = _make_png(tmp_path)
        response = {"candidates": [{"content": {"parts": [{"text": json.dumps({
            "sheet_id": "leo", "sheet_type": "character_identity_sheet",
            "scores": {
                "identity_accuracy": {"score": 13, "max": 15, "notes": ""},
                "expression_fidelity": {"score": 8, "max": 10, "notes": ""},
                "composition_quality": {"score": 8, "max": 10, "notes": ""},
                "technical_quality": {"score": 8, "max": 10, "notes": ""},
                "usability": {"score": 4, "max": 5, "notes": ""},
            },
            "total": 41, "passed": True, "actionable_feedback": "", "failing_tiles": [], "bad_reference_tags": []
        })}]}}]}
        result = review_composite_sheet(png, "character_identity_sheet", "leo", http_opener=_mock_opener(response), api_key="test")
        assert result.passed is True
        assert result.total == 41.0
        assert result.status == "approved"

    def test_failing_environment_board(self, tmp_path: Path) -> None:
        png = _make_png(tmp_path)
        response = {"candidates": [{"content": {"parts": [{"text": json.dumps({
            "sheet_id": "studio", "sheet_type": "environment_board",
            "scores": {
                "spatial_consistency": {"score": 5, "max": 15, "notes": "geometry changed"},
                "lighting_accuracy": {"score": 6, "max": 10, "notes": ""},
                "mood_encoding": {"score": 5, "max": 10, "notes": ""},
                "technical_quality": {"score": 5, "max": 10, "notes": ""},
                "usability": {"score": 2, "max": 5, "notes": ""},
            },
            "total": 23, "passed": False, "actionable_feedback": "Room layout inconsistent",
            "failing_tiles": ["alt-angle-corner"], "bad_reference_tags": ["geometry_unclear"]
        })}]}}]}
        result = review_composite_sheet(png, "environment_board", "studio", http_opener=_mock_opener(response), api_key="test")
        assert result.passed is False
        assert result.status == "needs_delta_fix"
        assert result.failing_tiles == ["alt-angle-corner"]
        assert "geometry_unclear" in result.bad_reference_tags

    def test_unknown_sheet_type(self, tmp_path: Path) -> None:
        result = review_composite_sheet(_make_png(tmp_path), "unknown_type", "x")
        assert result.passed is False
        assert result.error is not None
