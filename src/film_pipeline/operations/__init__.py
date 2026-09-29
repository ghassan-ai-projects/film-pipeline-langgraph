"""Operator use cases, their result records, and the ports they need.

This package used to be the in-process surface for a removed TUI. It now holds
the operator use cases that still have a caller, plus the `RuntimePort` protocol
the composition root satisfies. See `models.py` for what was deleted and why.
"""

from __future__ import annotations

from film_pipeline.operations._checkpoint_ops import (
    get_checkpoint,
    rollback_artifact,
    rollback_to_checkpoint,
)
from film_pipeline.operations.errors import (
    BackendOperationError,
    ProjectNotFoundError,
    ServiceError,
)
from film_pipeline.operations.models import (
    ArtifactRollbackResult,
    CheckpointRollbackResult,
)
from film_pipeline.operations.ports import (
    ArtifactStorePort,
    RuntimePort,
    ServicesPort,
    artifact_store_of,
)

__all__ = [
    "ArtifactRollbackResult",
    "ArtifactStorePort",
    "BackendOperationError",
    "CheckpointRollbackResult",
    "ProjectNotFoundError",
    "RuntimePort",
    "ServiceError",
    "ServicesPort",
    "artifact_store_of",
    "get_checkpoint",
    "rollback_artifact",
    "rollback_to_checkpoint",
]
