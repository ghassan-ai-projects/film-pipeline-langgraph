"""Issue records — track blockers, drift, and warnings across the studio."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from film_pipeline.schemas.base import IssueSeverity, SchemaBase


class IssueRecord(SchemaBase):
    """One issue that may block phase advancement or require human attention."""

    issue_id: str
    project_id: str
    phase: str
    severity: IssueSeverity
    code: str = Field(description="Stable machine-readable code, e.g. 'IDENTITY_DRIFT'.")
    message: str
    related_artifact_refs: list[str] = Field(default_factory=list)
    related_validator_ids: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    resolved: bool = False
    resolution_note: str = ""
    created_at: datetime
    resolved_at: datetime | None = None
