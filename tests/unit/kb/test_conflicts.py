"""Tests for KB conflict detection and resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.kb.conflicts import KBConflictDetector, _id_stem
from film_pipeline.kb.manifest import KBManifest
from film_pipeline.schemas.base import KbAuthority
from film_pipeline.schemas.kb import KBItemMetadata

MANIFEST_PATH = Path("film-knowledge-base/index/kb-manifest.yaml")


@pytest.fixture
def detector() -> KBConflictDetector:
    if not MANIFEST_PATH.exists():
        pytest.skip("kb-manifest.yaml not found")
    manifest = KBManifest.from_yaml(MANIFEST_PATH)
    return KBConflictDetector(manifest)


class TestIdStem:
    def test_strips_version(self) -> None:
        assert _id_stem("kb.policy.prompt.rctco.v1") == "kb.policy.prompt.rctco"
        assert _id_stem("kb.policy.prompt.rctco.v2") == "kb.policy.prompt.rctco"

    def test_no_version(self) -> None:
        assert _id_stem("kb.policy.prompt.rctco") == "kb.policy.prompt.rctco"

    def test_version_like_but_not(self) -> None:
        assert _id_stem("kb.policy.v1.rctco") == "kb.policy.v1.rctco"


class TestDetectConflicts:
    def test_no_conflicts_with_active_items(self, detector: KBConflictDetector) -> None:
        items = list(detector.manifest.items.values())
        conflicts = detector.detect_conflicts(items)
        # Currently no items declare conflicts_with
        assert len(conflicts) == 0

    def test_declared_conflict(self, detector: KBConflictDetector) -> None:
        item_a = KBItemMetadata(
            id="a",
            title="A",
            authority=KbAuthority.CANONICAL,
            summary="a",
            conflicts_with=["b"],
        )
        item_b = KBItemMetadata(
            id="b",
            title="B",
            authority=KbAuthority.CANONICAL,
            summary="b",
        )
        conflicts = detector.detect_conflicts([item_a, item_b])
        assert len(conflicts) == 1
        assert conflicts[0].items == ["a", "b"]


class TestResolveSuperseded:
    def test_no_superseded(self, detector: KBConflictDetector) -> None:
        item = KBItemMetadata(
            id="a",
            title="A",
            authority=KbAuthority.CANONICAL,
            summary="a",
        )
        kept, excluded = detector.resolve_superseded([item])
        assert len(kept) == 1
        assert len(excluded) == 0

    def test_superseded_item_removed(self, detector: KBConflictDetector) -> None:
        old = KBItemMetadata(
            id="old",
            title="Old",
            authority=KbAuthority.CASE_STUDY,
            summary="old",
        )
        new = KBItemMetadata(
            id="new",
            title="New",
            authority=KbAuthority.CANONICAL,
            summary="new",
            supersedes=["old"],
        )
        kept, excluded = detector.resolve_superseded([old, new])
        assert len(kept) == 1
        assert kept[0].id == "new"
        assert len(excluded) == 1
        assert excluded[0].ref == "old"


class TestResolveAuthority:
    def test_higher_authority_wins(self, detector: KBConflictDetector) -> None:
        canonical = KBItemMetadata(
            id="kb.policy.test.v1",
            title="Canonical",
            authority=KbAuthority.CANONICAL,
            summary="c",
        )
        case_study = KBItemMetadata(
            id="kb.policy.test.v2",
            title="Case Study",
            authority=KbAuthority.CASE_STUDY,
            summary="cs",
        )
        kept, excluded = detector.resolve_authority([canonical, case_study])
        assert len(kept) == 1
        assert kept[0].authority == KbAuthority.CANONICAL
        assert len(excluded) == 1
        assert excluded[0].reason == (
            "Superseded by kb.policy.test.v1 (higher authority: canonical > case_study)"
        )

    def test_same_authority_newer_version_wins(self, detector: KBConflictDetector) -> None:
        v1 = KBItemMetadata(
            id="kb.policy.test.v1",
            title="V1",
            authority=KbAuthority.CANONICAL,
            summary="v1",
            version=1,
        )
        v2 = KBItemMetadata(
            id="kb.policy.test.v2",
            title="V2",
            authority=KbAuthority.CANONICAL,
            summary="v2",
            version=2,
        )
        kept, excluded = detector.resolve_authority([v1, v2])
        assert len(kept) == 1
        assert kept[0].id == "kb.policy.test.v2"
        assert len(excluded) == 1
        assert excluded[0].ref == "kb.policy.test.v1"
        # Authority tied: the reason must credit the version, not claim a
        # higher authority that does not exist.
        assert excluded[0].reason == (
            "Superseded by kb.policy.test.v2 (equal authority: newer version 2 > 1)"
        )

    def test_same_authority_and_version_reports_tie(self, detector: KBConflictDetector) -> None:
        unsuffixed = KBItemMetadata(
            id="kb.policy.test",
            title="Unsuffixed",
            authority=KbAuthority.CANONICAL,
            summary="u",
            version=1,
        )
        v1 = KBItemMetadata(
            id="kb.policy.test.v1",
            title="V1",
            authority=KbAuthority.CANONICAL,
            summary="v1",
            version=1,
        )
        kept, excluded = detector.resolve_authority([unsuffixed, v1])
        assert len(kept) == 1
        assert kept[0].id == "kb.policy.test"
        assert len(excluded) == 1
        assert excluded[0].reason == (
            "Superseded by kb.policy.test (same authority and version; kept first-listed item)"
        )

    def test_single_item_passes_through(self, detector: KBConflictDetector) -> None:
        item = KBItemMetadata(
            id="kb.policy.test.v1",
            title="Test",
            authority=KbAuthority.CANONICAL,
            summary="t",
        )
        kept, excluded = detector.resolve_authority([item])
        assert len(kept) == 1
        assert len(excluded) == 0

    def test_empty_list(self, detector: KBConflictDetector) -> None:
        kept, excluded = detector.resolve_authority([])
        assert len(kept) == 0
        assert len(excluded) == 0
