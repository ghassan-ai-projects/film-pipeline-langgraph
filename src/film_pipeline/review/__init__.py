"""Review package generator for human approval gates.

Every human approval gate produces a structured :class:`ReviewPackage`
containing artifacts, diffs, validation results, issues, costs, and
available actions.
"""

from __future__ import annotations

from film_pipeline.governance.actions import AvailableActions, compute_available_actions
from film_pipeline.review.diff import ArtifactDiff, compute_artifact_diff
from film_pipeline.review.generator import REVIEW_TYPE_MAP, ReviewPackageGenerator

__all__ = [
    "REVIEW_TYPE_MAP",
    "ArtifactDiff",
    "AvailableActions",
    "ReviewPackageGenerator",
    "compute_artifact_diff",
    "compute_available_actions",
]
