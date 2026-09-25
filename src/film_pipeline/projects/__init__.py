"""Project identity and reference resolution contracts."""

from film_pipeline.projects.resolution import (
    AmbiguousProjectError,
    ProjectRecord,
    ProjectRegistry,
    ResolutionResult,
)

__all__ = [
    "AmbiguousProjectError",
    "ProjectRecord",
    "ProjectRegistry",
    "ResolutionResult",
]
