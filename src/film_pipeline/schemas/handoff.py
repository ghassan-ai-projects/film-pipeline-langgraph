"""Agent handoff and routing decision records."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas.base import AgentFamily, AgentRole, SchemaBase


class AgentHandoff(SchemaBase):
    """A handoff from one agent to another."""

    handoff_id: str
    from_agent: str
    to_agent: str
    project_id: str
    input_artifact_refs: list[str] = Field(default_factory=list)
    kb_context_ref: str = ""
    task: str
    expected_output_schema: str
    validation_required: list[str] = Field(default_factory=list)


class RoutingDecision(SchemaBase):
    """An explainable decision made by the orchestrator."""

    routing_decision_id: str
    selected_agent: str
    reason: str
    input_refs: list[str] = Field(default_factory=list)
    expected_output: str = ""
    requires_human_review: bool = False
    candidate_agents: list[str] = Field(
        default_factory=list,
        description="Other agents considered before selection.",
    )


class AgentRegistration(SchemaBase):
    """The orchestrator's view of an agent's capabilities and contracts."""

    agent_id: str
    family: AgentFamily
    role: AgentRole
    capabilities: list[str] = Field(default_factory=list)
    input_artifacts: list[str] = Field(default_factory=list)
    output_artifacts: list[str] = Field(default_factory=list)
    produces: str = Field(
        default="",
        description=(
            "The authoritative key this agent's ``execute()`` returns its primary "
            "artifact under. Consumers read the agent's result through this key "
            "instead of hardcoding it. ``output_artifacts`` is the free-form "
            "capability vocabulary and is not what the result dict is keyed by."
        ),
    )
    allowed_kb_domains: list[str] = Field(default_factory=list)
    blocked_kb_domains: list[str] = Field(default_factory=list)
    prompt_framework: str = "RCTCO"
    default_model_profile: str = "creative_writer"
    reviewed_by: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
