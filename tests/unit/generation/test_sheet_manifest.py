"""Tests for sheet manifest — .sheet.json written alongside composite PNGs."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from film_pipeline.generation.compositor import (
    build_character_identity_sheet,
    build_environment_board,
)


def _make_frame(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    img = Image.new("RGB", (512, 512), (100, 150, 200))
    img.save(path)
    return path


class TestSheetManifest:
    def test_character_sheet_writes_manifest(self, tmp_path: Path) -> None:
        frames = {"front-face": _make_frame(tmp_path, "front.png")}
        output = tmp_path / "identity-sheet.png"
        build_character_identity_sheet("leo", "Leo", frames, output)

        manifest_path = tmp_path / "identity-sheet.png.sheet.json"
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text())
        assert data["sheet_type"] == "character_identity_sheet"
        assert len(data["tiles"]) == 1
        assert data["tiles"][0]["tile_name"] == "front-face"
        assert len(data["placeholder_tiles"]) > 0  # many tiles missing

    def test_environment_board_writes_manifest(self, tmp_path: Path) -> None:
        frames = {"wide-establishing": _make_frame(tmp_path, "wide.png")}
        output = tmp_path / "env-board.png"
        build_environment_board("studio", "Studio", frames, output)

        manifest_path = tmp_path / "env-board.png.sheet.json"
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text())
        assert data["sheet_type"] == "environment_board"
        assert len(data["tiles"]) == 1
