"""Project identity, classification, and reference resolution contracts."""

from film_pipeline.projects.classification import (
    VALID_PROJECT_KINDS,
    InvalidProjectKindError,
    normalize_project_kind,
    project_kind_for_name,
    project_kind_for_state,
    project_title_from_id,
)
from film_pipeline.projects.resolution import (
    AmbiguousProjectError,
    ProjectRecord,
    ProjectRegistry,
    ResolutionResult,
)

__all__ = [
    "VALID_PROJECT_KINDS",
    "AmbiguousProjectError",
    "InvalidProjectKindError",
    "ProjectRecord",
    "ProjectRegistry",
    "ResolutionResult",
    "normalize_project_kind",
    "project_kind_for_name",
    "project_kind_for_state",
    "project_title_from_id",
]
