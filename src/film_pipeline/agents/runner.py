"""RCTCO prompt runner — builds prompts, injects KB context, calls model.

Dedicated prompt templates (not generic RCTCO assembly) are required for
critical-path agent execution. Model selection always flows through the
ModelRouter — no hardcoded model strings in execution paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from film_pipeline.agents.model_adapter import ModelAdapter
from film_pipeline.agents.model_routing import ModelRouter
from film_pipeline.schemas.handoff import AgentHandoff, AgentRegistration
from film_pipeline.schemas.kb import KBContextPacket


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
        self.rendered = "\n\n".join(
            [
                f"# Role\n{self.role}",
                f"# Core Task\n{self.core_task}",
                f"# Context\n{self.context}",
                f"# Constraints\n{self.constraints}",
                f"# Output\n{self.output_format}",
            ]
        )


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
        # Role from contract
        role = f"You are the {contract.agent_id} ({contract.role.value})."
        if contract.capabilities:
            role += f"\nCapabilities: {', '.join(contract.capabilities)}"

        # Core task from task parameter
        core_task = task

        # Context from KB context packet
        context_parts: list[str] = []
        if kb_context.authority_policy_refs:
            context_parts.append(
                f"Authority policies: {', '.join(kb_context.authority_policy_refs)}"
            )
        if kb_context.playbook_refs:
            context_parts.append(f"Playbooks: {', '.join(kb_context.playbook_refs)}")
        if kb_context.case_study_refs:
            context_parts.append(f"Case studies: {', '.join(kb_context.case_study_refs)}")
        context = "\n".join(context_parts) if context_parts else "No KB context."

        # Constraints from contract
        constraints = f"Allowed KB domains: {', '.join(contract.allowed_kb_domains) or 'all'}"
        if contract.blocked_kb_domains:
            constraints += f"\nBlocked KB domains: {', '.join(contract.blocked_kb_domains)}"
        if contract.failure_modes:
            constraints += f"\nAvoid: {', '.join(contract.failure_modes)}"

        # Output format
        output_format = "Respond with valid JSON matching your output schema."

        return RCTCOPrompt(
            role=role,
            core_task=core_task,
            context=context,
            constraints=constraints,
            output_format=output_format,
        )

    def call_model(
        self,
        prompt: RCTCOPrompt,
        *,
        model_profile: str = "operations_triage",
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
        if prompt.core_task in self.mock_responses:
            return self.mock_responses[prompt.core_task]
        if self.model_adapter is None:
            import logging

            _logger = logging.getLogger(__name__)
            _logger.warning(
                "PromptRunner.call_model falling back to generic mock — "
                "task '%s' not in mock_responses and no model_adapter configured.",
                prompt.core_task[:80],
            )
            return {"status": "ok", "agent": "mock", "output": {"_warning": "generic_fallback"}}
        if self.model_router is None:
            raise RuntimeError(
                "Model adapter is configured but no model router is set. "
                "Pass model_router= to PromptRunner."
            )

        import logging

        _logger = logging.getLogger(__name__)
        model_id, max_tokens, temperature, top_p, frequency_penalty = (
            self.model_router.resolve_model_params(model_profile)
        )

        # --- Attempt 1: normal call ---
        try:
            return self.model_adapter.chat_json(
                prompt.rendered,
                model=model_id,
                system=prompt.role,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
            )
        except ValueError:
            pass

        _logger.warning(
            "PromptRunner.call_model attempt 1 failed for profile '%s' (model=%s). "
            "Retrying with temperature 0.1.",
            model_profile,
            model_id,
        )

        # --- Attempt 2: lower temperature + explicit JSON instruction ---
        retry_prompt = (
            prompt.rendered + "\n\n!!! IMPORTANT: You MUST output valid, parseable JSON. "
            "No markdown commentary, no trailing text — just pure JSON."
        )
        try:
            return self.model_adapter.chat_json(
                retry_prompt,
                model=model_id,
                system=prompt.role,
                max_tokens=max_tokens,
                temperature=0.1,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
            )
        except ValueError:
            pass

        # --- Attempt 3: fallback model ---
        try:
            fallback_model = self.model_router.fallback(model_profile)
        except Exception:
            fallback_model = model_id
        if fallback_model == model_id:
            _logger.error(
                "PromptRunner.call_model all 3 attempts failed for profile '%s'. "
                "No distinct fallback model available.",
                model_profile,
            )
            return {
                "status": "model_failure",
                "agent": "prompt_runner",
                "error": "all_retries_exhausted",
                "profile": model_profile,
                "model": model_id,
            }

        _logger.warning(
            "PromptRunner.call_model attempt 2 failed. Retrying with fallback model %s.",
            fallback_model,
        )
        try:
            return self.model_adapter.chat_json(
                retry_prompt,
                model=fallback_model,
                system=prompt.role,
                max_tokens=max_tokens,
                temperature=0.1,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
            )
        except ValueError:
            _logger.error(
                "PromptRunner.call_model all 3 attempts failed — "
                "profile=%s, model=%s, fallback=%s.",
                model_profile,
                model_id,
                fallback_model,
            )
            return {
                "status": "model_failure",
                "agent": "prompt_runner",
                "error": "all_retries_exhausted",
                "profile": model_profile,
                "model": model_id,
                "fallback_model": fallback_model,
            }

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
        raw = self.call_model(prompt, model_profile=model_profile)
        # Validate it's a dict (basic)
        if not isinstance(raw, dict):
            raise ValueError(f"Model output is not a dict: {type(raw)}")
        return raw

    def run_from_template(
        self,
        template: Any,  # PromptTemplate (lazy import to avoid circular)
        _kb_context: KBContextPacket,
        task: str,
        *,
        model_profile: str = "operations_triage",
        context_vars: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], str, str]:
        """Run using a dedicated prompt template. Returns (output, template_id, model_profile).

        This is the REQUIRED path for critical-agent execution. Generic RCTCO
        assembly via ``run()`` is forbidden for critical-path agents.
        """
        # Render the dedicated template
        rendered_text = template.render(**(context_vars or {}))

        # Build a lightweight prompt for call_model() compatibility (mock dispatch uses core_task)
        prompt = RCTCOPrompt(
            role=template.role,
            core_task=task,
            context=rendered_text,
            constraints=template.constraints,
            output_format=template.output_format,
        )
        prompt.rendered = rendered_text

        raw = self.call_model(prompt, model_profile=model_profile)
        if not isinstance(raw, dict):
            raise ValueError(f"Model output is not a dict: {type(raw)}")
        return raw, template.template_id, model_profile

    def create_handoff(
        self,
        contract: AgentRegistration,
        handoff_id: str,
        project_id: str,
        task: str,
        kb_context: KBContextPacket,
        input_artifact_refs: list[str] | None = None,
    ) -> AgentHandoff:
        """Create a handoff record for this agent invocation."""
        return AgentHandoff(
            handoff_id=handoff_id,
            from_agent=contract.agent_id,
            to_agent="orchestrator-agent",
            project_id=project_id,
            input_artifact_refs=input_artifact_refs or [],
            kb_context_ref=kb_context.kb_context_id,
            task=task,
            expected_output_schema=(
                contract.output_artifacts[0] if contract.output_artifacts else "any"
            ),
            validation_required=contract.reviewed_by,
        )
