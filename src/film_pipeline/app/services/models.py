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
class ArtifactDetail:
    """Artifact detail shown by the TUI."""

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
class AuditEvent:
    """Audit feed item."""

    timestamp: str
    actor: str
    action: str
    target: str
    summary: str
