"""Prompt template registry — versioned, agent-specific RCTCO templates.

Critical-path agents resolve templates from this registry. Generic fallback
prompts assembled from contract metadata are NOT permitted for critical
execution.

KB reference note: ``film-knowledge-base/promt.md`` is classified as
**manual reference** only — it is not wired into runtime prompt execution
and is not consumed by the prompt framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromptTemplate:
    """A versioned, agent-specific RCTCO prompt template."""

    template_id: str
    agent_id: str
    version: int
    role: str
    core_task: str
    context_template: str
    constraints: str
    output_format: str
    output_schema_ref: str
    quality_instructions: str = ""

    def render(self, **context_vars: str) -> str:
        """Render the template with context variable substitution."""
        ctx = self.context_template
        for key, value in context_vars.items():
            ctx = ctx.replace(f"{{{key}}}", value)
        parts = [
            f"# Role\n{self.role}",
            f"# Core Task\n{self.core_task}",
            f"# Context\n{ctx}",
            f"# Constraints\n{self.constraints}",
            f"# Output\n{self.output_format}",
        ]
        if self.quality_instructions:
            parts.append(self.quality_instructions)
        return "\n\n".join(parts)


@dataclass
class PromptTemplateRegistry:
    """Registry of dedicated prompt templates keyed by agent_id."""

    templates: dict[str, PromptTemplate] = field(default_factory=dict)

    def register(self, template: PromptTemplate) -> None:
        """Register a template. Overwrites existing for same agent_id."""
        self.templates[template.agent_id] = template

    def get(self, agent_id: str) -> PromptTemplate | None:
        """Get the template for an agent, or None if not registered."""
        return self.templates.get(agent_id)

    def get_required(self, agent_id: str) -> PromptTemplate:
        """Get the template for an agent, raising if not found."""
        template = self.templates.get(agent_id)
        if template is None:
            raise KeyError(
                f"No dedicated prompt template registered for agent '{agent_id}'. "
                f"Critical-path agents require dedicated templates — generic fallback is forbidden."
            )
        return template


# --- Session-scoped registry ---

_registry: PromptTemplateRegistry | None = None


def get_registry() -> PromptTemplateRegistry:
    """Return the session-scoped prompt template registry."""
    global _registry
    if _registry is None:
        _registry = PromptTemplateRegistry()
        _load_defaults(_registry)
    return _registry


def _load_defaults(reg: PromptTemplateRegistry) -> None:
    """Load the default prompt templates for all critical-path agents and validators."""
    from film_pipeline.agents.prompt_templates.defaults import load_all, load_validator_templates

    load_all(reg)
    load_validator_templates(reg)
