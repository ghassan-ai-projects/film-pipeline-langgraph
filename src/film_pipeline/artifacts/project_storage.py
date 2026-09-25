"""Compatibility aliases for :mod:`film_pipeline.storage.project_storage`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.storage.project_storage import _BACKEND_TYPE as _BACKEND_TYPE
from film_pipeline.storage.project_storage import CheckpointRepo as CheckpointRepo
from film_pipeline.storage.project_storage import ProjectStorage as ProjectStorage
from film_pipeline.storage.project_storage import _logger as _logger
from film_pipeline.storage.project_storage import get_git_backend_type as get_git_backend_type
from film_pipeline.storage.project_storage import graph_state_location as graph_state_location
from film_pipeline.storage.project_storage import set_git_backend_type as set_git_backend_type

__all__ = [
    "CheckpointRepo",
    "ProjectStorage",
    "get_git_backend_type",
    "graph_state_location",
    "set_git_backend_type",
]
