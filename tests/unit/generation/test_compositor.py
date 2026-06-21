"""Tests for compositor — Character Identity Sheet construction."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from film_pipeline.generation.compositor import (
    build_character_identity_sheet,
    build_environment_board,
    replace_tile,
)


def _make_frame(tmp_path: Path, name: str, size: tuple[int, int] = (1024, 1024)) -> Path:
    """Create a synthetic frame PNG with varied pixels."""
    path = tmp_path / name
    img = Image.new("RGB", size, (100, 150, 200))
    for x in range(0, size[0], 64):
        for y in range(0, size[1], 64):
            img.putpixel((x, y), (x % 256, y % 256, (x + y) % 256))
    img.save(path)
    return path


class TestCharacterIdentitySheet:
    def test_builds_sheet_with_all_frames(self, tmp_path: Path) -> None:
        frames = {
            "front-face": _make_frame(tmp_path, "front.png"),
            "3-4-left": _make_frame(tmp_path, "3-4-l.png"),
            "full-body": _make_frame(tmp_path, "body.png"),
            "expression-neutral": _make_frame(tmp_path, "expr-n.png"),
        }
        output = tmp_path / "identity-sheet.png"
        result = build_character_identity_sheet("leo", "Leo Marchetti", frames, output)
        assert result == output
        assert output.exists()
        img = Image.open(output)
        assert img.size == (2048, 2048)
        assert img.mode == "RGB"

    def test_builds_sheet_with_missing_frames(self, tmp_path: Path) -> None:
        frames = {
            "front-face": _make_frame(tmp_path, "front.png"),
            # 3-4-left, profile, full-body all missing
        }
        output = tmp_path / "identity-sheet.png"
        build_character_identity_sheet("leo", "Leo", frames, output)
        assert output.exists()
        # Should not crash — missing frames render as placeholders

    def test_builds_sheet_with_no_frames(self, tmp_path: Path) -> None:
        output = tmp_path / "identity-sheet.png"
        build_character_identity_sheet("leo", "Leo", {}, output)
        assert output.exists()
        # All tiles are placeholders

    def test_sheet_has_correct_dimensions(self, tmp_path: Path) -> None:
        frames = {"front-face": _make_frame(tmp_path, "f.png")}
        output = tmp_path / "sheet.png"
        build_character_identity_sheet("test", "Test", frames, output)
        img = Image.open(output)
        assert img.size == (2048, 2048)

    def test_creates_output_directory(self, tmp_path: Path) -> None:
        output = tmp_path / "deep" / "nested" / "sheet.png"
        frames = {"front-face": _make_frame(tmp_path, "f.png")}
        build_character_identity_sheet("x", "X", frames, output)
        assert output.exists()


class TestReplaceTile:
    def test_replaces_single_tile(self, tmp_path: Path) -> None:
        frames = {
            "front-face": _make_frame(tmp_path, "front.png"),
            "3-4-left": _make_frame(tmp_path, "3-4-l.png"),
        }
        sheet = tmp_path / "sheet.png"
        build_character_identity_sheet("leo", "Leo", frames, sheet)

        new_front = _make_frame(tmp_path, "new-front.png", (512, 512))
        result = replace_tile(sheet, "front-face", new_front)
        assert result.exists()

    def test_replace_unknown_tile_raises(self, tmp_path: Path) -> None:
        frames = {"front-face": _make_frame(tmp_path, "f.png")}
        sheet = tmp_path / "sheet.png"
        build_character_identity_sheet("x", "X", frames, sheet)
        with pytest.raises(ValueError, match="Unknown tile"):
            replace_tile(sheet, "nonexistent", _make_frame(tmp_path, "n.png"))


class TestEnvironmentBoard:
    def test_builds_board_with_palette(self, tmp_path: Path) -> None:
        frames = {
            "wide-establishing": _make_frame(tmp_path, "wide.png"),
        }
        output = tmp_path / "env-board.png"
        palette = ["#1a1a2e", "#e94560", "#0f3460", "#16213e"]
        result = build_environment_board(
            "studio",
            "Studio",
            frames,
            output,
            palette_colors=palette,
        )
        assert result == output
        assert output.exists()
        img = Image.open(output)
        assert img.size == (3840, 2160)
        # Palette area should NOT be solid placeholder gray — check a pixel
        # that falls inside the palette tile area
        px, py = 10, 1700  # inside color-palette region
        pixel = img.getpixel((px, py))
        # Should not be placeholder color (200, 200, 210)
        assert pixel != (200, 200, 210)

    def test_builds_board_without_palette(self, tmp_path: Path) -> None:
        frames = {
            "wide-establishing": _make_frame(tmp_path, "wide.png"),
        }
        output = tmp_path / "env-board.png"
        build_environment_board(
            "studio",
            "Studio",
            frames,
            output,
            palette_colors=None,
        )
        assert output.exists()
        img = Image.open(output)
        assert img.size == (3840, 2160)
        # Palette area should be placeholder
        px, py = 10, 1700
        pixel = img.getpixel((px, py))
        assert pixel == (200, 200, 210)

    def test_builds_board_with_empty_palette(self, tmp_path: Path) -> None:
        frames = {
            "wide-establishing": _make_frame(tmp_path, "wide.png"),
        }
        output = tmp_path / "env-board.png"
        build_environment_board(
            "studio",
            "Studio",
            frames,
            output,
            palette_colors=[],
        )
        assert output.exists()
        # Should not crash — renders placeholder

    def test_builds_board_with_invalid_hex(self, tmp_path: Path) -> None:
        frames = {
            "wide-establishing": _make_frame(tmp_path, "wide.png"),
        }
        output = tmp_path / "env-board.png"
        palette = ["not-a-color", "#GGHHII", "  ", "#123456"]
        build_environment_board(
            "studio",
            "Studio",
            frames,
            output,
            palette_colors=palette,
        )
        assert output.exists()
        # Only the valid hex should render; no crash
