"""Tests for RCTCO prompt runner."""

from __future__ import annotations

import pytest

from film_pipeline.agents.model_routing import ModelRouter
from film_pipeline.agents.runner import PromptRunner, RCTCOPrompt
from film_pipeline.schemas.base import AgentFamily, AgentRole
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
        assert result == {
            "status": "ok",
            "agent": "mock",
            "output": {"_warning": "generic_fallback"},
        }

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
        assert result == {
            "status": "ok",
            "agent": "mock",
            "output": {"_warning": "generic_fallback"},
        }

    def test_call_model_with_adapter_and_no_mock(self) -> None:
        """When model_adapter is set and no mock matches, call the real adapter."""
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()
        mock_adapter.chat_json.return_value = {"real": True, "score": 100}
        router = ModelRouter(
            profiles={
                "operations_triage": {
                    "primary": "test-model",
                    "max_tokens": 1024,
                    "temperature": 0.2,
                }
            }
        )
        runner = PromptRunner(model_adapter=mock_adapter, model_router=router)
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
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["model"] == "test-model"
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

    def test_call_model_raises_when_adapter_set_but_no_router(self) -> None:
        """call_model raises RuntimeError when model_adapter is set but model_router is None."""
        from unittest.mock import MagicMock

        runner = PromptRunner(model_adapter=MagicMock(), model_router=None)
        prompt = RCTCOPrompt(
            role="r",
            core_task="test",
            context="c",
            constraints="x",
            output_format="y",
        )
        with pytest.raises(RuntimeError, match="no model router is set"):
            runner.call_model(prompt)

    def test_retry_on_json_parse_failure(self) -> None:
        """Three attempts with escalation on repeated ValueError."""
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()
        mock_adapter.chat_json.side_effect = [
            ValueError("bad json"),
            ValueError("bad json again"),
            ValueError("still bad"),
        ]
        router = ModelRouter(
            profiles={
                "operations_triage": {
                    "primary": "primary-model",
                    "fallback": "fallback-model",
                    "max_tokens": 1024,
                    "temperature": 0.2,
                }
            }
        )
        runner = PromptRunner(model_adapter=mock_adapter, model_router=router)
        prompt = RCTCOPrompt(
            role="r",
            core_task="fail",
            context="c",
            constraints="x",
            output_format="y",
        )
        result = runner.call_model(prompt, model_profile="operations_triage")
        assert result["status"] == "model_failure"
        assert result["error"] == "all_retries_exhausted"
        assert result["profile"] == "operations_triage"
        assert mock_adapter.chat_json.call_count == 3
        # Attempt 2: temperature 0.1
        assert mock_adapter.chat_json.call_args_list[1].kwargs["temperature"] == 0.1
        # Attempt 3: fallback model
        assert mock_adapter.chat_json.call_args_list[2].kwargs["model"] == "fallback-model"

    def test_retry_succeeds_on_second_attempt(self) -> None:
        """If first call fails, second succeeds with lower temp."""
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()
        mock_adapter.chat_json.side_effect = [
            ValueError("bad"),
            {"recovered": True},
        ]
        router = ModelRouter(
            profiles={
                "operations_triage": {
                    "primary": "pm",
                    "max_tokens": 1024,
                    "temperature": 0.2,
                }
            }
        )
        runner = PromptRunner(model_adapter=mock_adapter, model_router=router)
        prompt = RCTCOPrompt(
            role="r",
            core_task="recover",
            context="c",
            constraints="x",
            output_format="y",
        )
        result = runner.call_model(prompt, model_profile="operations_triage")
        assert result == {"recovered": True}
        assert mock_adapter.chat_json.call_count == 2

    def test_retry_succeeds_with_fallback_model(self) -> None:
        """Third attempt uses fallback model and succeeds."""
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()
        mock_adapter.chat_json.side_effect = [
            ValueError("bad"),
            ValueError("bad2"),
            {"fallback_saved_us": True},
        ]
        router = ModelRouter(
            profiles={
                "creative_writer": {
                    "primary": "primary-x",
                    "fallback": "cheap-fallback",
                    "max_tokens": 8192,
                    "temperature": 0.7,
                }
            }
        )
        runner = PromptRunner(model_adapter=mock_adapter, model_router=router)
        prompt = RCTCOPrompt(
            role="r",
            core_task="fb",
            context="c",
            constraints="x",
            output_format="y",
        )
        result = runner.call_model(prompt, model_profile="creative_writer")
        assert result == {"fallback_saved_us": True}
        assert mock_adapter.chat_json.call_count == 3
        # Third attempt uses fallback
        assert mock_adapter.chat_json.call_args_list[2].kwargs["model"] == "cheap-fallback"

    def test_provider_runtime_errors_reach_fallback_model(self) -> None:
        """Transport/auth failures must use the same fallback ladder as bad JSON."""
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()
        mock_adapter.chat_json.side_effect = [
            RuntimeError("z.ai unavailable"),
            RuntimeError("z.ai still unavailable"),
            {"recovered": "fallback"},
        ]
        router = ModelRouter(
            profiles={
                "creative_writer": {
                    "primary": "zai/glm-5.3-flash",
                    "fallback": "openrouter/fallback",
                    "max_tokens": 1024,
                    "temperature": 0.2,
                }
            }
        )
        runner = PromptRunner(model_adapter=mock_adapter, model_router=router)
        prompt = RCTCOPrompt(
            role="r",
            core_task="provider-failure",
            context="c",
            constraints="x",
            output_format="y",
        )

        assert runner.call_model(prompt, model_profile="creative_writer") == {
            "recovered": "fallback"
        }
        assert mock_adapter.chat_json.call_count == 3
        assert mock_adapter.chat_json.call_args_list[2].kwargs["model"] == "openrouter/fallback"

    def test_provider_runtime_errors_are_normalized_after_fallback(self) -> None:
        """An unavailable primary and fallback return a stable failure envelope."""
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()
        mock_adapter.chat_json.side_effect = RuntimeError("provider unavailable")
        router = ModelRouter(
            profiles={
                "operations_triage": {
                    "primary": "zai/glm-5.3-flash",
                    "fallback": "openrouter/fallback",
                    "max_tokens": 1024,
                    "temperature": 0.2,
                }
            }
        )
        runner = PromptRunner(model_adapter=mock_adapter, model_router=router)
        prompt = RCTCOPrompt(
            role="r",
            core_task="provider-failure",
            context="c",
            constraints="x",
            output_format="y",
        )

        result = runner.call_model(prompt, model_profile="operations_triage")
        assert result["status"] == "model_failure"
        assert result["fallback_model"] == "openrouter/fallback"
        assert mock_adapter.chat_json.call_count == 3

    def test_token_limit_retry_compresses_context_before_retry(self) -> None:
        """Token-limit failures shrink context instead of replaying the same prompt."""
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()
        mock_adapter.chat_json.side_effect = [
            ValueError("context_length_exceeded: maximum context length"),
            {"recovered": True},
        ]
        router = ModelRouter(
            profiles={
                "operations_triage": {
                    "primary": "openai/gpt-4.1",
                    "max_tokens": 1024,
                    "temperature": 0.2,
                }
            }
        )
        runner = PromptRunner(model_adapter=mock_adapter, model_router=router)
        prompt = RCTCOPrompt(
            role="r",
            core_task="recover",
            context="0123456789" * 1000,
            constraints="x",
            output_format="y",
        )
        result = runner.call_model(prompt, model_profile="operations_triage")
        assert result == {"recovered": True}
        first_prompt = mock_adapter.chat_json.call_args_list[0].args[0]
        second_prompt = mock_adapter.chat_json.call_args_list[1].args[0]
        assert len(second_prompt) < len(first_prompt)
        assert "context compressed for retry" in second_prompt

    def test_run_from_template_includes_quality_instructions(self) -> None:
        """run_from_template renders quality_instructions into the prompt."""
        from unittest.mock import MagicMock

        from film_pipeline.agents.prompt_templates.registry import PromptTemplate

        template = PromptTemplate(
            template_id="test-tpl",
            agent_id="test-agent",
            version=1,
            role="Test Role",
            core_task="Test Task",
            context_template="ctx: {idea}",
            constraints="Be good.",
            output_format="JSON",
            output_schema_ref="test",
            quality_instructions="QUALITY REQUIREMENTS:\n- Be detailed.",
        )
        mock_adapter = MagicMock()
        mock_adapter.chat_json.return_value = {"ok": True}
        router = ModelRouter(
            profiles={
                "operations_triage": {
                    "primary": "m",
                    "max_tokens": 1024,
                    "temperature": 0.2,
                }
            }
        )
        runner = PromptRunner(model_adapter=mock_adapter, model_router=router)
        kb = _make_kb()
        runner.run_from_template(template, kb, "Task", context_vars={"idea": "test"})
        call_arg = mock_adapter.chat_json.call_args[0][0]  # first positional arg
        assert "QUALITY REQUIREMENTS" in call_arg
        assert "Be detailed." in call_arg


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
