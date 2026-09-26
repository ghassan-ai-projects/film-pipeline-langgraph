"""Tests for handoff manager."""

from __future__ import annotations

from film_pipeline.agents.handoff import HandoffManager
from film_pipeline.schemas.base import AgentFamily, AgentRole
from film_pipeline.schemas.handoff import AgentRegistration
from film_pipeline.schemas.kb import KBContextPacket


class TestHandoffManager:
    def test_create_handoff(self) -> None:
        manager = HandoffManager()
        contract = AgentRegistration(
            agent_id="test-agent",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=["test"],
            input_artifacts=["input"],
            output_artifacts=["output_schema"],
            allowed_kb_domains=["ops"],
            reviewed_by=["reviewer-agent"],
        )
        kb = KBContextPacket(
            kb_context_id="kbctx:p1:agent:v1",
            project_id="p1",
            phase="script",
            agent_id="test-agent",
            task="test",
        )
        handoff = manager.create(
            contract=contract,
            project_id="p1",
            task="Write script",
            kb_context=kb,
        )
        assert handoff.from_agent == "test-agent"
        assert handoff.to_agent == "orchestrator-agent"
        assert handoff.project_id == "p1"
        assert len(manager) == 1

    def test_multiple_handoffs(self) -> None:
        manager = HandoffManager()
        contract = AgentRegistration(
            agent_id="agent-a",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=["a"],
            input_artifacts=["in"],
            output_artifacts=["out"],
            allowed_kb_domains=["ops"],
        )
        kb = KBContextPacket(
            kb_context_id="kbctx:x",
            project_id="p1",
            phase="x",
            agent_id="x",
            task="x",
        )
        manager.create(contract, "p1", "task1", kb)
        manager.create(contract, "p2", "task2", kb)
        assert len(manager) == 2

    def test_by_agent(self) -> None:
        manager = HandoffManager()
        contract_a = AgentRegistration(
            agent_id="agent-a",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=["a"],
            input_artifacts=["in"],
            output_artifacts=["out"],
            allowed_kb_domains=["ops"],
        )
        contract_b = AgentRegistration(
            agent_id="agent-b",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=["b"],
            input_artifacts=["in"],
            output_artifacts=["out"],
            allowed_kb_domains=["ops"],
        )
        kb = KBContextPacket(
            kb_context_id="kbctx:x",
            project_id="p1",
            phase="x",
            agent_id="x",
            task="x",
        )
        manager.create(contract_a, "p1", "task1", kb)
        manager.create(contract_b, "p1", "task2", kb)
        assert len(manager.by_agent("agent-a")) == 1
        assert len(manager.by_agent("agent-b")) == 1

    def test_by_project(self) -> None:
        manager = HandoffManager()
        contract = AgentRegistration(
            agent_id="agent",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=["a"],
            input_artifacts=["in"],
            output_artifacts=["out"],
            allowed_kb_domains=["ops"],
        )
        kb = KBContextPacket(
            kb_context_id="kbctx:x",
            project_id="x",
            phase="x",
            agent_id="x",
            task="x",
        )
        manager.create(contract, "p1", "task1", kb)
        manager.create(contract, "p1", "task2", kb)
        manager.create(contract, "p2", "task3", kb)
        assert len(manager.by_project("p1")) == 2
        assert len(manager.by_project("p2")) == 1

    def test_handoff_has_validation_required(self) -> None:
        manager = HandoffManager()
        contract = AgentRegistration(
            agent_id="test-agent",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=["test"],
            input_artifacts=["input"],
            output_artifacts=["output_schema"],
            allowed_kb_domains=["ops"],
            reviewed_by=["reviewer-1", "reviewer-2"],
        )
        kb = KBContextPacket(
            kb_context_id="kbctx:x",
            project_id="p1",
            phase="x",
            agent_id="x",
            task="x",
        )
        handoff = manager.create(contract, "p1", "task", kb)
        assert handoff.validation_required == ["reviewer-1", "reviewer-2"]
