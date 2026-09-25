"""Test helpers for isolated storage roots.

Tests must never touch real storage. These helpers create marked sandbox
roots so a test cannot confuse a throwaway directory with production storage.
"""

from __future__ import annotations

from pathlib import Path

from film_pipeline.storage.storage import PROFILE_SANDBOX, init_storage_root
from film_pipeline.storage.store import ArtifactStore


def sandbox_store_root(path: Path) -> Path:
    """Create and mark ``path`` as a sandbox storage root; return it."""
    return init_storage_root(path, profile=PROFILE_SANDBOX)


def make_store(path: Path) -> ArtifactStore:
    """Create a marked sandbox storage root at ``path`` and a store over it."""
    return ArtifactStore(root=sandbox_store_root(path))
