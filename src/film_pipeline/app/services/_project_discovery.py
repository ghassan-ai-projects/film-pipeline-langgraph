"""Discovery and classification of projects found in artifact storage."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from film_pipeline.app._persistence import (
    artifact_root,
    latest_discovered_phase,
    looks_like_project_dir,
)
from film_pipeline.app.services.errors import BackendOperationError
from film_pipeline.app.services.models import ProjectListItem

if TYPE_CHECKING:
    from film_pipeline.app.services.operator import OperatorService


def discover_project_folders(svc: OperatorService, known_ids: set[str]) -> list[ProjectListItem]:
    """Return project folders present in artifact storage but absent from runtime memory."""
    root = artifact_root(svc.runtime)
    if root is None or not root.exists() or not root.is_dir():
        return []
    discovered: list[ProjectListItem] = []
    for project_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        project_id = project_dir.name
        if project_id in known_ids or not looks_like_project_dir(project_dir):
            continue
        discovered.append(_as_discovered_item(project_dir))
    return discovered


def _as_discovered_item(project_dir: Path) -> ProjectListItem:
    """Build the listing entry for a project folder found in artifact storage."""
    project_id = project_dir.name
    return ProjectListItem(
        project_id=project_id,
        title=project_title_from_id(project_id),
        slug=project_id,
        current_phase=latest_discovered_phase(project_dir),
        status="discovered",
        has_blockers=False,
        awaiting_review=False,
        project_kind=project_kind_for_path(project_dir),
        project_root=str(project_dir),
    )


def load_discovered_project(svc: OperatorService, project_id: str) -> dict[str, Any] | None:
    """Register a discovered artifact-storage folder as a live runtime project."""
    root = artifact_root(svc.runtime)
    if root is None:
        return None
    project_dir = root / project_id
    if not project_dir.exists() or not looks_like_project_dir(project_dir):
        return None
    state = svc.runtime.create_project(
        project_id=project_id,
        title=project_title_from_id(project_id),
        slug=project_id,
    )
    state["current_phase"] = latest_discovered_phase(project_dir)
    state["project_kind"] = project_kind_for_path(project_dir)
    state["human_approval_required"] = False
    svc.runtime.projects[project_id] = state
    return state


def project_kind_for_state(state: Mapping[str, Any], project_id: str) -> str:
    explicit = str(state.get("project_kind", "")).strip().lower()
    if explicit:
        return normalize_project_kind(explicit)
    return project_kind_for_name(project_id)


def project_kind_for_path(project_dir: Path) -> str:
    return project_kind_for_name(project_dir.name)


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
