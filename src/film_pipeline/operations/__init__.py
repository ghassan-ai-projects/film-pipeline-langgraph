"""Operator use cases, their typed view models, and the ports they need."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from film_pipeline.operations.errors import (
    BackendOperationError,
    ProjectNotFoundError,
    ServiceError,
)
from film_pipeline.operations.models import (
    ArtifactDetail,
    ArtifactRollbackResult,
    AuditEvent,
    CheckpointRollbackResult,
    DashboardSummary,
    GenerationWorkspace,
    MutationResult,
    OperatorComment,
    OperatorCommentRequest,
    ProjectCreateRequest,
    ProjectListItem,
    ReviewWorkspace,
    ValidationWorkspace,
)
from film_pipeline.operations.ports import (
    ArtifactStorePort,
    ProviderComposition,
    RuntimePort,
    RuntimeProvider,
    ServicesPort,
    artifact_store_of,
)

#: Names resolved lazily. Importing the operator module eagerly would create a
#: cycle: `projects.classification` imports `operations.errors`, so the
#: `operations` facade must not pull in `operator`, which imports `projects`.
_LAZY_NAMES = {"OperatorService"}

if TYPE_CHECKING:
    # Declared for type checkers only; never imported at runtime.
    from film_pipeline.operations.operator import OperatorService as OperatorService


def __getattr__(name: str) -> Any:
    """Resolve the operator service on first use rather than at import time."""
    if name in _LAZY_NAMES:
        from film_pipeline.operations.operator import OperatorService

        return OperatorService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Include the lazily resolved names in ``dir()``."""
    return sorted(set(__all__) | set(globals()))


__all__ = [
    "ArtifactDetail",
    "ArtifactRollbackResult",
    "ArtifactStorePort",
    "AuditEvent",
    "BackendOperationError",
    "CheckpointRollbackResult",
    "DashboardSummary",
    "GenerationWorkspace",
    "MutationResult",
    "OperatorComment",
    "OperatorCommentRequest",
    "OperatorService",
    "ProjectCreateRequest",
    "ProjectListItem",
    "ProjectNotFoundError",
    "ProviderComposition",
    "ReviewWorkspace",
    "RuntimePort",
    "RuntimeProvider",
    "ServiceError",
    "ServicesPort",
    "ValidationWorkspace",
    "artifact_store_of",
]
