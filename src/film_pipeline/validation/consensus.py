"""Multi-model consensus builder — parallel review, agreement, synthesis."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from film_pipeline.schemas.base import ValidationStatus
from film_pipeline.schemas.validation import (
    AgreementLevel,
    ConsensusReport,
    ReviewerScore,
    ValidationReport,
)


@dataclass
class ConsensusBuilder:
    """Builds a ConsensusReport from multiple independent ValidationReports."""

    def build(
        self,
        reports: list[ValidationReport] | list[dict[str, object]],
        artifact_refs: list[str] | None = None,
    ) -> ConsensusReport:
        """Synthesize multiple reviewer reports into one consensus.

        ``reports`` accepts either the models or their serialized mappings,
        because the two real callers differ: ``_validation_reports`` in graph
        state holds ``report.model_dump()`` output (every writer and every other
        reader in the tree treats it as dicts), while direct callers pass models.
        Coercing here rather than narrowing the parameter keeps the synthesis
        logic below object-typed; taking the dicts on trust and attribute-accessing
        them raised ``AttributeError: 'dict' object has no attribute
        'validator_id'`` on the QC path, which a bare ``except Exception`` then
        swallowed silently.
        """
        reports = [_as_report(report) for report in reports]
        if not reports:
            return ConsensusReport(
                review_id=_new_review_id(),
                artifact_refs=artifact_refs or [],
                reviewers=[],
                agreement_level="low",
                consensus_status=ValidationStatus.ERROR,
                shared_findings=["No reviewer reports available."],
                disagreements=[],
                orchestrator_recommendation="Cannot synthesize without reviewer reports.",
            )

        reviewers = _reviewer_scores(reports)

        agreement_level = _calculate_agreement(reports)
        consensus_status = _consensus_status(reports)
        shared, disagreements = _compare_findings(reports)
        recommendation = _orchestrator_recommendation(consensus_status, agreement_level)

        return ConsensusReport(
            review_id=_new_review_id(),
            artifact_refs=artifact_refs or [],
            reviewers=reviewers,
            agreement_level=agreement_level,
            consensus_status=consensus_status,
            shared_findings=shared,
            disagreements=disagreements,
            orchestrator_recommendation=recommendation,
        )


def _new_review_id() -> str:
    """Fresh identifier for one synthesized consensus report."""
    return f"consensus:{uuid4().hex[:8]}"


class UnknownReportShapeError(ValueError):
    """Raised when a consensus input is neither a report nor a report mapping."""


def _as_report(report: ValidationReport | dict[str, object]) -> ValidationReport:
    """Coerce one consensus input to a :class:`ValidationReport`.

    A mapping is re-validated through the model rather than read by key, so a
    malformed entry fails loudly here instead of silently contributing a wrong
    score. A non-mapping that is not already a report is a programming error and
    is reported as one.
    """
    if isinstance(report, ValidationReport):
        return report
    if isinstance(report, dict):
        return ValidationReport.model_validate(report)
    raise UnknownReportShapeError(
        "consensus inputs must be ValidationReport or its mapping form, got "
        f"{type(report).__name__}"
    )


def _reviewer_scores(reports: list[ValidationReport]) -> list[ReviewerScore]:
    """Project each reviewer report onto its consensus reviewer score."""
    return [
        ReviewerScore(
            model_id=r.validator_id,
            validator_id=r.validator_id,
            score=r.score,
            status=r.status,
        )
        for r in reports
    ]


def _calculate_agreement(reports: list[ValidationReport]) -> AgreementLevel:
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
    return ValidationStatus.NEEDS_REVISION  # pragma: no cover — ERROR-status reviews land here


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


def _orchestrator_recommendation(
    consensus_status: ValidationStatus,
    agreement_level: str,
) -> str:
    """Human-facing next step implied by the consensus outcome."""
    if consensus_status == ValidationStatus.BLOCKED:
        return "Revise before human approval."
    if consensus_status == ValidationStatus.PASS_WITH_NOTES:
        return "Pass with noted warnings. Proceed with caution."
    if agreement_level == "low":
        return "Reviewers disagree significantly. Escalate to human."
    return "Approve."
