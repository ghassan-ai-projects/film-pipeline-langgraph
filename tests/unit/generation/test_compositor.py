"""Tests for compositor — Character Identity Sheet construction."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from film_pipeline.generation.compositor import (
    build_character_identity_sheet,
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
        result = build_character_identity_sheet("leo", "Leo", frames, output)
        assert output.exists()
        # Should not crash — missing frames render as placeholders

    def test_builds_sheet_with_no_frames(self, tmp_path: Path) -> None:
        output = tmp_path / "identity-sheet.png"
        result = build_character_identity_sheet("leo", "Leo", {}, output)
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
