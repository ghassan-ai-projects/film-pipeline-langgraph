"""Validation report, ledger, and consensus report."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from film_pipeline.schemas._base import (
    IssueSeverity,
    SchemaBase,
    ValidationModality,
    ValidationScope,
    ValidationStatus,
)

AgreementLevel = Literal["high", "medium", "low"]


class ValidationIssue(SchemaBase):
    """One issue surfaced by a validator."""

    code: str
    message: str
    severity: IssueSeverity = Field(description="'info' | 'warning' | 'blocking'.")
    suggestion: str = ""
    affected_entity: str = ""
    affected_field: str = ""
    affected_shot: str = ""


class ValidationReport(SchemaBase):
    """One validator's structured output."""

    validation_id: str
    validator_id: str
    scope: ValidationScope
    modalities: list[ValidationModality]
    artifact_refs: list[str] = Field(default_factory=list)
    score: float = Field(ge=0, le=100)
    status: ValidationStatus
    blocking_issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    requires_human_review: bool = False


class ReviewerScore(SchemaBase):
    """One reviewer's score in a multi-model consensus."""

    model_id: str
    validator_id: str
    score: float = Field(ge=0, le=100)
    status: ValidationStatus


class ConsensusReport(SchemaBase):
    """Aggregate of multiple reviewer reports on the same artifact."""

    review_id: str
    artifact_refs: list[str] = Field(default_factory=list)
    reviewers: list[ReviewerScore] = Field(default_factory=list)
    agreement_level: AgreementLevel = Field(description="'high' | 'medium' | 'low'.")
    consensus_status: ValidationStatus
    shared_findings: list[str] = Field(default_factory=list)
    disagreements: list[str] = Field(default_factory=list)
    orchestrator_recommendation: str = ""


class ValidationLedgerEntry(SchemaBase):
    """Stored validation record persisted to the artifact store."""

    report: ValidationReport
    project_id: str
    phase: str
    consensus: ConsensusReport | None = None
