"""Unit tests for the small pure helpers in film_pipeline.mcp.tools.reference_generation.

The full ``generate_reference_images`` pipeline (provider calls, retries,
composite sheets, Gemini review) is exercised end-to-end by
``tests/integration/test_reference_generation_mcp.py``. This file targets
the standalone helper functions that don't require a full image-generation
pipeline to exercise.
"""

from __future__ import annotations

import json
from pathlib import Path

from film_pipeline.mcp.tools.reference_generation import (
    _group_and_sort_entries,
    _group_key,
    _reference_aspect_ratio,
    _reference_job_id,
    _reference_output_dir,
    _select_image_provider,
    _write_reference_index_files,
)


def test_group_key_normalizes_case_and_whitespace() -> None:
    entry: dict[str, object] = {"subject_type": " Character ", "subject_id": " LEO "}
    assert _group_key(entry) == "character:leo"


def test_group_key_handles_missing_fields() -> None:
    assert _group_key({}) == ":"


def test_reference_aspect_ratio_environment() -> None:
    assert _reference_aspect_ratio({"subject_type": "environment"}) == "16:9"
    assert _reference_aspect_ratio({"asset_type": "environment_board"}) == "16:9"


def test_reference_aspect_ratio_style_and_camera_and_scale() -> None:
    assert _reference_aspect_ratio({"asset_type": "style_board"}) == "16:9"
    assert _reference_aspect_ratio({"asset_type": "camera_profile"}) == "16:9"
    assert _reference_aspect_ratio({"asset_type": "scale_sheet"}) == "16:9"


def test_reference_aspect_ratio_default_is_portrait() -> None:
    assert _reference_aspect_ratio({"subject_type": "character"}) == "3:4"


def test_reference_job_id_replaces_separators() -> None:
    assert _reference_job_id("char:leo/front-face") == "char-leo-front-face"


def test_reference_output_dir_for_character() -> None:
    root = Path("/tmp/project-root")
    entry: dict[str, object] = {"subject_type": "Character", "subject_id": "Leo"}
    result = _reference_output_dir(entry, root)
    assert result == root / "references" / "characters" / "leo" / "master-frames"


def test_reference_output_dir_for_misc_subject() -> None:
    root = Path("/tmp/project-root")
    entry: dict[str, object] = {"subject_type": "style"}
    result = _reference_output_dir(entry, root)
    assert result == root / "references" / "style"


def test_group_and_sort_entries_filters_non_dict_and_blank_ids() -> None:
    entries: list[object] = [
        {"reference_id": "ref1", "subject_type": "character", "subject_id": "leo"},
        "not-a-dict",
        {"reference_id": "", "subject_type": "character", "subject_id": "leo"},
    ]
    results: list[dict[str, object]] = []
    out = _group_and_sort_entries(entries, set(), False, Path("/tmp/proj"), results)
    assert len(out) == 1
    assert out[0]["reference_id"] == "ref1"


def test_group_and_sort_entries_respects_requested_ids_filter() -> None:
    entries: list[object] = [
        {"reference_id": "ref1", "subject_type": "character", "subject_id": "leo"},
        {"reference_id": "ref2", "subject_type": "character", "subject_id": "mia"},
    ]
    results: list[dict[str, object]] = []
    out = _group_and_sort_entries(entries, {"ref2"}, False, Path("/tmp/proj"), results)
    assert len(out) == 1
    assert out[0]["reference_id"] == "ref2"


def test_group_and_sort_entries_marks_skip_when_asset_exists(tmp_path: Path) -> None:
    existing = tmp_path / "frame.png"
    existing.write_bytes(b"fake-png-bytes")
    entries: list[object] = [
        {
            "reference_id": "ref1",
            "subject_type": "character",
            "subject_id": "leo",
            "asset_path": "frame.png",
        }
    ]
    results: list[dict[str, object]] = []
    out = _group_and_sort_entries(entries, set(), False, tmp_path, results)
    assert out[0].get("_skip") is True


def test_group_and_sort_entries_force_overrides_skip(tmp_path: Path) -> None:
    existing = tmp_path / "frame.png"
    existing.write_bytes(b"fake-png-bytes")
    entries: list[object] = [
        {
            "reference_id": "ref1",
            "subject_type": "character",
            "subject_id": "leo",
            "asset_path": "frame.png",
        }
    ]
    results: list[dict[str, object]] = []
    out = _group_and_sort_entries(entries, set(), True, tmp_path, results)
    assert out[0].get("_skip") is None


def test_group_and_sort_entries_sorts_anchor_first() -> None:
    entries: list[object] = [
        {
            "reference_id": "ref_b",
            "subject_type": "character",
            "subject_id": "leo",
            "frame_role": "side-profile",
        },
        {
            "reference_id": "ref_a",
            "subject_type": "character",
            "subject_id": "leo",
            "frame_role": "front-face",
        },
    ]
    results: list[dict[str, object]] = []
    out = _group_and_sort_entries(entries, set(), False, Path("/tmp/proj"), results)
    assert out[0]["reference_id"] == "ref_a"
    assert out[1]["reference_id"] == "ref_b"


def test_select_image_provider_returns_none_when_no_image_provider() -> None:
    class _FakeAdapter:
        entry = type("E", (), {"provider_type": "video"})()

    class _FakeRuntime:
        def list_providers(self) -> list[str]:
            return ["video-provider-1"]

        def get_provider(self, provider_id: str) -> object:
            return _FakeAdapter()

    assert _select_image_provider(_FakeRuntime()) is None


def test_select_image_provider_returns_image_adapter() -> None:
    class _ImageAdapter:
        entry = type("E", (), {"provider_type": "image"})()

    class _VideoAdapter:
        entry = type("E", (), {"provider_type": "video"})()

    class _FakeRuntime:
        def list_providers(self) -> list[str]:
            return ["video-provider-1", "image-provider-1"]

        def get_provider(self, provider_id: str) -> object:
            return _VideoAdapter() if provider_id == "video-provider-1" else _ImageAdapter()

    adapter = _select_image_provider(_FakeRuntime())
    assert adapter is not None
    assert adapter.entry.provider_type == "image"


def test_write_reference_index_files(tmp_path: Path) -> None:
    entries: list[dict[str, object]] = [
        {
            "reference_id": "ref1",
            "asset_type": "character_frame",
            "subject_id": "leo",
            "asset_path": "references/characters/leo/master-frames/front.png",
            "provider": "mock-image-provider",
            "validation": {"status": "approved", "score": 38.0},
            "locked": True,
            "generation_status": "validated",
            "quality_score": 95.0,
        },
        {
            "reference_id": "ref2",
            "generation_status": "failed",
        },
    ]
    _write_reference_index_files(tmp_path, entries)

    idx_dir = tmp_path / "references" / "index"
    index_data = json.loads((idx_dir / "reference-index.json").read_text())
    assert len(index_data["entries"]) == 2
    assert index_data["entries"][0]["reference_id"] == "ref1"

    summary = json.loads((idx_dir / "reference-validation-summary.json").read_text())
    assert summary["total_entries"] == 2
    assert summary["validated"] == 1
    assert summary["failed"] == 1
    assert summary["average_score"] == 95.0
