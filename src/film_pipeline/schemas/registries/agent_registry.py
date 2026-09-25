"""Agent registry entry schema."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas.base import AgentFamily, AgentRole, SchemaBase


class AgentRegistryEntry(SchemaBase):
    """Discoverable record for an agent registration.

    The orchestrator selects agents by capability using these records.
    """

    agent_id: str
    family: AgentFamily
    role: AgentRole
    capabilities: list[str] = Field(default_factory=list)
    input_artifacts: list[str] = Field(default_factory=list)
    output_artifacts: list[str] = Field(default_factory=list)
    allowed_kb_domains: list[str] = Field(default_factory=list)
    blocked_kb_domains: list[str] = Field(default_factory=list)
    prompt_framework: str = "RCTCO"
    default_model_profile: str = "creative_writer"
    reviewed_by: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    enabled: bool = True
