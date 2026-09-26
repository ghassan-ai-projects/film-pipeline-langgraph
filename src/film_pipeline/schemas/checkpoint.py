"""Checkpoint metadata, rollback records, and invalidation reports."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from film_pipeline.schemas.base import FilmPhase, MutableSchemaBase, SchemaBase


class RollbackOutcome(StrEnum):
    """Terminal state of one rollback execution."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class CheckpointState(MutableSchemaBase):
    """Persisted graph state for checkpoint resume."""

    state: dict[str, Any] = Field(default_factory=dict)


class CheckpointMetadata(SchemaBase):
    """One checkpoint created at a phase gate or before expensive work."""

    checkpoint_id: str
    project_id: str
    phase: FilmPhase
    created_at: datetime
    reason: str
    artifact_versions: dict[str, str] = Field(
        default_factory=dict,
        description="Map of artifact_type → version_id.",
    )
    graph_state_ref: str = ""
    approval_refs: list[str] = Field(default_factory=list)
    validation_refs: list[str] = Field(default_factory=list)
    budget_state_ref: str = ""
    git_commit: str = ""
    git_tag: str = ""
    git_branch: str = ""


class InvalidationReport(SchemaBase):
    """List of artifacts that will be invalidated by a rollback or change."""

    rollback_target: str
    will_revert: list[str] = Field(default_factory=list)
    will_invalidate: list[str] = Field(default_factory=list)
    requires_regeneration: bool = False
    requires_human_confirmation: bool = True
    notes: str = ""


class RollbackRecord(SchemaBase):
    """Audit record of one rollback execution."""

    rollback_id: str
    project_id: str
    target_checkpoint_id: str
    invalidation_report_ref: str
    performed_by: str
    created_at: datetime
    outcome: RollbackOutcome = Field(description="'success' | 'partial' | 'failed'.")


class BranchMetadata(MutableSchemaBase):
    """A creative branch for exploring alternatives."""

    branch_id: str
    project_id: str
    base_checkpoint_id: str
    purpose: str
    active: bool = False
