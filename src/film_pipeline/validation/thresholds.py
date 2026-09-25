"""Validation threshold checker — maps scores to pass / review / block."""

from __future__ import annotations

from film_pipeline.schemas.base import ValidationStatus
from film_pipeline.schemas.registries.validator_registry import ValidatorThresholds


def score_to_status(
    score: float,
    thresholds: ValidatorThresholds | None = None,
) -> ValidationStatus:
    """Classify a score into the full four-status contract.

    Default thresholds:
      - pass ≥ 85
      - pass_with_notes ≥ 75
      - needs_revision ≥ 65
      - blocked < 65
    """
    t = thresholds or ValidatorThresholds()

    if score >= t.pass_at:
        return ValidationStatus.PASS
    if score >= t.review_at:
        return ValidationStatus.PASS_WITH_NOTES
    if score >= t.block_below:
        return ValidationStatus.NEEDS_REVISION
    return ValidationStatus.BLOCKED


def is_blocking(score: float, thresholds: ValidatorThresholds | None = None) -> bool:
    """Check whether a score triggers a block."""
    return score_to_status(score, thresholds) == ValidationStatus.BLOCKED


def needs_human_review(score: float, thresholds: ValidatorThresholds | None = None) -> bool:
    """Check whether a score requires human review."""
    status = score_to_status(score, thresholds)
    return status in (ValidationStatus.NEEDS_REVISION, ValidationStatus.BLOCKED)
