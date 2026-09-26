"""Shared prompt-template value object for agent prompt composition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


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
        """Render the template with context variable substitution.

        Substitution is applied across the whole assembled prompt, so
        ``{placeholder}`` tokens are filled in any section — role, core task,
        context, constraints, and output — not just the context block. The
        output-format JSON examples use ``"key": "..."`` form, never ``{key}``,
        so they are unaffected.
        """
        current_date = context_vars.get("current_date") or datetime.now(UTC).date().isoformat()
        parts = [
            f"# Role\n{self.role}",
            f"# Runtime Context\nCurrent date: {current_date}",
            f"# Core Task\n{self.core_task}",
            f"# Context\n{self.context_template}",
            f"# Constraints\n{self.constraints}",
            f"# Output\n{self.output_format}",
        ]
        if self.quality_instructions:
            parts.append(self.quality_instructions)
        text = "\n\n".join(parts)
        for key, value in context_vars.items():
            text = text.replace(f"{{{key}}}", value)
        return text
