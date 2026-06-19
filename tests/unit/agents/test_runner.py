"""Tests for RCTCO prompt runner."""

from __future__ import annotations

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
        assert len(handoff.validation_required) == 1


def _make_contract() -> AgentRegistration:
    return AgentRegistration(
        agent_id="test-agent",
        family=AgentFamily.OPERATIONS,
        role=AgentRole.CREATOR,
        capabilities=["test"],
        input_artifacts=["input"],
        output_artifacts=["output_schema_v1"],
        allowed_kb_domains=["ops"],
        reviewed_by=["reviewer-agent"],
        failure_modes=["bad_output"],
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
