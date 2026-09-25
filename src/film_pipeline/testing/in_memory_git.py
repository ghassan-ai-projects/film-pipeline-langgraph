"""Compatibility aliases for devharness in-memory git.

Re-exports from the canonical owner. Only symbols with real consumers are
kept, so strict mypy sees an explicit export surface.
"""

from film_pipeline.devharness.in_memory_git import (
    InMemoryGitBackend as InMemoryGitBackend,
)
from film_pipeline.devharness.in_memory_git import (
    reset_in_memory_git as reset_in_memory_git,
)

__all__ = ["InMemoryGitBackend", "reset_in_memory_git"]
