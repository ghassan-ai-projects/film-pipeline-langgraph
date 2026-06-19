"""Validation registry and validator framework.

Validators are pluggable components that score artifacts against rubrics and
produce structured :class:`ValidationReport` records.
"""

from __future__ import annotations

from film_pipeline.validation.base import BaseValidator
from film_pipeline.validation.consensus import ConsensusBuilder
from film_pipeline.validation.registry import ValidatorRegistry
from film_pipeline.validation.thresholds import (
    is_blocking,
    needs_human_review,
    score_to_status,
)
from film_pipeline.validation.validators import MVP_VALIDATORS

__all__ = [
    "MVP_VALIDATORS",
    "BaseValidator",
    "ConsensusBuilder",
    "ValidatorRegistry",
    "is_blocking",
    "needs_human_review",
    "score_to_status",
]
