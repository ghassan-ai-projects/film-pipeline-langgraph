"""Frozen dataclasses and shared constants for the operator cockpit view models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from film_pipeline.app.services.models import (
    AuditEvent,
    DashboardSummary,
    GenerationWorkspace,
    OperatorComment,
    ProjectListItem,
    ReviewWorkspace,
    ValidationWorkspace,
)

GRAPH_PHASES: tuple[str, ...] = (
    "intake",
    "constitution",
    "development",
    "script",
    "visual_dev",
    "shot_bible",
    "gen_planning",
    "generation",
    "qc",
    "post",
    "delivery",
)


@dataclass(frozen=True)
class CockpitSnapshot:
    """Single refresh payload for the operator cockpit."""

    projects: list[ProjectListItem]
    dashboard: DashboardSummary | None
    review: ReviewWorkspace | None
    validation: ValidationWorkspace | None
    artifacts: list[dict[str, object]]
    assets: list[dict[str, object]]
    checkpoints: list[dict[str, str]]
    providers: list[dict[str, object]]
    audit_events: list[AuditEvent]
    comments: list[OperatorComment]
    matrix_rows: list[dict[str, object]]
    graph_rows: list[dict[str, object]]
    command_suggestions: list[dict[str, object]]
    command_options: CommandOptions
    generation: GenerationWorkspace | None = None
    # Readable review material for the current phase (built in the render
    # layer via builders_reading; typed as Any to avoid an import cycle).
    reading: Any = None
    prompts: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class CommandOptions:
    """Selectable IDs used by command palette and contextual forms."""

    project_ids: list[str] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)
    artifact_ids: list[str] = field(default_factory=list)
    scene_ids: list[str] = field(default_factory=list)
    validator_ids: list[str] = field(default_factory=list)
    provider_ids: list[str] = field(default_factory=list)
    project_kinds: list[str] = field(default_factory=lambda: ["production", "test", "all"])


@dataclass(frozen=True)
class CommandValidation:
    """Live validation result for one command palette value."""

    status: str
    message: str
    completion: str = ""


@dataclass(frozen=True)
class TargetSelection:
    """Selected cockpit object used for contextual inspection and comments."""

    target_type: str
    target_id: str
    phase: str = ""
    source: str = ""
    detail: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReaderView:
    """Readable artifact or scene view for the cockpit."""

    title: str
    subtitle: str
    outline: list[str]
    body: str
    metadata: dict[str, object]
    linked_comments: list[OperatorComment]
    linked_validation: list[dict[str, Any]]


@dataclass(frozen=True)
class MatrixImpact:
    """Impact summary for a selected smart-matrix row."""

    target_id: str
    target_type: str
    phase: str
    summary: str
    linked_comments: list[OperatorComment]
    linked_validation: list[dict[str, Any]]
    suggested_actions: list[str]


@dataclass(frozen=True)
class ValidationGroup:
    """Grouped validator failures for operator triage."""

    validator_id: str
    severity: str
    count: int
    targets: list[str]
    message: str
    suggested_action: str


@dataclass(frozen=True)
class ValidationFixSuggestion:
    """Actionable fix row derived from one validation issue."""

    target_id: str
    target_type: str
    severity: str
    validator_id: str
    message: str
    command: str
    rationale: str


@dataclass(frozen=True)
class PhaseDetail:
    """Drill-down view for one pipeline graph phase."""

    phase: str
    status: str
    summary: str
    artifacts: list[dict[str, object]]
    blockers: list[str]
    suggested_commands: list[str]


@dataclass(frozen=True)
class ReviewIssueTarget:
    """Review issue with inferred navigation target."""

    issue_id: str
    severity: str
    target_id: str
    target_type: str
    message: str
    command: str
