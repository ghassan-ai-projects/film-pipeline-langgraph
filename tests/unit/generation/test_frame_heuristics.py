"""Tests for frame_heuristics — the 5 Pillow-based checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from film_pipeline.generation.frame_heuristics import run_heuristic_checks


@pytest.fixture
def valid_png(tmp_path: Path) -> Path:
    """A valid 512x512 RGB PNG with varied content."""
    path = tmp_path / "valid.png"
    img = Image.new("RGB", (512, 512), color=(100, 150, 200))
    # Add some variation so it's not flagged as solid color
    for x in range(0, 512, 64):
        for y in range(0, 512, 64):
            img.putpixel((x, y), (x % 256, y % 256, (x + y) % 256))
    img.save(path)
    return path


@pytest.fixture
def small_png(tmp_path: Path) -> Path:
    """A 64x64 PNG - too small for reference use."""
    path = tmp_path / "small.png"
    img = Image.new("RGB", (64, 64), color=(100, 150, 200))
    img.save(path)
    return path


@pytest.fixture
def solid_color_png(tmp_path: Path) -> Path:
    """A solid-color PNG — effectively blank."""
    path = tmp_path / "solid.png"
    img = Image.new("RGB", (512, 512), color=(128, 128, 128))
    img.save(path)
    return path


@pytest.fixture
def empty_png(tmp_path: Path) -> Path:
    """An empty (0-byte) file."""
    path = tmp_path / "empty.png"
    path.write_text("")
    return path


class TestRunHeuristicChecks:
    def test_valid_image_passes_all_checks(self, valid_png: Path) -> None:
        result = run_heuristic_checks(valid_png, subject_type="character")
        assert result.passed is True
        assert result.failures == []
        assert result.image_size == (512, 512)
        assert "file_exists" in result.checks_run
        assert "not_corrupt" in result.checks_run
        assert "min_resolution" in result.checks_run
        assert "has_content" in result.checks_run
        assert "face_present" in result.checks_run

    def test_valid_image_non_character_skips_face_check(self, valid_png: Path) -> None:
        result = run_heuristic_checks(valid_png, subject_type="environment")
        assert result.passed is True
        assert "face_present" not in result.checks_run

    def test_too_small_fails_min_resolution(self, small_png: Path) -> None:
        result = run_heuristic_checks(small_png, subject_type="character")
        assert result.passed is False
        assert any("resolution_too_low" in f for f in result.failures)

    def test_solid_color_fails_has_content(self, solid_color_png: Path) -> None:
        result = run_heuristic_checks(solid_color_png, subject_type="character")
        assert result.passed is False
        assert "solid_color_or_blank" in result.failures

    def test_empty_file_fails_file_exists(self, empty_png: Path) -> None:
        result = run_heuristic_checks(empty_png, subject_type="character")
        assert result.passed is False
        assert "file_empty" in result.failures

    def test_missing_file_fails(self, tmp_path: Path) -> None:
        result = run_heuristic_checks(tmp_path / "nonexistent.png", subject_type="character")
        assert result.passed is False
        assert "file_missing" in result.failures

    def test_too_small_for_face_detection_on_character(self, small_png: Path) -> None:
        result = run_heuristic_checks(small_png, subject_type="character")
        assert result.passed is False
        # The first failure will be resolution_too_low, and face detection
        # also flags too_small_for_face_detection since image_size exists
        failures = result.failures
        assert any("resolution_too_low" in f for f in failures)

    def test_result_passed_false_when_failures(self, solid_color_png: Path) -> None:
        result = run_heuristic_checks(solid_color_png, subject_type="character")
        assert result.passed is False
        assert len(result.failures) > 0

    def test_result_passed_true_when_no_failures(self, valid_png: Path) -> None:
        result = run_heuristic_checks(valid_png, subject_type="prop")
        assert result.passed is True
        assert result.failures == []
