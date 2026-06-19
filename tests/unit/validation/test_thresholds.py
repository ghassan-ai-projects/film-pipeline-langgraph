"""Tests for validation thresholds."""

from __future__ import annotations

from film_pipeline.schemas._base import ValidationStatus
from film_pipeline.schemas.registries.validator_registry import ValidatorThresholds
from film_pipeline.validation.thresholds import (
    is_blocking,
    needs_human_review,
    score_to_status,
)


class TestScoreToStatus:
    def test_pass(self) -> None:
        assert score_to_status(95) == ValidationStatus.PASS
        assert score_to_status(85) == ValidationStatus.PASS

    def test_pass_with_notes(self) -> None:
        assert score_to_status(84) == ValidationStatus.PASS_WITH_NOTES
        assert score_to_status(75) == ValidationStatus.PASS_WITH_NOTES

    def test_blocked(self) -> None:
        assert score_to_status(74) == ValidationStatus.BLOCKED
        assert score_to_status(0) == ValidationStatus.BLOCKED

    def test_custom_thresholds(self) -> None:
        thresholds = ValidatorThresholds(pass_at=90, review_at=80, block_below=80)
        assert score_to_status(91, thresholds) == ValidationStatus.PASS
        assert score_to_status(85, thresholds) == ValidationStatus.PASS_WITH_NOTES
        assert score_to_status(79, thresholds) == ValidationStatus.BLOCKED


class TestIsBlocking:
    def test_blocking(self) -> None:
        assert is_blocking(50) is True
        assert is_blocking(74) is True

    def test_not_blocking(self) -> None:
        assert is_blocking(85) is False
        assert is_blocking(75) is False


class TestNeedsHumanReview:
    def test_needs_review(self) -> None:
        assert needs_human_review(50) is True  # BLOCKED
        # PASS_WITH_NOTES does NOT require human review per this function
        assert needs_human_review(80) is False

    def test_no_review_needed(self) -> None:
        assert needs_human_review(95) is False
        assert needs_human_review(75) is False
