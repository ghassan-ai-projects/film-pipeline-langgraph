"""Tests for BaseAgent abstract class."""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas._base import AgentFamily, AgentRole
from film_pipeline.schemas.handoff import AgentRegistration
from film_pipeline.schemas.kb import KBContextPacket


class _ConcreteAgent(BaseAgent):
    """Minimal concrete agent for testing BaseAgent lifecycle."""

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: KBContextPacket,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context  # Used in real agents, not in test stub
        return {"state": state, "task": task}

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        return {"result": model_output.get("value", "empty")}

    def validate(self, result: dict[str, Any]) -> bool:
        return "result" in result


@pytest.fixture
def contract() -> AgentRegistration:
    return AgentRegistration(
        agent_id="concrete-agent",
        family=AgentFamily.OPERATIONS,
        role=AgentRole.CREATOR,
        capabilities=["test"],
        input_artifacts=["input"],
        output_artifacts=["output"],
        allowed_kb_domains=["ops"],
        reviewed_by=["reviewer"],
    )


@pytest.fixture
def kb() -> KBContextPacket:
    return KBContextPacket(
        kb_context_id="kbctx:x",
        project_id="p1",
        phase="x",
        agent_id="x",
        task="x",
    )


class TestBaseAgent:
    def test_contract_stored(self, contract: AgentRegistration) -> None:
        agent = _ConcreteAgent(contract)
        assert agent.contract.agent_id == "concrete-agent"

    def test_prepare(self, contract: AgentRegistration, kb: KBContextPacket) -> None:
        agent = _ConcreteAgent(contract)
        result = agent.prepare({"phase": "intake"}, kb, "Classify")
        assert result["state"] == {"phase": "intake"}
        assert result["task"] == "Classify"

    def test_execute(self, contract: AgentRegistration) -> None:
        agent = _ConcreteAgent(contract)
        result = agent.execute({"value": "done"})
        assert result["result"] == "done"

    def test_validate_pass(self, contract: AgentRegistration) -> None:
        agent = _ConcreteAgent(contract)
        assert agent.validate({"result": "ok"}) is True

    def test_validate_fail(self, contract: AgentRegistration) -> None:
        agent = _ConcreteAgent(contract)
        assert agent.validate({"wrong": "key"}) is False

    def test_run_success(self, contract: AgentRegistration, kb: KBContextPacket) -> None:
        agent = _ConcreteAgent(contract)
        result = agent.run(
            state={"phase": "intake"},
            kb_context=kb,
            task="Classify",
            model_output={"value": "success"},
        )
        assert result["result"] == "success"

    def test_run_validation_fails(self, contract: AgentRegistration, kb: KBContextPacket) -> None:
        class _FailingAgent(_ConcreteAgent):
            def validate(self, _result: dict[str, Any]) -> bool:
                return False

        failing = _FailingAgent(contract)
        try:
            failing.run({"phase": "intake"}, kb, "task", {"value": "x"})
            raise AssertionError("Expected ValueError")
        except ValueError:
            pass
