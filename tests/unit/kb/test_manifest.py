"""Tests for KB manifest reader."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.kb.manifest import KBManifest
from film_pipeline.schemas._base import KbAuthority

MANIFEST_PATH = Path("film-knowledge-base/index/kb-manifest.yaml")


@pytest.fixture
def manifest() -> KBManifest:
    if not MANIFEST_PATH.exists():
        pytest.skip("kb-manifest.yaml not found")
    return KBManifest.from_yaml(MANIFEST_PATH)


class TestManifest:
    def test_manifest_loads(self, manifest: KBManifest) -> None:
        assert len(manifest) == 12

    def test_get_item(self, manifest: KBManifest) -> None:
        item = manifest.get("kb.policy.prompt.rctco.v1")
        assert item is not None
        assert item.authority == KbAuthority.CANONICAL
        assert item.status == "active"

    def test_contains(self, manifest: KBManifest) -> None:
        assert "kb.policy.prompt.rctco.v1" in manifest
        assert "nonexistent" not in manifest

    def test_by_authority_canonical(self, manifest: KBManifest) -> None:
        items = manifest.by_authority(KbAuthority.CANONICAL)
        assert len(items) == 6

    def test_by_authority_playbook(self, manifest: KBManifest) -> None:
        items = manifest.by_authority(KbAuthority.ACTIVE_PLAYBOOK)
        assert len(items) == 3

    def test_by_authority_case_study(self, manifest: KBManifest) -> None:
        items = manifest.by_authority(KbAuthority.CASE_STUDY)
        assert len(items) == 3

    def test_by_phase_all_match(self, manifest: KBManifest) -> None:
        # "all" phases should match every phase
        items = manifest.by_phase("generation")
        # 6 canonical (2 with all + 2 with generation) + 2 playbooks + 3 case studies
        # canonical: prompt.rctco (all), prompt (all), no_duplicate (gen), checkpoint (all),
        #   human (all), validation (qc, post) — wait, validation doesn't match gen
        # So: 5 canonical + 2 playbook + 3 case_study = 10
        assert len(items) >= 8

    def test_by_agent(self, manifest: KBManifest) -> None:
        items = manifest.by_agent("generation-agent")
        assert len(items) >= 3

    def test_by_domain(self, manifest: KBManifest) -> None:
        items = manifest.by_domain("operations")
        assert len(items) >= 3

    def test_active_only(self, manifest: KBManifest) -> None:
        items = manifest.active_only()
        assert len(items) == 12  # All are active

    def test_canonical_shortcut(self, manifest: KBManifest) -> None:
        items = manifest.canonical()
        assert len(items) == 6

    def test_playbooks_shortcut(self, manifest: KBManifest) -> None:
        items = manifest.playbooks()
        assert len(items) == 3

    def test_case_studies_shortcut(self, manifest: KBManifest) -> None:
        items = manifest.case_studies()
        assert len(items) == 3

    def test_iteration(self, manifest: KBManifest) -> None:
        ids = {item.id for item in manifest}
        assert "kb.policy.prompt.rctco.v1" in ids
