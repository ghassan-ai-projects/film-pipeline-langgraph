"""Continuity ledger — per-shot state tracking."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas.base import SchemaBase


class StateRecord(SchemaBase):
    """A snapshot of one state dimension at a shot boundary."""

    label: str
    description: str
    refs: list[str] = Field(default_factory=list, description="Asset or artifact ids.")


class ContinuityLedgerEntry(SchemaBase):
    """Per-shot continuity state in/out plus risk notes."""

    shot_id: str
    state_in: list[StateRecord] = Field(default_factory=list)
    action: str = Field(description="What happens during this shot.")
    state_out: list[StateRecord] = Field(default_factory=list)
    character_state: dict[str, str] = Field(default_factory=dict)
    prop_state: dict[str, str] = Field(default_factory=dict)
    wardrobe_state: dict[str, str] = Field(default_factory=dict)
    environment_state: dict[str, str] = Field(default_factory=dict)
    lighting_state: dict[str, str] = Field(default_factory=dict)
    story_threads: list[str] = Field(default_factory=list)
    continuity_risks: list[str] = Field(default_factory=list)
    next_required_anchors: list[str] = Field(default_factory=list)


class ContinuityLedger(SchemaBase):
    """Aggregate continuity ledger."""

    project_id: str
    entries: list[ContinuityLedgerEntry] = Field(default_factory=list)
