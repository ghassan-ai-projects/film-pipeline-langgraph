"""Discovery and classification of projects found in artifact storage."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from film_pipeline.app._persistence import storage_for
from film_pipeline.app.services.errors import BackendOperationError
from film_pipeline.app.services.models import ProjectListItem

if TYPE_CHECKING:
    from film_pipeline.app.services.operator import OperatorService


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


def project_kind_for_state(state: Mapping[str, Any], project_id: str) -> str:
    explicit = str(state.get("project_kind", "")).strip().lower()
    if explicit:
        return normalize_project_kind(explicit)
    return project_kind_for_name(project_id)


def project_kind_for_name(name: str) -> str:
    lowered = name.lower()
    test_markers = ("test", "fixture", "sample", "tmp", "demo")
    return "test" if any(marker in lowered for marker in test_markers) else "production"


def normalize_project_kind(project_kind: str) -> str:
    kind = project_kind.strip().lower()
    if kind not in {"production", "test"}:
        raise BackendOperationError(
            f"project_kind must be 'production' or 'test', got '{project_kind}'."
        )
    return kind


def project_title_from_id(project_id: str) -> str:
    """Derive a human-readable title from a project folder name."""
    return project_id.replace("-", " ").replace("_", " ").title()
