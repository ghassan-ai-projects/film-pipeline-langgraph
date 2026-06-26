"""Tests for deterministic artifact context compression."""

from __future__ import annotations

from film_pipeline.kb.compression import compact_json_context


def test_compact_json_context_preserves_small_artifacts() -> None:
    artifact = {"scene_id": "sc_001", "text": "Short scene."}

    compacted = compact_json_context(artifact, max_chars=1000)

    assert '"scene_id": "sc_001"' in compacted
    assert "[COMPRESSED ARTIFACT CONTEXT]" not in compacted


def test_compact_json_context_bounds_large_artifacts_and_promotes_ids() -> None:
    artifact = {
        "rows": [
            {
                "shot_id": f"shot_{idx:03d}",
                "scene_id": f"scene_{idx % 3:03d}",
                "prompt": "dense visual detail " * 40,
            }
            for idx in range(30)
        ]
    }

    compacted = compact_json_context(artifact, max_chars=900)

    assert len(compacted) <= 900
    assert "[COMPRESSED ARTIFACT CONTEXT]" in compacted
    assert "shot_000" in compacted
    assert "scene_000" in compacted
    assert "compressed artifact body clipped" in compacted
