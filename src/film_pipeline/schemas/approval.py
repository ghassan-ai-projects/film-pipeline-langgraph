"""Approval records, revision requests, review packages, and profile changes."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from film_pipeline.schemas.base import FilmPhase, SchemaBase

ApprovalAction = Literal["approve", "request_revision", "reject", "escalate"]
ProfileChangeStatus = Literal["pending", "approved", "rejected", "superseded"]


class ApprovalRecord(SchemaBase):
    """One approval by a human (or mock human) for a phase or artifact."""

    approval_id: str
    project_id: str
    phase: FilmPhase
    artifact_refs: list[str] = Field(default_factory=list)
    action: ApprovalAction
    note: str = ""
    approver_id: str
    actor_type: str = Field(default="human", description="'human' | 'mock_human'.")
    created_at: datetime


class RevisionRequest(SchemaBase):
    """A request to revise an artifact, linked to old and new versions."""

    revision_id: str
    project_id: str
    phase: FilmPhase
    artifact_refs: list[str] = Field(default_factory=list)
    requester_id: str
    note: str
    from_version: int = Field(ge=1)
    to_version: int | None = None
    created_at: datetime


class ReviewPackage(SchemaBase):
    """The package a human reviewer sees at an approval gate."""

    review_package_id: str
    project_id: str
    phase: FilmPhase
    type: str = Field(description="e.g. 'config_review', 'treatment_review', 'final_cut_review'.")
    summary: str
    artifacts: list[str] = Field(default_factory=list)
    diff_from_approved: dict[str, list[str]] = Field(
        default_factory=lambda: dict[str, list[str]](added=[], changed=[], removed=[]),
    )
    validation_results: list[str] = Field(default_factory=list)
    open_issues: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    cost_impact: dict[str, str] = Field(default_factory=dict)
    orchestrator_recommendation: str
    available_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)


class ProfileChangeProposal(SchemaBase):
    """A proposed mid-project change to the profile stack."""

    proposal_id: str
    project_id: str
    proposed_by: str
    reason: str
    previous_profile_stack: dict[str, str] = Field(default_factory=dict)
    proposed_profile_stack: dict[str, str] = Field(default_factory=dict)
    previous_profile_version: int = Field(default=0, ge=0)
    projected_config_diff: dict[str, Any] = Field(default_factory=dict)
    status: ProfileChangeStatus = "pending"
    created_at: datetime


class ProfileChangeApproval(SchemaBase):
    """Human approval of a profile-change proposal."""

    approval_id: str
    proposal_id: str
    project_id: str
    approved_by: str
    note: str = ""
    profile_version: int = Field(ge=1)
    new_profile_stack: dict[str, str] = Field(default_factory=dict)
    new_resolved_config_ref: str = ""
    invalidation_report_ref: str = ""
    created_at: datetime
