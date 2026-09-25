"""Review imports remain aliases of governance action policy."""

from film_pipeline.governance import AvailableActions, compute_available_actions
from film_pipeline.review.actions import (
    AvailableActions as LegacyAvailableActions,
)
from film_pipeline.review.actions import (
    compute_available_actions as legacy_compute_available_actions,
)


def test_review_action_aliases_keep_identity() -> None:
    assert LegacyAvailableActions is AvailableActions
    assert legacy_compute_available_actions is compute_available_actions
