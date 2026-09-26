"""RCTCO prompt runner — builds prompts, injects KB context, calls model.

Dedicated prompt templates (not generic RCTCO assembly) are required for
critical-path agent execution. Model selection always flows through the
ModelRouter — no hardcoded model strings in execution paths.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from film_pipeline.agents.model_adapter import ModelAdapter
from film_pipeline.agents.model_routing import ModelRouter
from film_pipeline.providers.failure_classifier import (
    compress_prompt_for_retry,
    is_token_limit_exceeded,
)
from film_pipeline.schemas.handoff import AgentRegistration
from film_pipeline.schemas.kb import KBContextPacket

if TYPE_CHECKING:
    from film_pipeline.agents._prompt_template import PromptTemplate

_logger = logging.getLogger(__name__)


@dataclass
class RCTCOPrompt:
    """A rendered RCTCO prompt ready for model execution."""

    role: str
    core_task: str
    context: str
    constraints: str
    output_format: str
    rendered: str = ""

    def __post_init__(self) -> None:
        current_date = datetime.now(UTC).date().isoformat()
        self.rendered = "\n\n".join(
            [
                f"# Role\n{self.role}",
                f"# Runtime Context\nCurrent date: {current_date}",
                f"# Core Task\n{self.core_task}",
                f"# Context\n{self.context}",
                f"# Constraints\n{self.constraints}",
                f"# Output\n{self.output_format}",
            ]
        )


@dataclass(frozen=True)
class _ResolvedCallParams:
    """Immutable parameters resolved for one real-call attempt ladder."""

    model_profile: str
    model_id: str
    max_tokens: int
    temperature: float
    top_p: float
    frequency_penalty: float
    fallback_model: str


@dataclass
class PromptRunner:
    """Builds RCTCO prompts, injects KB context, runs model, parses output.

    Uses mock responses by default. Pass ``model_adapter`` to call a real LLM
    via OpenRouter, and ``model_router`` to resolve model profiles. When a
    mock response is registered for a task it takes precedence over the real
    adapter.

    For real model calls, ``model_profile`` is REQUIRED — the runner resolves
    it through the router to determine the provider model id, max_tokens, and
    temperature.
    """

    mock_responses: dict[str, dict[str, Any]] = field(default_factory=dict)
    model_adapter: ModelAdapter | None = None
    model_router: ModelRouter | None = None

    def build_rctco(
        self,
        contract: AgentRegistration,
        kb_context: KBContextPacket,
        task: str,
    ) -> RCTCOPrompt:
        """Build an RCTCO prompt from the agent contract and KB context."""
        output_format = "Respond with valid JSON matching your output schema."
        return RCTCOPrompt(
            role=self._role_section(contract),
            core_task=task,
            context=self._kb_context_section(kb_context),
            constraints=self._constraint_section(contract),
            output_format=output_format,
        )

    @staticmethod
    def _role_section(contract: AgentRegistration) -> str:
        """Render the RCTCO Role block from the agent contract."""
        role = f"You are the {contract.agent_id} ({contract.role.value})."
        if contract.capabilities:
            role += f"\nCapabilities: {', '.join(contract.capabilities)}"
        return role

    @staticmethod
    def _kb_context_section(kb_context: KBContextPacket) -> str:
        """Render the Context block from KB authority/playbook/case refs."""
        context_parts: list[str] = []
        if kb_context.authority_policy_refs:
            context_parts.append(
                f"Authority policies: {', '.join(kb_context.authority_policy_refs)}"
            )
        if kb_context.playbook_refs:
            context_parts.append(f"Playbooks: {', '.join(kb_context.playbook_refs)}")
        if kb_context.case_study_refs:
            context_parts.append(f"Case studies: {', '.join(kb_context.case_study_refs)}")
        return "\n".join(context_parts) if context_parts else "No KB context."

    @staticmethod
    def _constraint_section(contract: AgentRegistration) -> str:
        """Render the Constraints block from the KB domain allow/block lists."""
        constraints = f"Allowed KB domains: {', '.join(contract.allowed_kb_domains) or 'all'}"
        if contract.blocked_kb_domains:
            constraints += f"\nBlocked KB domains: {', '.join(contract.blocked_kb_domains)}"
        if contract.failure_modes:
            constraints += f"\nAvoid: {', '.join(contract.failure_modes)}"
        return constraints

    def _find_mock_response(
        self, core_task: str, *, agent_id: str | None = None
    ) -> dict[str, Any] | None:
        """Match a mock response by ``agent_id``, falling back to exact task match.

        Mock responses are keyed by agent_id (e.g. ``"intake-classifier-agent"``)
        so routing is unambiguous regardless of how task strings are worded.
        Exact ``core_task`` match is kept as a secondary fallback for backward
        compatibility.
        """
        if not self.mock_responses:
            return None
        if agent_id is not None and agent_id in self.mock_responses:
            return self.mock_responses[agent_id]
        if core_task in self.mock_responses:
            return self.mock_responses[core_task]
        return None

    @staticmethod
    def _generic_mock_fallback(core_task: str) -> dict[str, Any]:
        """Return the canned response used when no mock matched and no adapter exists."""
        _logger.warning(
            "PromptRunner.call_model falling back to generic mock — "
            "task '%s' not in mock_responses and no model_adapter configured.",
            core_task[:80],
        )
        return {"status": "ok", "agent": "mock", "output": {"_warning": "generic_fallback"}}

    def _resolve_real_call_params(
        self,
        model_profile: str,
        model_overrides: dict[str, object] | None,
    ) -> _ResolvedCallParams:
        """Resolve profile + config overrides into immutable real-call parameters."""
        router = self.model_router
        assert router is not None
        (
            model_id,
            max_tokens,
            temperature,
            top_p,
            frequency_penalty,
        ) = router.resolve_model_params(model_profile, model_overrides)
        try:
            override_fallback = (model_overrides or {}).get("fallback")
            fallback_model = (
                str(override_fallback) if override_fallback else router.fallback(model_profile)
            )
        except Exception:
            fallback_model = model_id
        return _ResolvedCallParams(
            model_profile=model_profile,
            model_id=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            fallback_model=fallback_model,
        )

    @staticmethod
    def _json_instruction_suffix(text: str) -> str:
        """Append the strict-JSON directive required on structured retries."""
        return text + (
            "\n\n!!! IMPORTANT: You MUST output valid, parseable JSON. "
            "No markdown commentary, no trailing text — just pure JSON."
        )

    def _chat_once(
        self,
        params: _ResolvedCallParams,
        prompt_text: str,
        *,
        system_role: str,
    ) -> dict[str, Any]:
        """Issue a single chat_json call with fully unpacked resolved parameters."""
        adapter = self.model_adapter
        assert adapter is not None
        return adapter.chat_json(
            prompt_text,
            model=params.model_id,
            system=system_role,
            max_tokens=params.max_tokens,
            temperature=params.temperature,
            top_p=params.top_p,
            frequency_penalty=params.frequency_penalty,
        )

    def _attempt_normal_call(
        self,
        prompt: RCTCOPrompt,
        params: _ResolvedCallParams,
    ) -> tuple[dict[str, Any] | None, str]:
        """Attempt 1 — normal call with assigned profile; may compress on token limit.

        Returns ``(result, rendered_prompt)`` where result is None when the
        attempt ladder must continue and rendered_prompt reflects any compression.
        """
        rendered_prompt = prompt.rendered
        try:
            return (
                self._chat_once(params, rendered_prompt, system_role=prompt.role),
                rendered_prompt,
            )
        except Exception as exc:
            if is_token_limit_exceeded(exc, params.model_id):
                rendered_prompt = compress_prompt_for_retry(rendered_prompt, factor=0.6)
                _logger.warning(
                    "PromptRunner.call_model hit token limit for profile '%s' "
                    "(model=%s). Compressed context for retry.",
                    params.model_profile,
                    params.model_id,
                )
            elif isinstance(exc, (ValueError, RuntimeError)):
                pass
            else:
                raise

        _logger.warning(
            "PromptRunner.call_model attempt 1 failed for profile '%s' (model=%s). "
            "Retrying with temperature 0.1.",
            params.model_profile,
            params.model_id,
        )
        return None, rendered_prompt

    def _attempt_structured_retry(
        self,
        prompt: RCTCOPrompt,
        params: _ResolvedCallParams,
        rendered_prompt: str,
    ) -> tuple[dict[str, Any] | None, str]:
        """Attempt 2 — lower temperature plus explicit JSON instruction.

        Returns ``(result, retry_prompt)`` where retry_prompt carries any further
        compression forward into the fallback-model attempt.
        """
        retry_prompt = self._json_instruction_suffix(rendered_prompt)
        try:
            return (
                self._chat_once(
                    replace(params, temperature=0.1), retry_prompt, system_role=prompt.role
                ),
                retry_prompt,
            )
        except Exception as exc:
            if is_token_limit_exceeded(exc, params.model_id):
                compressed = compress_prompt_for_retry(rendered_prompt, factor=0.35)
                retry_prompt = self._json_instruction_suffix(compressed)
                _logger.warning(
                    "PromptRunner.call_model hit token limit again for profile '%s' "
                    "(model=%s). Compressed context more aggressively for fallback.",
                    params.model_profile,
                    params.model_id,
                )
            elif isinstance(exc, (ValueError, RuntimeError)):
                pass
            else:
                raise
        return None, retry_prompt

    @staticmethod
    def _all_retries_exhausted(
        params: _ResolvedCallParams, *, fallback_model: str | None = None
    ) -> dict[str, Any]:
        """Build the terminal error dict returned when the 3-attempt ladder exhausts."""
        failure: dict[str, Any] = {
            "status": "model_failure",
            "agent": "prompt_runner",
            "error": "all_retries_exhausted",
            "profile": params.model_profile,
            "model": params.model_id,
        }
        if fallback_model is not None:
            failure["fallback_model"] = fallback_model
        return failure

    def _attempt_fallback_model(
        self,
        prompt: RCTCOPrompt,
        params: _ResolvedCallParams,
        retry_prompt: str,
    ) -> dict[str, Any]:
        """Attempt 3 — distinct fallback model, else terminal exhaustion dict."""
        if params.fallback_model == params.model_id:
            _logger.error(
                "PromptRunner.call_model all 3 attempts failed for profile '%s'. "
                "No distinct fallback model available.",
                params.model_profile,
            )
            return self._all_retries_exhausted(params)

        _logger.warning(
            "PromptRunner.call_model attempt 2 failed. Retrying with fallback model %s.",
            params.fallback_model,
        )
        try:
            return self._chat_once(
                replace(params, temperature=0.1, model_id=params.fallback_model),
                retry_prompt,
                system_role=prompt.role,
            )
        except (ValueError, RuntimeError):
            _logger.error(
                "PromptRunner.call_model all 3 attempts failed — "
                "profile=%s, model=%s, fallback=%s.",
                params.model_profile,
                params.model_id,
                params.fallback_model,
            )
            return self._all_retries_exhausted(params, fallback_model=params.fallback_model)

    def call_model(
        self,
        prompt: RCTCOPrompt,
        *,
        model_profile: str = "operations_triage",
        agent_id: str | None = None,
        model_overrides: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        """Call the model. Uses mock if a canned response is registered.

        When ``model_adapter`` is set and no mock matches, resolves the model
        through the router and calls the real LLM, expecting a JSON response.

        Retry strategy (3 attempts):
        1. Normal call with assigned profile.
        2. Retry with temperature 0.1 + explicit JSON instruction.
        3. Retry with fallback model.
        After 3 failures, returns an error dict (never crashes).
        """
        mock_response = self._find_mock_response(prompt.core_task, agent_id=agent_id)
        if mock_response is not None:
            return mock_response
        if self.model_adapter is None:
            return self._generic_mock_fallback(prompt.core_task)
        if self.model_router is None:
            raise RuntimeError(
                "Model adapter is configured but no model router is set. "
                "Pass model_router= to PromptRunner."
            )
        params = self._resolve_real_call_params(model_profile, model_overrides)
        first, rendered_prompt = self._attempt_normal_call(prompt, params)
        if first is not None:
            return first
        second, retry_prompt = self._attempt_structured_retry(prompt, params, rendered_prompt)
        if second is not None:
            return second
        return self._attempt_fallback_model(prompt, params, retry_prompt)

    def run(
        self,
        contract: AgentRegistration,
        kb_context: KBContextPacket,
        task: str,
        *,
        model_profile: str = "operations_triage",
    ) -> dict[str, Any]:
        """Full run: build RCTCO → call model → parse output."""
        prompt = self.build_rctco(contract, kb_context, task)
        raw = self.call_model(prompt, model_profile=model_profile, agent_id=contract.agent_id)
        return self._ensure_dict_output(raw)

    def run_from_template(
        self,
        template: PromptTemplate,
        _kb_context: KBContextPacket,
        task: str,
        *,
        model_profile: str = "operations_triage",
        context_vars: dict[str, str] | None = None,
        agent_id: str | None = None,
        model_overrides: dict[str, object] | None = None,
    ) -> tuple[dict[str, Any], str, str]:
        """Run using a dedicated prompt template. Returns (output, template_id, model_profile).

        This is the REQUIRED path for critical-agent execution. Generic RCTCO
        assembly via ``run()`` is forbidden for critical-path agents.
        ``model_overrides`` lets a project's resolved config swap the model/params
        for this profile without a code edit.
        """
        rendered_text = template.render(**(context_vars or {}))
        prompt = self._template_to_prompt(template, task, rendered_text)
        raw = self.call_model(
            prompt,
            model_profile=model_profile,
            agent_id=agent_id,
            model_overrides=model_overrides,
        )
        return self._ensure_dict_output(raw), template.template_id, model_profile

    @staticmethod
    def _template_to_prompt(template: PromptTemplate, task: str, rendered_text: str) -> RCTCOPrompt:
        """Wrap a rendered dedicated template in a prompt for call_model compatibility.

        Mock dispatch keys off ``core_task``, so the lightweight prompt carries
        the raw task string rather than template content.
        """
        prompt = RCTCOPrompt(
            role=template.role,
            core_task=task,
            context=rendered_text,
            constraints=template.constraints,
            output_format=template.output_format,
        )
        prompt.rendered = rendered_text
        return prompt

    @staticmethod
    def _ensure_dict_output(raw: Any) -> dict[str, Any]:
        """Return the model output as a dict or raise the standard ValueError."""
        if not isinstance(raw, dict):
            raise ValueError(f"Model output is not a dict: {type(raw)}")
        return raw
