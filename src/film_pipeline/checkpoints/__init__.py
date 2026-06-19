"""Checkpointing, resume snapshots, invalidation engine, and rollback."""

from __future__ import annotations

from film_pipeline.checkpoints.branches import BranchManager
from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.checkpoints.invalidation import DEPENDENCY_GRAPH, InvalidationEngine
from film_pipeline.checkpoints.manager import CheckpointManager
from film_pipeline.checkpoints.resume import ResumeManager, ResumeSnapshot
from film_pipeline.checkpoints.rollback import RollbackManager

__all__ = [
    "DEPENDENCY_GRAPH",
    "BranchManager",
    "CheckpointManager",
    "GitBackend",
    "InvalidationEngine",
    "ResumeManager",
    "ResumeSnapshot",
    "RollbackManager",
]
