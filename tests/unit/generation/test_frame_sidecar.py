"""Tests for frame_sidecar — .meta.json write/read round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.generation.frame_sidecar import (
    read_frame_sidecar,
    write_frame_sidecar,
)
from film_pipeline.schemas.reference import ReferenceFrame


class TestFrameSidecar:
    def test_write_and_read_roundtrip(self, tmp_path: Path) -> None:
        frame_path = tmp_path / "test.png"
        frame_path.write_text("fake png")

        meta = ReferenceFrame(
            frame_path="test.png",
            reference_id="char-leo-front-face",
            subject_type="character",
            subject_id="leo",
            provider_id="gemini-imagen-4",
            model_id="imagen-4.0-fast-generate-001",
            tier="standard",
            seed=42,
            prompt_text="A tall man...",
            frame_role="front-face",
            expression="neutral",
            lighting="key-light",
            aspect_ratio="3:4",
            generation_status="validated",
            quality_score=85.0,
            retry_count=1,
            best_score=34.0,
            heuristic_checks_passed=True,
            mime_type="image/png",
            created_at="2026-06-21T00:00:00Z",
        )
        sidecar_path = write_frame_sidecar(frame_path, meta)
        assert sidecar_path.exists()
        assert sidecar_path.name == "test.png.meta.json"

        read_back = read_frame_sidecar(frame_path)
        assert read_back.reference_id == "char-leo-front-face"
        assert read_back.seed == 42
        assert read_back.quality_score == 85.0
        assert read_back.generation_status == "validated"

    def test_read_missing_sidecar_raises(self, tmp_path: Path) -> None:
        frame_path = tmp_path / "nonexistent.png"
        with pytest.raises(FileNotFoundError):
            read_frame_sidecar(frame_path)

    def test_read_corrupt_sidecar_raises(self, tmp_path: Path) -> None:
        frame_path = tmp_path / "corrupt.png"
        frame_path.write_text("fake png")
        sidecar = tmp_path / "corrupt.png.meta.json"
        sidecar.write_text("{not valid json")
        with pytest.raises(ValueError):
            read_frame_sidecar(frame_path)
