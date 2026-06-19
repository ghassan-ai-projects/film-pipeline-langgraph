"""Approval records, revision requests, and review packages."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from film_pipeline.schemas._base import FilmPhase, SchemaBase

ApprovalAction = Literal["approve", "request_revision", "reject", "escalate"]


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
