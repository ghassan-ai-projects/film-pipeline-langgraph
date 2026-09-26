"""Tests for validation-status-driven routing in compute_actions."""

from __future__ import annotations

from film_pipeline.orchestration.router import compute_actions
from film_pipeline.schemas.base import ValidationModality, ValidationScope, ValidationStatus
from film_pipeline.schemas.validation import ValidationReport


def _report(status: ValidationStatus, score: float) -> ValidationReport:
    return ValidationReport(
        validation_id="val:test:1",
        validator_id="test-validator",
        scope=ValidationScope.ARTIFACT,
        modalities=[ValidationModality.TEXT],
        score=score,
        status=status,
    )


def _state_with_reports(
    reports: list[ValidationReport], *, approved: bool = False
) -> dict[str, object]:
    return {
        "current_phase": "qc",
        "approved": approved,
        "human_approval_required": False,
        "issues": [],
        "_validation_reports": [r.model_dump(mode="json") for r in reports],
    }


def test_blocked_status_routes_to_handle_blockers() -> None:
    state = _state_with_reports([_report(ValidationStatus.BLOCKED, 50)])
    result = compute_actions(state)
    assert result.next_action == "handle_blockers"
    assert "repair" in result.eligible


def test_needs_revision_routes_to_revise() -> None:
    state = _state_with_reports([_report(ValidationStatus.NEEDS_REVISION, 70)])
    result = compute_actions(state)
    assert result.next_action == "revise"
    assert "revise" in result.eligible


def test_pass_with_notes_adds_non_blocking_note() -> None:
    state = _state_with_reports([_report(ValidationStatus.PASS_WITH_NOTES, 80)], approved=True)
    result = compute_actions(state)
    assert result.next_action == "advance_to_post"
    assert any("passed with notes" in b["reason"] for b in result.blocked)


def test_pass_status_does_not_block() -> None:
    state = _state_with_reports([_report(ValidationStatus.PASS, 90)], approved=True)
    result = compute_actions(state)
    assert result.next_action == "advance_to_post"
    assert not any(b["action"] == "approve_phase" for b in result.blocked)


def test_consensus_report_dict_takes_precedence() -> None:
    state: dict[str, object] = {
        "current_phase": "qc",
        "approved": False,
        "human_approval_required": False,
        "issues": [],
        "_validation_reports": [
            ValidationReport(
                validation_id="val:test:1",
                validator_id="test-validator",
                scope=ValidationScope.ARTIFACT,
                modalities=[ValidationModality.TEXT],
                score=90,
                status=ValidationStatus.PASS,
            ).model_dump(mode="json")
        ],
        "consensus_report": {
            "consensus_status": ValidationStatus.BLOCKED.value,
            "reviewers": [],
        },
    }
    result = compute_actions(state)
    assert result.next_action == "handle_blockers"


def test_worst_status_wins() -> None:
    reports = [
        _report(ValidationStatus.PASS, 90),
        _report(ValidationStatus.PASS_WITH_NOTES, 80),
        _report(ValidationStatus.BLOCKED, 50),
    ]
    state = _state_with_reports(reports)
    result = compute_actions(state)
    assert result.next_action == "handle_blockers"
