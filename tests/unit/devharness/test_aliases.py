"""Legacy test harness imports resolve to the development harness owner."""

from film_pipeline import devharness, testing
from film_pipeline.devharness.in_memory_git import InMemoryGitBackend
from film_pipeline.devharness.storage import make_store
from film_pipeline.testing.in_memory_git import InMemoryGitBackend as LegacyGitBackend
from film_pipeline.testing.storage import make_store as legacy_make_store


def test_legacy_harness_aliases_keep_identity() -> None:
    assert testing.MockHumanActor is devharness.MockHumanActor
    assert testing.MockModelAdapter is devharness.MockModelAdapter
    assert LegacyGitBackend is InMemoryGitBackend
    assert legacy_make_store is make_store
