"""Tests for delta_regenerator — tile-level regeneration."""

from __future__ import annotations

from pathlib import Path

from film_pipeline.generation.delta_regenerator import regenerate_failing_tiles
from film_pipeline.generation.sheet_reviewer import SheetReviewResult


class TestRegenerateFailingTiles:
    def test_regenerates_only_failing_tiles(self, tmp_path: Path) -> None:
        sheet = tmp_path / "sheet.png"
        from PIL import Image

        img = Image.new("RGB", (256, 256), (100, 150, 200))
        img.save(sheet)

        review = SheetReviewResult(
            sheet_id="leo",
            sheet_type="character_identity_sheet",
            passed=False,
            total=30.0,
            max_score=50.0,
            failing_tiles=["profile-right"],
            actionable_feedback="Face looks different",
        )
        entries = [
            {"frame_role": "front-face", "asset_path": "f1.png"},
            {"frame_role": "profile-right", "asset_path": "f2.png"},
            {"frame_role": "full-body", "asset_path": "f3.png"},
        ]

        regenerated: list[str] = []

        def regen_fn(entry, feedback):
            regenerated.append(entry["frame_role"])
            new_p = tmp_path / f"new_{entry['frame_role']}.png"
            img.save(new_p)
            return new_p

        _best_score, _iterations, _history = regenerate_failing_tiles(
            review,
            entries,
            sheet,
            tmp_path,
            regenerate_fn=regen_fn,
            max_iterations=2,
        )

        assert "profile-right" in regenerated
        assert "front-face" not in regenerated
        assert "full-body" not in regenerated
