"""Typed view models for operator use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProjectCreateRequest:
    """Input required to create a project and optionally start intake."""

    project_id: str
    title: str
    slug: str = ""
    idea: str = ""
    runtime_mode: str = "mock"
    workflow_mode: str = "manual"
    project_kind: str = "production"
    target_runtime_seconds: int = 0  # 0 = not specified; intake will estimate
    film_type_profile: str = ""
    quality_profile: str = ""
    provider_profile: str = ""
    review_profile: str = ""
    auto_approve_profile: str = ""
    generation_policy: str = "generate"


@dataclass(frozen=True)
class ProjectListItem:
    """Project rail entry."""

    project_id: str
    title: str
    slug: str
    current_phase: str
    status: str
    has_blockers: bool
    awaiting_review: bool
    last_updated_at: str = ""
    project_kind: str = "production"
    project_root: str = ""


@dataclass(frozen=True)
class DashboardSummary:
    """Operator dashboard view model."""

    project_id: str
    title: str
    slug: str
    current_phase: str
    runtime_mode: str
    workflow_mode: str
    status: str
    next_action: str
    route_reason: str
    idea: str = ""
    eligible_actions: list[str] = field(default_factory=list)
    blocked_actions: list[dict[str, str]] = field(default_factory=list)
    pending_revisions: list[dict[str, Any]] = field(default_factory=list)
    candidate_refs: dict[str, Any] = field(default_factory=dict)
    approved_refs: dict[str, Any] = field(default_factory=dict)
    budget_snapshot: dict[str, Any] = field(default_factory=dict)
    provider_blocked: list[str] = field(default_factory=list)
    issue_count: int = 0
    artifact_count: int = 0
    checkpoint_count: int = 0
    has_blockers: bool = False
    stalled_phase: str = ""
    profile_stack: dict[str, str] = field(default_factory=dict)
    generation_policy: str = "generate"


@dataclass(frozen=True)
class ReviewWorkspace:
    """Current phase review workspace."""

    project_id: str
    phase: str
    recommendation: str
    candidate_artifacts: list[dict[str, Any]] = field(default_factory=list)
    open_issues: list[str] = field(default_factory=list)
    available_actions: list[str] = field(default_factory=list)
    blocked_actions: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ValidationWorkspace:
    """Validation report and issue summary for a project."""

    project_id: str
    phase: str
    source: str
    reports: list[dict[str, Any]] = field(default_factory=list)
    blocking_issues: list[dict[str, Any]] = field(default_factory=list)
    non_blocking_issues: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class GenerationWorkspace:
    """Generation batch status for a project."""

    project_id: str
    phase: str
    provider: str
    model: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    planned: int = 0
    submitted: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    next_step: str = ""


@dataclass(frozen=True)
class OperatorCommentRequest:
    """Operator annotation attached to a concrete project target."""

    target_type: str
    target_id: str
    body: str
    phase: str = ""
    source: str = "operator"


@dataclass(frozen=True)
class OperatorComment:
    """Stored operator annotation."""

    comment_id: str
    project_id: str
    target_type: str
    target_id: str
    body: str
    phase: str
    source: str
    created_at: str
    resolved: bool = False


@dataclass(frozen=True)
class ArtifactDetail:
    """Artifact detail shown by operator surfaces."""

    artifact_id: str
    artifact_type: str
    phase: str
    version: int
    status: str
    body: dict[str, Any]


@dataclass(frozen=True)
class MutationResult:
    """Result of an operator mutation."""

    ok: bool
    project_id: str
    current_phase: str
    message: str = ""


@dataclass(frozen=True)
class CheckpointRollbackResult:
    """Completed project rollback and persisted bookkeeping references."""

    rollback_target: str
    phase: str
    reason: str
    invalidation_report_ref: str
    rollback_record_ref: str


@dataclass(frozen=True)
class ArtifactRollbackResult:
    """Completed artifact restore and persisted bookkeeping references."""

    artifact_id: str
    restored_from: str
    git_commit: str
    invalidation_report_ref: str
    rollback_record_ref: str


@dataclass(frozen=True)
class AuditEvent:
    """Audit feed item."""

    timestamp: str
    actor: str
    action: str
    target: str
    summary: str
