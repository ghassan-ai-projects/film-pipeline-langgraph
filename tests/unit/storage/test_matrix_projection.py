"""Tests for layered master matrix projection."""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.schemas.base import FilmPhase
from film_pipeline.storage.matrix_projection import materialize_matrix


class FakeStore:
    def __init__(self, data: dict[tuple[str, FilmPhase, str, int], dict[str, Any]]) -> None:
        self.data = data

    def load(
        self,
        project_id: str,
        phase: FilmPhase,
        artifact_id: str,
        version: int,
    ) -> dict[str, Any]:
        key = (project_id, phase, artifact_id, version)
        if key not in self.data:
            raise FileNotFoundError(artifact_id)
        return self.data[key]


def test_materialize_matrix_applies_ordered_patch_layers() -> None:
    store = FakeStore(
        {
            (
                "p1",
                FilmPhase.SHOT_BIBLE,
                "shot_matrix",
                1,
            ): {
                "project_id": "p1",
                "rows": [
                    {"shot_id": "s1", "status": "planned", "asset_refs": ["a0"]},
                    {"shot_id": "s2", "status": "planned", "asset_refs": []},
                ],
            },
            (
                "p1",
                FilmPhase.GEN_PLANNING,
                "patch_a",
                1,
            ): {
                "patch_id": "patch_a",
                "matrix_ref": "artifact:shot_bible:shot_matrix:v1",
                "phase": "gen_planning",
                "updates": [
                    {"shot_id": "s1", "set": {"status": "prompted"}},
                    {"shot_id": "missing", "set": {"status": "ignored"}},
                ],
            },
            (
                "p1",
                FilmPhase.GENERATION,
                "patch_b",
                2,
            ): {
                "patch_id": "patch_b",
                "matrix_ref": "artifact:shot_bible:shot_matrix:v1",
                "phase": "generation",
                "updates": [
                    {"shot_id": "s1", "append": {"asset_refs": ["a1"]}},
                    {"shot_id": "s2", "set": {"status": "generated"}},
                ],
            },
        }
    )

    matrix = materialize_matrix(
        store,
        "p1",
        "artifact:shot_bible:shot_matrix:v1",
        ["artifact:gen_planning:patch_a:v1", "artifact:generation:patch_b:v2"],
    )

    assert matrix["rows"] == [
        {"shot_id": "s1", "status": "prompted", "asset_refs": ["a0", "a1"]},
        {"shot_id": "s2", "status": "generated", "asset_refs": []},
    ]


def test_materialize_matrix_defaults_malformed_rows_to_empty_list() -> None:
    store = FakeStore(
        {
            ("p1", FilmPhase.SHOT_BIBLE, "shot_matrix", 1): {
                "project_id": "p1",
                "rows": {"not": "a list"},
            }
        }
    )

    matrix = materialize_matrix(store, "p1", "artifact:shot_bible:shot_matrix:v1", [])

    assert matrix["rows"] == []


def test_materialize_matrix_raises_when_patch_ref_not_found() -> None:
    store = FakeStore(
        {
            ("p1", FilmPhase.SHOT_BIBLE, "shot_matrix", 1): {
                "project_id": "p1",
                "rows": [{"shot_id": "s1"}],
            }
        }
    )

    with pytest.raises(FileNotFoundError):
        materialize_matrix(
            store, "p1", "artifact:shot_bible:shot_matrix:v1", ["artifact:gen_planning:missing:v1"]
        )
