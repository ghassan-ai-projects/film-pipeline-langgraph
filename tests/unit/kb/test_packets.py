"""Tests for KB context packet builder."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.kb.manifest import KBManifest
from film_pipeline.kb.packets import KBContextPacketBuilder

MANIFEST_PATH = Path("film-knowledge-base/index/kb-manifest.yaml")


@pytest.fixture
def builder() -> KBContextPacketBuilder:
    if not MANIFEST_PATH.exists():
        pytest.skip("kb-manifest.yaml not found")
    manifest = KBManifest.from_yaml(MANIFEST_PATH)
    return KBContextPacketBuilder(manifest)


class TestPackets:
    def test_build_basic(self, builder: KBContextPacketBuilder) -> None:
        packet = builder.build(
            project_id="test_project",
            phase="script",
            agent_id="script-agent",
            task="Write Act 1 script",
        )
        assert packet.project_id == "test_project"
        assert packet.phase == "script"
        assert packet.agent_id == "script-agent"
        assert packet.task == "Write Act 1 script"
        assert packet.kb_context_id.startswith("kbctx:")

    def test_build_includes_canonical(self, builder: KBContextPacketBuilder) -> None:
        packet = builder.build(
            project_id="test_project",
            phase="generation",
            agent_id="generation-agent",
            task="Generate clip",
        )
        # At least some canonical policies should be included
        assert len(packet.authority_policy_refs) >= 1
        assert "kb.policy.prompt.rctco.v1" in packet.authority_policy_refs

    def test_build_includes_playbooks(self, builder: KBContextPacketBuilder) -> None:
        packet = builder.build(
            project_id="test_project",
            phase="generation",
            agent_id="generation-agent",
            task="Generate clip",
        )
        # Should include relevant playbooks
        assert len(packet.playbook_refs) >= 1

    def test_build_includes_case_studies(self, builder: KBContextPacketBuilder) -> None:
        packet = builder.build(
            project_id="test_project",
            phase="generation",
            agent_id="generation-agent",
            task="Generate clip",
        )
        # All 3 case studies apply to generation; they should appear
        assert len(packet.case_study_refs) == 3

    def test_build_has_payload(self, builder: KBContextPacketBuilder) -> None:
        packet = builder.build(
            project_id="test_project",
            phase="generation",
            agent_id="generation-agent",
            task="Generate clip",
        )
        assert isinstance(packet.payload, dict)
        assert "kb.policy.prompt.rctco.v1" in packet.payload

    def test_build_no_duplicate_refs(self, builder: KBContextPacketBuilder) -> None:
        packet = builder.build(
            project_id="test_project",
            phase="generation",
            agent_id="generation-agent",
            task="Generate clip",
        )
        all_refs = packet.authority_policy_refs + packet.playbook_refs + packet.case_study_refs
        assert len(all_refs) == len(set(all_refs))

    def test_build_different_phase_different_context(self, builder: KBContextPacketBuilder) -> None:
        gen_packet = builder.build(
            project_id="test",
            phase="generation",
            agent_id="generation-agent",
            task="gen",
        )
        script_packet = builder.build(
            project_id="test",
            phase="script",
            agent_id="script-agent",
            task="write",
        )
        # Contexts should differ by phase
        assert gen_packet.case_study_refs != script_packet.case_study_refs

    def test_build_examples_empty(self, builder: KBContextPacketBuilder) -> None:
        packet = builder.build(
            project_id="test_project",
            phase="generation",
            agent_id="generation-agent",
            task="Generate clip",
        )
        assert packet.examples == []

    def test_build_with_all_phase(self, builder: KBContextPacketBuilder) -> None:
        packet = builder.build(
            project_id="test",
            phase="intake",
            agent_id="orchestrator",
            task="Intake project",
        )
        # should still get canonical policies (prompt, checkpoint, human, validation)
        assert len(packet.authority_policy_refs) >= 3
