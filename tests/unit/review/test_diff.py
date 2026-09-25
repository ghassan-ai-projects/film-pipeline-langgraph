"""Tests for artifact diff engine."""

from __future__ import annotations

from film_pipeline.governance.diff import _id_stem
from film_pipeline.review.diff import ArtifactDiff, compute_artifact_diff


class TestIdStem:
    def test_strips_version(self) -> None:
        assert _id_stem("artifact:script:S001:v3") == "artifact:script:S001"
        assert _id_stem("artifact:visual_dev:reference_index:v2") == (
            "artifact:visual_dev:reference_index"
        )

    def test_no_version(self) -> None:
        assert _id_stem("artifact:script:S001") == "artifact:script:S001"

    def test_no_colon_version(self) -> None:
        assert _id_stem("simple_ref") == "simple_ref"


class TestArtifactDiff:
    def test_empty(self) -> None:
        d = ArtifactDiff()
        assert d.has_changes is False
        assert d.total_changes == 0

    def test_with_changes(self) -> None:
        d = ArtifactDiff(added=["a"], changed=["b"], removed=["c"])
        assert d.has_changes is True
        assert d.total_changes == 3


class TestComputeDiff:
    def test_added_only(self) -> None:
        diff = compute_artifact_diff(
            current=["artifact:script:S001:v1", "artifact:script:S002:v1"],
            previous=["artifact:script:S001:v1"],
        )
        assert "artifact:script:S002:v1" in diff.added
        assert len(diff.changed) == 0
        assert len(diff.removed) == 0

    def test_removed_only(self) -> None:
        diff = compute_artifact_diff(
            current=["artifact:script:S001:v1"],
            previous=["artifact:script:S001:v1", "artifact:script:S002:v1"],
        )
        assert "artifact:script:S002:v1" in diff.removed
        assert len(diff.added) == 0

    def test_changed_version(self) -> None:
        diff = compute_artifact_diff(
            current=["artifact:script:S001:v3"],
            previous=["artifact:script:S001:v2"],
        )
        assert "artifact:script:S001:v3" in diff.changed
        assert len(diff.added) == 0
        assert len(diff.removed) == 0

    def test_no_change(self) -> None:
        diff = compute_artifact_diff(
            current=["artifact:script:S001:v1"],
            previous=["artifact:script:S001:v1"],
        )
        assert len(diff.added) == 0
        assert len(diff.changed) == 0
        assert len(diff.removed) == 0

    def test_empty_previous(self) -> None:
        diff = compute_artifact_diff(
            current=["a", "b"],
            previous=[],
        )
        assert set(diff.added) == {"a", "b"}
        assert len(diff.changed) == 0
        assert len(diff.removed) == 0

    def test_empty_current(self) -> None:
        diff = compute_artifact_diff(
            current=[],
            previous=["a", "b"],
        )
        assert set(diff.removed) == {"a", "b"}
        assert len(diff.added) == 0
