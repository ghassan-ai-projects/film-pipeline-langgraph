"""Compatibility aliases for project discovery, now owned by ``projects``."""

from film_pipeline.projects.discovery import (
    discover_project_folders as discover_project_folders,
)
from film_pipeline.projects.discovery import (
    load_discovered_project as load_discovered_project,
)

__all__ = ["discover_project_folders", "load_discovered_project"]
