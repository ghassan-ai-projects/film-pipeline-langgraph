"""Tests for additional composite templates — expression, scale, style."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from film_pipeline.generation.compositor import (
    build_expression_sheet,
    build_scale_sheet,
    build_style_board,
)


def _make_frame(tmp_path: Path, name: str, size: tuple[int, int] = (512, 512)) -> Path:
    path = tmp_path / name
    img = Image.new("RGB", size, (100, 150, 200))
    img.save(path)
    return path


class TestExpressionSheet:
    def test_builds_with_expressions(self, tmp_path: Path) -> None:
        frames = {
            "expression-neutral": _make_frame(tmp_path, "neutral.png"),
            "expression-frustrated": _make_frame(tmp_path, "frus.png"),
        }
        output = tmp_path / "expr-sheet.png"
        result = build_expression_sheet("leo", "Leo", frames, output)
        assert result == output
        assert output.exists()
        img = Image.open(output)
        assert img.size == (2048, 2048)

    def test_builds_with_no_frames(self, tmp_path: Path) -> None:
        output = tmp_path / "expr-sheet.png"
        build_expression_sheet("leo", "Leo", {}, output)
        assert output.exists()


class TestScaleSheet:
    def test_builds_with_characters(self, tmp_path: Path) -> None:
        frames = {
            "leo": _make_frame(tmp_path, "leo-full.png"),
            "maya": _make_frame(tmp_path, "maya-full.png"),
        }
        output = tmp_path / "scale-sheet.png"
        result = build_scale_sheet("test-project", frames, output)
        assert result == output
        assert output.exists()
        img = Image.open(output)
        assert img.size == (3840, 2160)

    def test_builds_with_no_frames(self, tmp_path: Path) -> None:
        output = tmp_path / "scale-sheet.png"
        build_scale_sheet("test", {}, output)
        assert output.exists()


class TestStyleBoard:
    def test_builds_with_palette(self, tmp_path: Path) -> None:
        output = tmp_path / "style-board.png"
        result = build_style_board(
            "test",
            ["#1a1a2e", "#e94560"],
            "gritty",
            "16mm",
            "melancholic",
            output,
        )
        assert result == output
        assert output.exists()
        img = Image.open(output)
        assert img.size == (3840, 2160)

    def test_builds_with_empty_palette(self, tmp_path: Path) -> None:
        output = tmp_path / "style-board.png"
        build_style_board("test", [], "", "", "", output)
        assert output.exists()
