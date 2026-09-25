"""Knowledge base item metadata, context packets, and conflicts."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from film_pipeline.schemas.base import (
    KbAuthority,
    MutableSchemaBase,
    SchemaBase,
)


class KBItemMetadata(SchemaBase):
    """Metadata attached to every curated KB item."""

    id: str = Field(description="Stable id, e.g. 'kb.policy.prompt.rctco.v1'.")
    title: str
    authority: KbAuthority
    status: str = Field(default="active", description="'active' | 'deprecated' | 'draft'.")
    version: int = 1
    domains: list[str] = Field(default_factory=list)
    applies_to_phases: list[str] = Field(default_factory=list)
    applies_to_agents: list[str] = Field(default_factory=list)
    modalities: list[str] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)
    conflicts_with: list[str] = Field(default_factory=list)
    summary: str
    last_reviewed: datetime | None = None


class KBExcludedRef(SchemaBase):
    """One KB item deliberately excluded from a context packet."""

    ref: str
    reason: str


class KBContextPacket(SchemaBase):
    """The governed slice of the KB delivered to one agent for one task."""

    kb_context_id: str
    project_id: str
    phase: str
    agent_id: str
    task: str
    authority_policy_refs: list[str] = Field(default_factory=list)
    playbook_refs: list[str] = Field(default_factory=list)
    case_study_refs: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    excluded_refs: list[KBExcludedRef] = Field(default_factory=list)
    payload: dict[str, str] = Field(
        default_factory=dict,
        description="Optional resolved body content for each ref.",
    )


class KBConflictRecord(MutableSchemaBase):
    """A detected KB conflict awaiting human or curator resolution."""

    conflict_id: str
    items: list[str] = Field(description="KB item ids in conflict.")
    description: str
    resolution: str | None = None
    resolved: bool = False
    detected_at: datetime
