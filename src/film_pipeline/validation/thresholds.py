"""Validation threshold checker — maps scores to pass / review / block."""

from __future__ import annotations

from film_pipeline.schemas._base import ValidationStatus
from film_pipeline.schemas.registries.validator_registry import ValidatorThresholds


def score_to_status(
    score: float,
    thresholds: ValidatorThresholds | None = None,
) -> ValidationStatus:
    """Classify a score using the given thresholds.

    Default thresholds: pass ≥ 85, review ≥ 75, block < 75.
    """
    t = thresholds or ValidatorThresholds()

    if score >= t.pass_at:
        return ValidationStatus.PASS
    if score >= t.block_below:
        return ValidationStatus.PASS_WITH_NOTES
    return ValidationStatus.BLOCKED


def is_blocking(score: float, thresholds: ValidatorThresholds | None = None) -> bool:
    """Check whether a score triggers a block."""
    return score_to_status(score, thresholds) == ValidationStatus.BLOCKED


def needs_human_review(score: float, thresholds: ValidatorThresholds | None = None) -> bool:
    """Check whether a score requires human review."""
    status = score_to_status(score, thresholds)
    return status in (ValidationStatus.NEEDS_REVISION, ValidationStatus.BLOCKED)
