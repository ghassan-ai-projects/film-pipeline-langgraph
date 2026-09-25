"""Compatibility aliases for operator models, now owned by ``operations``."""

from film_pipeline.operations.models import ArtifactDetail as ArtifactDetail
from film_pipeline.operations.models import (
    ArtifactRollbackResult as ArtifactRollbackResult,
)
from film_pipeline.operations.models import AuditEvent as AuditEvent
from film_pipeline.operations.models import (
    CheckpointRollbackResult as CheckpointRollbackResult,
)
from film_pipeline.operations.models import DashboardSummary as DashboardSummary
from film_pipeline.operations.models import (
    GenerationWorkspace as GenerationWorkspace,
)
from film_pipeline.operations.models import MutationResult as MutationResult
from film_pipeline.operations.models import OperatorComment as OperatorComment
from film_pipeline.operations.models import (
    OperatorCommentRequest as OperatorCommentRequest,
)
from film_pipeline.operations.models import (
    ProjectCreateRequest as ProjectCreateRequest,
)
from film_pipeline.operations.models import ProjectListItem as ProjectListItem
from film_pipeline.operations.models import ReviewWorkspace as ReviewWorkspace
from film_pipeline.operations.models import (
    ValidationWorkspace as ValidationWorkspace,
)

__all__ = [
    "ArtifactDetail",
    "ArtifactRollbackResult",
    "AuditEvent",
    "CheckpointRollbackResult",
    "DashboardSummary",
    "GenerationWorkspace",
    "MutationResult",
    "OperatorComment",
    "OperatorCommentRequest",
    "ProjectCreateRequest",
    "ProjectListItem",
    "ReviewWorkspace",
    "ValidationWorkspace",
]
