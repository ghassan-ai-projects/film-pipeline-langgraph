"""Review package compatibility paths resolve to governance owners."""

from film_pipeline.governance import (
    ArtifactDiff,
    ReviewPackageGenerator,
    compute_artifact_diff,
)
from film_pipeline.review import diff as legacy_diff
from film_pipeline.review import generator as legacy_generator


def test_review_package_aliases_keep_identity() -> None:
    assert legacy_diff.ArtifactDiff is ArtifactDiff
    assert legacy_diff.compute_artifact_diff is compute_artifact_diff
    assert legacy_generator.ReviewPackageGenerator is ReviewPackageGenerator
