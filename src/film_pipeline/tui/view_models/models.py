"""Frozen dataclasses and shared constants for the studio view models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from film_pipeline.app.services.models import (
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
class StudioSnapshot:
    """Single refresh payload for the studio screens."""

    projects: list[ProjectListItem]
    dashboard: DashboardSummary | None = None
    review: ReviewWorkspace | None = None
    validation: ValidationWorkspace | None = None
    artifacts: list[dict[str, object]] = field(default_factory=list)
    assets: list[dict[str, object]] = field(default_factory=list)
    providers: list[dict[str, object]] = field(default_factory=list)
    comments: list[OperatorComment] = field(default_factory=list)
    generation: GenerationWorkspace | None = None
    prompts: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class TargetSelection:
    """Selected studio object used for contextual inspection and comments."""

    target_type: str
    target_id: str
    phase: str = ""
    source: str = ""
    detail: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReaderView:
    """Readable artifact or scene view for the reader pane."""

    title: str
    subtitle: str
    outline: list[str]
    body: str
    metadata: dict[str, object]
    linked_comments: list[OperatorComment]
    linked_validation: list[dict[str, Any]]
