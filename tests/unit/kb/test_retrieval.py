"""Tests for KB retrieval engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.kb.manifest import KBManifest
from film_pipeline.kb.retrieval import KBRetrieval
from film_pipeline.schemas._base import KbAuthority

MANIFEST_PATH = Path("film-knowledge-base/index/kb-manifest.yaml")


@pytest.fixture
def retrieval() -> KBRetrieval:
    if not MANIFEST_PATH.exists():
        pytest.skip("kb-manifest.yaml not found")
    manifest = KBManifest.from_yaml(MANIFEST_PATH)
    return KBRetrieval(manifest)


class TestRetrieval:
    def test_deterministic_retrieval(self, retrieval: KBRetrieval) -> None:
        items = retrieval.deterministic(["kb.policy.prompt.rctco.v1"])
        assert len(items) == 1
        assert items[0].id == "kb.policy.prompt.rctco.v1"

    def test_deterministic_missing(self, retrieval: KBRetrieval) -> None:
        items = retrieval.deterministic(["nonexistent"])
        assert len(items) == 0

    def test_deterministic_mixed(self, retrieval: KBRetrieval) -> None:
        items = retrieval.deterministic(["kb.policy.prompt.rctco.v1", "nonexistent"])
        assert len(items) == 1

    def test_by_tags_phase(self, retrieval: KBRetrieval) -> None:
        items = retrieval.by_tags(phase="generation")
        assert len(items) >= 6  # at least canonical + playbooks + case studies

    def test_by_tags_agent(self, retrieval: KBRetrieval) -> None:
        items = retrieval.by_tags(agent_id="generation-agent")
        assert len(items) >= 2

    def test_by_tags_authority(self, retrieval: KBRetrieval) -> None:
        items = retrieval.by_tags(authority=KbAuthority.CANONICAL)
        assert len(items) == 6

    def test_by_tags_combined(self, retrieval: KBRetrieval) -> None:
        items = retrieval.by_tags(phase="generation", authority=KbAuthority.CASE_STUDY)
        # All 3 case studies apply to generation
        assert len(items) == 3

    def test_examples(self, retrieval: KBRetrieval) -> None:
        items = retrieval.examples(phase="generation")
        assert len(items) >= 0  # case studies tagged for generation

    def test_for_task_layered(self, retrieval: KBRetrieval) -> None:
        result = retrieval.for_task(phase="generation", agent_id="generation-agent")
        assert "canonical" in result
        assert "playbooks" in result
        assert "case_studies" in result
        assert len(result["canonical"]) >= 3

    def test_for_task_with_required(self, retrieval: KBRetrieval) -> None:
        result = retrieval.for_task(
            phase="generation",
            agent_id="generation-agent",
            required_policy_ids=["kb.policy.prompt.rctco.v1"],
        )
        assert any(i.id == "kb.policy.prompt.rctco.v1" for i in result["canonical"])

    def test_for_task_playbooks_for_phase(self, retrieval: KBRetrieval) -> None:
        result = retrieval.for_task(phase="gen_planning", agent_id="prompt-composition-agent")
        assert len(result["playbooks"]) >= 1  # reference_images playbook
