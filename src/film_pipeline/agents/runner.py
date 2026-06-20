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
        """
        if prompt.core_task in self.mock_responses:
            return self.mock_responses[prompt.core_task]
        if self.model_adapter is not None:
            if self.model_router is None:
                raise RuntimeError(
                    "Model adapter is configured but no model router is set. "
                    "Pass model_router= to PromptRunner."
                )
            model_id, max_tokens, temperature = self.model_router.resolve_model_params(
                model_profile
            )
            return self.model_adapter.chat_json(
                prompt.rendered,
                model=model_id,
                system=prompt.role,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        # No mock matched, no model adapter — return fallback with a warning
        import logging

        _logger = logging.getLogger(__name__)
        _logger.warning(
            "PromptRunner.call_model falling back to generic mock — "
            "task '%s' not in mock_responses and no model_adapter configured.",
            prompt.core_task[:80],
        )
        return {"status": "ok", "agent": "mock", "output": {"_warning": "generic_fallback"}}

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
