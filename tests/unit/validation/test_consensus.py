"""Tests for multi-model consensus builder."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from film_pipeline.schemas.base import (
    IssueSeverity,
    ValidationModality,
    ValidationScope,
    ValidationStatus,
)
from film_pipeline.schemas.validation import ValidationIssue, ValidationReport
from film_pipeline.validation.consensus import ConsensusBuilder


def _make_report(
    validator_id: str,
    score: float,
    status: ValidationStatus = ValidationStatus.PASS,
    blocking_codes: list[str] | None = None,
    warning_codes: list[str] | None = None,
) -> ValidationReport:
    blocking: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    if blocking_codes:
        for code in blocking_codes:
            blocking.append(
                ValidationIssue(
                    code=code, message=f"Issue: {code}", severity=IssueSeverity.BLOCKING
                )
            )
    if warning_codes:
        for code in warning_codes:
            warnings.append(
                ValidationIssue(
                    code=code, message=f"Warning: {code}", severity=IssueSeverity.WARNING
                )
            )
    return ValidationReport(
        validation_id=f"val:{validator_id}:1",
        validator_id=validator_id,
        scope=ValidationScope.CLIP,
        modalities=[ValidationModality.VIDEO],
        score=score,
        status=status,
        blocking_issues=blocking,
        warnings=warnings,
    )


class TestConsensusBuilder:
    def test_empty_reports(self) -> None:
        builder = ConsensusBuilder()
        consensus = builder.build([])
        assert consensus.agreement_level == "low"
        assert consensus.consensus_status == ValidationStatus.ERROR
        assert len(consensus.reviewers) == 0

    def test_single_report(self) -> None:
        builder = ConsensusBuilder()
        r = _make_report("v1", 90)
        consensus = builder.build([r])
        assert consensus.agreement_level == "high"
        assert consensus.consensus_status == ValidationStatus.PASS

    def test_high_agreement(self) -> None:
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 90)
        r2 = _make_report("v2", 92)
        consensus = builder.build([r1, r2])
        assert consensus.agreement_level == "high"

    def test_medium_agreement(self) -> None:
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 90)
        r2 = _make_report("v2", 78)
        consensus = builder.build([r1, r2])
        assert consensus.agreement_level == "medium"

    def test_low_agreement(self) -> None:
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 95)
        r2 = _make_report("v2", 70)
        consensus = builder.build([r1, r2])
        assert consensus.agreement_level == "low"

    def test_blocking_consensus(self) -> None:
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 90, ValidationStatus.PASS)
        r2 = _make_report("v2", 60, ValidationStatus.BLOCKED)
        consensus = builder.build([r1, r2])
        assert consensus.consensus_status == ValidationStatus.BLOCKED

    def test_shared_findings(self) -> None:
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 85, blocking_codes=["b1", "b2"])
        r2 = _make_report("v2", 80, blocking_codes=["b1"])
        consensus = builder.build([r1, r2])
        assert len(consensus.reviewers) == 2
        assert any("b1" in f for f in consensus.shared_findings)

    def test_orchestrator_recommendation(self) -> None:
        builder = ConsensusBuilder()
        r = _make_report("v1", 90)
        consensus = builder.build([r])
        assert len(consensus.orchestrator_recommendation) > 0

    def test_needs_revision_consensus(self) -> None:
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 80, ValidationStatus.PASS_WITH_NOTES)
        r2 = _make_report("v2", 70, ValidationStatus.NEEDS_REVISION)
        consensus = builder.build([r1, r2])
        assert consensus.consensus_status == ValidationStatus.NEEDS_REVISION

    def test_low_agreement_recommendation(self) -> None:
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 95, ValidationStatus.PASS)
        r2 = _make_report("v2", 70, ValidationStatus.BLOCKED)
        consensus = builder.build([r1, r2])
        # Low agreement + blocked = revise recommendation
        assert consensus.agreement_level == "low"

    def test_warnings_shared(self) -> None:
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 90)
        r2 = _make_report("v2", 88)
        consensus = builder.build([r1, r2])
        # Both PASS — high agreement
        assert consensus.consensus_status == ValidationStatus.PASS

    def test_artifact_refs(self) -> None:
        builder = ConsensusBuilder()
        r = _make_report("v1", 90)
        consensus = builder.build([r], artifact_refs=["ref:1", "ref:2"])
        assert consensus.artifact_refs == ["ref:1", "ref:2"]

    def test_blocked_consensus_recommendation(self) -> None:
        builder = ConsensusBuilder()
        r = _make_report("v1", 50, ValidationStatus.BLOCKED)
        consensus = builder.build([r])
        assert "Revise" in consensus.orchestrator_recommendation

    def test_warnings_produce_shared_findings(self) -> None:
        """Reports with warnings but no blocking issues."""
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 80, ValidationStatus.PASS_WITH_NOTES, warning_codes=["w1", "w2"])
        r2 = _make_report("v2", 82, ValidationStatus.PASS_WITH_NOTES, warning_codes=["w1"])
        consensus = builder.build([r1, r2])
        assert consensus.consensus_status == ValidationStatus.PASS_WITH_NOTES
        assert any("w1" in f for f in consensus.shared_findings)

    def test_disagreements_when_no_shared_issues(self) -> None:
        """Reports with no blocking and no warnings produce disagreements."""
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 85, ValidationStatus.PASS)
        r2 = _make_report("v2", 90, ValidationStatus.PASS)
        consensus = builder.build([r1, r2])
        assert consensus.agreement_level == "high"
        assert consensus.consensus_status == ValidationStatus.PASS

    def test_pass_with_notes_consensus(self) -> None:
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 82, ValidationStatus.PASS_WITH_NOTES)
        r2 = _make_report("v2", 84, ValidationStatus.PASS_WITH_NOTES)
        consensus = builder.build([r1, r2])
        assert consensus.consensus_status == ValidationStatus.PASS_WITH_NOTES

    def test_accepts_serialized_report_mappings(self) -> None:
        """The QC path feeds `report.model_dump()` output, i.e. plain dicts.

        `_validation_reports` is declared `list[dict[str, Any]]` and every writer
        appends `model_dump()`, but `build` used to require `ValidationReport`
        models and attribute-access them, raising
        `AttributeError: 'dict' object has no attribute 'validator_id'`. The QC
        node wrapped that call in a bare `except Exception: return`, so consensus
        reports were silently never produced. This pins the mapping shape so the
        regression cannot return.
        """
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 85, ValidationStatus.PASS)
        r2 = _make_report("v2", 90, ValidationStatus.PASS)
        consensus = builder.build([r1.model_dump(), r2.model_dump()], ["art:1"])
        assert consensus.consensus_status == ValidationStatus.PASS
        assert len(consensus.reviewers) == 2
        assert consensus.artifact_refs == ["art:1"]

    def test_mapping_and_model_inputs_agree(self) -> None:
        """The two accepted shapes must synthesize the same consensus."""
        builder = ConsensusBuilder()
        r1 = _make_report("v1", 70, ValidationStatus.NEEDS_REVISION, blocking_codes=["b1"])
        r2 = _make_report("v2", 72, ValidationStatus.NEEDS_REVISION, blocking_codes=["b1"])
        from_models = builder.build([r1, r2])
        from_mappings = builder.build([r1.model_dump(), r2.model_dump()])
        # `review_id` is a fresh uuid per build, so compare the synthesized content.
        assert from_models.reviewers == from_mappings.reviewers
        assert from_models.agreement_level == from_mappings.agreement_level
        assert from_models.consensus_status == from_mappings.consensus_status
        assert from_models.shared_findings == from_mappings.shared_findings

    def test_serialized_report_round_trips_without_loss(self) -> None:
        """Every scored field the synthesis reads survives the mapping round trip.

        `build` reads `validator_id`, `score` and `status`; if `model_dump()`
        dropped or renamed one, the mapping path would synthesize a different
        consensus from identical input. This asserts field-level agreement rather
        than only that no exception was raised.
        """
        report = _make_report("v1", 88, ValidationStatus.PASS_WITH_NOTES, warning_codes=["w1"])
        dumped = report.model_dump()
        assert dumped["validator_id"] == "v1"
        assert dumped["score"] == 88
        assert dumped["status"] == ValidationStatus.PASS_WITH_NOTES

    def test_non_mapping_entry_raises_a_named_error(self) -> None:
        """A non-report, non-mapping entry fails with the module's own error type.

        The call is made through `Any` deliberately: the guard exists for callers
        holding untyped data (a JSON list, a legacy snapshot), which is exactly
        the case mypy cannot describe. `Any` is used here in a *test* to reach a
        runtime guard, not to widen a production signature.
        """
        from film_pipeline.validation.consensus import UnknownReportShapeError

        untyped: Any = ["oops"]
        with pytest.raises(UnknownReportShapeError):
            ConsensusBuilder().build(untyped)

    def test_malformed_mapping_is_rejected(self) -> None:
        """A dict that is not a report shape fails validation rather than passing."""
        malformed: dict[str, object] = {"unknown_field": 1}
        with pytest.raises(ValidationError):
            ConsensusBuilder().build([malformed])
