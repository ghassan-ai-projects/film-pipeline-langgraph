"""Prompt registry — RCTCO prompt packages."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas.base import SchemaBase


class RCTCOPrompt(SchemaBase):
    """Role / Core Task / Context / Constraints / Output prompt package.

    Every agent prompt conforms to this shape (see RCTCO framework in
    ``film-knowledge-base/prompt-framework.md``).
    """

    r: str = Field(description="Role.")
    c1: str = Field(description="Core task.")
    t: dict[str, str] = Field(default_factory=dict, description="Context inputs.")
    c2: list[str] = Field(default_factory=list, description="Constraints.")
    o_format: str = Field(default="json", description="Output format spec.")
    o_schema_ref: str = Field(default="", description="Schema id for validation.")

    def render(self) -> str:
        """Render a human-readable prompt body for logging or fallback."""
        constraints = "\n".join(f"- {c}" for c in self.c2) if self.c2 else "- (none)"
        context = "\n".join(f"- {k}: {v}" for k, v in self.t.items()) if self.t else "- (none)"
        return (
            f"Role: {self.r}\n\n"
            f"Core Task: {self.c1}\n\n"
            f"Context:\n{context}\n\n"
            f"Constraints:\n{constraints}\n\n"
            f"Output Format: {self.o_format}\n"
            f"Output Schema: {self.o_schema_ref or '(unspecified)'}"
        )


class PromptRegistryEntry(SchemaBase):
    """One stored RCTCO prompt package ready for execution."""

    prompt_id: str
    agent_id: str
    shot_id: str = ""
    artifact_refs: list[str] = Field(default_factory=list)
    rctco: RCTCOPrompt
    rendered_prompt: str = ""
    validation_status: str = "pending"


class PromptRegistry(SchemaBase):
    """Aggregate prompt registry for a project."""

    project_id: str
    entries: list[PromptRegistryEntry] = Field(default_factory=list)
