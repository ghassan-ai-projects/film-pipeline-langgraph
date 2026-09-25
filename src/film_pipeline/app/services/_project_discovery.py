"""Discovery of projects found in artifact storage but absent from runtime memory.

Only the two helpers that need a live runtime live here: scanning the storage
root and promoting a discovered folder into a runtime project. The pure
classification rules they rely on — project kind, title, and name policy — are
owned by :mod:`film_pipeline.projects.classification`.

The former names remain importable from this module while its consumers migrate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from film_pipeline.operations.models import ProjectListItem
from film_pipeline.projects.classification import (
    normalize_project_kind as normalize_project_kind,
)
from film_pipeline.projects.classification import (
    project_kind_for_name as project_kind_for_name,
)
from film_pipeline.projects.classification import (
    project_kind_for_state as project_kind_for_state,
)
from film_pipeline.projects.classification import (
    project_title_from_id as project_title_from_id,
)
from film_pipeline.storage.runtime_gateway import project_storage_for as storage_for

if TYPE_CHECKING:
    from film_pipeline.app.services.operator import OperatorService

__all__ = [
    "discover_project_folders",
    "load_discovered_project",
    "normalize_project_kind",
    "project_kind_for_name",
    "project_kind_for_state",
    "project_title_from_id",
]


def discover_project_folders(svc: OperatorService, known_ids: set[str]) -> list[ProjectListItem]:
    """Return project folders present in artifact storage but absent from runtime memory."""
    storage = storage_for(svc.runtime)
    if storage is None or not storage.root.is_dir():
        return []
    discovered: list[ProjectListItem] = []
    for project_id in storage.list_project_ids():
        if project_id in known_ids or not storage.looks_like_project(project_id):
            continue
        discovered.append(_as_discovered_item(storage, project_id))
    return discovered


def _as_discovered_item(storage: Any, project_id: str) -> ProjectListItem:
    """Build the listing entry for a project folder found in artifact storage."""
    return ProjectListItem(
        project_id=project_id,
        title=project_title_from_id(project_id),
        slug=project_id,
        current_phase=storage.latest_artifact_phase(project_id),
        status="discovered",
        has_blockers=False,
        awaiting_review=False,
        project_kind=project_kind_for_name(project_id),
        project_root=str(storage.project_dir(project_id)),
    )


def load_discovered_project(svc: OperatorService, project_id: str) -> dict[str, Any] | None:
    """Register a discovered artifact-storage folder as a live runtime project."""
    storage = storage_for(svc.runtime)
    if storage is None or not storage.looks_like_project(project_id):
        return None
    state = svc.runtime.create_project(
        project_id=project_id,
        title=project_title_from_id(project_id),
        slug=project_id,
    )
    state["current_phase"] = storage.latest_artifact_phase(project_id)
    state["project_kind"] = project_kind_for_name(project_id)
    state["human_approval_required"] = False
    svc.runtime.projects[project_id] = state
    return state
