"""Base validator — standard lifecycle: prepare → validate → score → report."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from film_pipeline.schemas._base import ValidationStatus
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
)
from film_pipeline.schemas.validation import ValidationIssue, ValidationReport
from film_pipeline.validation.thresholds import score_to_status


class BaseValidator(ABC):
    """Standard validator lifecycle contract.

    Every validator implements:
    - validate(artifact, context) → raw result dict
    - score(raw) → float
    - report(artifact_refs, score, issues) → ValidationReport
    """

    entry: ValidatorRegistryEntry

    def __init__(self, entry: ValidatorRegistryEntry) -> None:
        self.entry = entry

    @abstractmethod
    def validate(
        self,
        artifact: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the validation and return structured findings."""
        ...

    @abstractmethod
    def extract_score(self, raw: dict[str, Any]) -> float:
        """Extract a 0-100 score from the raw validation output."""
        ...

    @abstractmethod
    def extract_issues(self, raw: dict[str, Any]) -> list[ValidationIssue]:
        """Extract issues (blocking + warnings) from raw output."""
        ...

    def run(
        self,
        artifact: dict[str, Any],
        artifact_refs: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ValidationReport:
        """Full lifecycle: validate → score → classify → report."""
        raw = self.validate(artifact, context)
        score = self.extract_score(raw)
        issues = self.extract_issues(raw)

        blocking = [i for i in issues if i.severity == "blocking"]
        warnings = [i for i in issues if i.severity != "blocking"]
        status = score_to_status(score, self.entry.thresholds)

        return ValidationReport(
            validation_id=f"validation:{self.entry.validator_id}:{uuid4().hex[:8]}",
            validator_id=self.entry.validator_id,
            scope=self.entry.scope,
            modalities=list(self.entry.modalities),
            artifact_refs=artifact_refs or [],
            score=score,
            status=status,
            blocking_issues=blocking,
            warnings=warnings,
            recommended_actions=_recommended_actions(status, blocking),
            requires_human_review=status
            in (
                ValidationStatus.NEEDS_REVISION,
                ValidationStatus.BLOCKED,
            ),
        )


def _recommended_actions(
    status: ValidationStatus,
    blocking: list[ValidationIssue],
) -> list[str]:
    if status == ValidationStatus.PASS:
        return []
    if status == ValidationStatus.PASS_WITH_NOTES:
        return ["Review warnings before proceeding."]
    if blocking:
        return [f"Resolve: {i.code} — {i.message}" for i in blocking]
    return ["Review and revise before resubmitting."]
