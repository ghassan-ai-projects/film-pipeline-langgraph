"""Tests for RCTCO prompt runner."""

from __future__ import annotations

import pytest

from film_pipeline.agents.runner import PromptRunner, RCTCOPrompt
from film_pipeline.schemas._base import AgentFamily, AgentRole
from film_pipeline.schemas.handoff import AgentRegistration
from film_pipeline.schemas.kb import KBContextPacket


class TestRCTCOPrompt:
    def test_rendered_contains_role(self) -> None:
        prompt = RCTCOPrompt(
            role="You are a test agent.",
            core_task="Write a scene.",
            context="A dark forest.",
            constraints="Max 200 words.",
            output_format="JSON",
        )
        assert "# Role" in prompt.rendered
        assert "test agent" in prompt.rendered
        assert "# Core Task" in prompt.rendered
        assert "Write a scene" in prompt.rendered
        assert "# Context" in prompt.rendered
        assert "# Constraints" in prompt.rendered
        assert "# Output" in prompt.rendered


class TestPromptRunner:
    def test_build_rctco(self) -> None:
        runner = PromptRunner()
        contract = _make_contract()
        kb = _make_kb()

        prompt = runner.build_rctco(contract, kb, "Test task")
        assert isinstance(prompt, RCTCOPrompt)
        assert "test-agent" in prompt.role
        assert "Test task" in prompt.core_task
        assert "kb.policy.prompt.rctco.v1" in prompt.context
        assert "Allowed KB domains" in prompt.constraints
        assert "JSON" in prompt.output_format

    def test_call_model_default(self) -> None:
        runner = PromptRunner()
        prompt = RCTCOPrompt(
            role="r", core_task="ct", context="c", constraints="x", output_format="y"
        )
        result = runner.call_model(prompt)
        assert result == {"status": "ok", "agent": "mock", "output": {}}

    def test_call_model_mock_response(self) -> None:
        runner = PromptRunner(mock_responses={"Test task": {"result": "canned", "score": 95}})
        prompt = RCTCOPrompt(
            role="r", core_task="Test task", context="c", constraints="x", output_format="y"
        )
        result = runner.call_model(prompt)
        assert result == {"result": "canned", "score": 95}

    def test_run_complete(self) -> None:
        runner = PromptRunner(mock_responses={"Test task": {"valid": True, "data": [1, 2, 3]}})
        contract = _make_contract()
        kb = _make_kb()
        result = runner.run(contract, kb, "Test task")
        assert result["valid"] is True
        assert result["data"] == [1, 2, 3]

    def test_create_handoff(self) -> None:
        runner = PromptRunner()
        contract = _make_contract()
        kb = _make_kb()
        handoff = runner.create_handoff(
            contract,
            handoff_id="h1",
            project_id="p1",
            task="Test task",
            kb_context=kb,
        )
        assert handoff.from_agent == "test-agent"
        assert handoff.project_id == "p1"
        assert handoff.kb_context_ref == kb.kb_context_id

    def test_create_handoff_with_artifacts(self) -> None:
        runner = PromptRunner()
        contract = _make_contract()
        kb = _make_kb()
        handoff = runner.create_handoff(
            contract,
            handoff_id="h2",
            project_id="p2",
            task="Test task",
            kb_context=kb,
            input_artifact_refs=["artifact:script:v1", "artifact:scene:v2"],
        )
        assert handoff.input_artifact_refs == ["artifact:script:v1", "artifact:scene:v2"]

    def test_run_with_string_output_raises(self) -> None:
        runner = PromptRunner(mock_responses={"Test task": "not a dict"})  # type: ignore[dict-item]
        contract = _make_contract()
        kb = _make_kb()
        with pytest.raises(ValueError, match="not a dict"):
            runner.run(contract, kb, "Test task")

    def test_build_rctco_with_blocked_domains(self) -> None:
        runner = PromptRunner()
        contract = _make_contract(blocked_kb_domains=["cost", "providers"])
        kb = _make_kb()
        prompt = runner.build_rctco(contract, kb, "Test task")
        assert "Blocked KB domains: cost, providers" in prompt.constraints

    def test_build_rctco_with_failure_modes(self) -> None:
        runner = PromptRunner()
        contract = _make_contract(failure_modes=["bad_output", "timeout"])
        kb = _make_kb()
        prompt = runner.build_rctco(contract, kb, "Test task")
        assert "Avoid: bad_output, timeout" in prompt.constraints

    def test_build_rctco_empty_kb_context(self) -> None:
        runner = PromptRunner()
        contract = _make_contract()
        kb = KBContextPacket(
            kb_context_id="kbctx:empty:v1",
            project_id="p1",
            phase="x",
            agent_id="x",
            task="x",
        )
        prompt = runner.build_rctco(contract, kb, "Test task")
        assert "No KB context." in prompt.context

    def test_call_model_default_path(self) -> None:
        runner = PromptRunner()
        prompt = RCTCOPrompt(
            role="r", core_task="unknown", context="c", constraints="x", output_format="y"
        )
        result = runner.call_model(prompt)
        assert result == {"status": "ok", "agent": "mock", "output": {}}

    def test_call_model_with_adapter_and_no_mock(self) -> None:
        """When model_adapter is set and no mock matches, call the real adapter."""
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()
        mock_adapter.chat_json.return_value = {"real": True, "score": 100}
        runner = PromptRunner(model_adapter=mock_adapter)
        prompt = RCTCOPrompt(
            role="You are a test agent.",
            core_task="Real LLM task",
            context="Some context",
            constraints="Be brief",
            output_format="JSON",
        )
        result = runner.call_model(prompt)
        assert result == {"real": True, "score": 100}
        mock_adapter.chat_json.assert_called_once()
        call_kwargs = mock_adapter.chat_json.call_args.kwargs
        assert call_kwargs["temperature"] == 0.7
        assert "You are a test agent." in call_kwargs["system"]

    def test_call_model_mock_wins_over_adapter(self) -> None:
        """Mock response takes precedence even when adapter is configured."""
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()
        runner = PromptRunner(
            mock_responses={"Test task": {"from_mock": True}},
            model_adapter=mock_adapter,
        )
        prompt = RCTCOPrompt(
            role="r", core_task="Test task", context="c", constraints="x", output_format="y"
        )
        result = runner.call_model(prompt)
        assert result == {"from_mock": True}
        mock_adapter.chat_json.assert_not_called()


def _make_contract(
    blocked_kb_domains: list[str] | None = None,
    failure_modes: list[str] | None = None,
) -> AgentRegistration:
    return AgentRegistration(
        agent_id="test-agent",
        family=AgentFamily.OPERATIONS,
        role=AgentRole.CREATOR,
        capabilities=["test"],
        input_artifacts=["input"],
        output_artifacts=["output_schema_v1"],
        allowed_kb_domains=["ops"],
        blocked_kb_domains=blocked_kb_domains or [],
        reviewed_by=["reviewer-agent"],
        failure_modes=failure_modes or [],
    )


def _make_kb() -> KBContextPacket:
    return KBContextPacket(
        kb_context_id="kbctx:p1:agent:v1",
        project_id="p1",
        phase="generation",
        agent_id="test-agent",
        task="Test task",
        authority_policy_refs=["kb.policy.prompt.rctco.v1"],
        playbook_refs=["kb.playbook.sequential_chain.v1"],
        case_study_refs=["kb.lesson.cost_overrun.v1"],
        payload={"kb.policy.prompt.rctco.v1": "prompt-framework.md"},
    )
