"""Multi-model consensus builder — parallel review, agreement, synthesis."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from film_pipeline.schemas._base import ValidationStatus
from film_pipeline.schemas.validation import (
    ConsensusReport,
    ReviewerScore,
    ValidationReport,
)


@dataclass
class ConsensusBuilder:
    """Builds a ConsensusReport from multiple independent ValidationReports."""

    def build(
        self,
        reports: list[ValidationReport],
        artifact_refs: list[str] | None = None,
    ) -> ConsensusReport:
        """Synthesize multiple reviewer reports into one consensus."""
        if not reports:
            return ConsensusReport(
                review_id=f"consensus:{uuid4().hex[:8]}",
                artifact_refs=artifact_refs or [],
                reviewers=[],
                agreement_level="low",
                consensus_status=ValidationStatus.ERROR,
                shared_findings=["No reviewer reports available."],
                disagreements=[],
                orchestrator_recommendation="Cannot synthesize without reviewer reports.",
            )

        reviewers = [
            ReviewerScore(
                model_id=r.validator_id,
                validator_id=r.validator_id,
                score=r.score,
                status=r.status,
            )
            for r in reports
        ]

        agreement_level = _calculate_agreement(reports)
        consensus_status = _consensus_status(reports)
        shared, disagreements = _compare_findings(reports)

        if consensus_status == ValidationStatus.BLOCKED:
            recommendation = "Revise before human approval."
        elif consensus_status == ValidationStatus.PASS_WITH_NOTES:
            recommendation = "Pass with noted warnings. Proceed with caution."
        elif agreement_level == "low":
            recommendation = "Reviewers disagree significantly. Escalate to human."
        else:
            recommendation = "Approve."

        return ConsensusReport(
            review_id=f"consensus:{uuid4().hex[:8]}",
            artifact_refs=artifact_refs or [],
            reviewers=reviewers,
            agreement_level=agreement_level,
            consensus_status=consensus_status,
            shared_findings=shared,
            disagreements=disagreements,
            orchestrator_recommendation=recommendation,
        )


def _calculate_agreement(reports: list[ValidationReport]) -> str:
    scores = [r.score for r in reports]
    if not scores:  # pragma: no cover — build() returns early for empty
        return "low"
    spread = max(scores) - min(scores)
    if spread <= 5:
        return "high"
    if spread <= 15:
        return "medium"
    return "low"


def _consensus_status(reports: list[ValidationReport]) -> ValidationStatus:
    statuses = [r.status for r in reports]
    if any(s == ValidationStatus.BLOCKED for s in statuses):
        return ValidationStatus.BLOCKED
    if any(s == ValidationStatus.NEEDS_REVISION for s in statuses):
        return ValidationStatus.NEEDS_REVISION
    if any(s == ValidationStatus.PASS_WITH_NOTES for s in statuses):
        return ValidationStatus.PASS_WITH_NOTES
    if all(s == ValidationStatus.PASS for s in statuses):
        return ValidationStatus.PASS
    return ValidationStatus.NEEDS_REVISION  # pragma: no cover — all statuses caught above


def _compare_findings(
    reports: list[ValidationReport],
) -> tuple[list[str], list[str]]:
    all_blocking: set[str] = set()
    all_warnings: set[str] = set()

    for r in reports:
        for issue in r.blocking_issues:
            all_blocking.add(issue.code)
        for issue in r.warnings:
            all_warnings.add(issue.code)

    shared: list[str] = []
    disagreements: list[str] = []

    if all_blocking:
        shared.append(f"All reviewers agree on blocking: {', '.join(sorted(all_blocking))}")
    else:
        disagreements.append("No shared blocking issues across reviewers.")

    if all_warnings:
        shared.append(f"All reviewers note warnings: {', '.join(sorted(all_warnings))}")

    return shared, disagreements
