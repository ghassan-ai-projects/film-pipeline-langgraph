"""Runtime persistence orchestration: restore and persist project state.

This module holds **policy only** — which projects to load, how discovered
projects are adopted, and how the runtime's in-memory registries are updated.
It performs no path construction and no file I/O of its own: every read and
write goes through :class:`~film_pipeline.storage.project_storage.ProjectStorage`,
the single owner of the on-disk layout.

That separation is deliberate. Storage decides *where and how* bytes land;
this module decides *what the runtime should do* about them.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.checkpoints.manager import CheckpointManager
from film_pipeline.schemas.checkpoint import CheckpointMetadata
from film_pipeline.schemas.runtime_state import ProjectRecord
from film_pipeline.storage.project_storage import (
    ProjectStorage,
    set_git_backend_type,
)
from film_pipeline.storage.storage import default_runtime_root

_logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from film_pipeline.app.runtime import StudioRuntime

# The application owns backend wiring; the storage core stays dependency-free.
set_git_backend_type(GitBackend)


def configured_runtime_root() -> Path:
    """Return the runtime root selected by the environment or default config."""
    raw_root = os.getenv("FILM_PIPELINE_RUNTIME_ROOT", "").strip()
    return Path(raw_root) if raw_root else default_runtime_root()


def use_persistent_runtime() -> bool:
    """Return whether durable runtime state is enabled.

    The explicit no-persist switch wins over inherited process environment so
    a stdio/test invocation cannot accidentally open SQLite or file stores.
    """
    return bool(os.getenv("FILM_PIPELINE_PERSIST_STATE")) and not bool(
        os.getenv("FILM_PIPELINE_NO_PERSIST")
    )


def storage_for(rt: StudioRuntime) -> ProjectStorage | None:
    """The project-storage gateway for a runtime, or ``None`` without services."""
    if rt.services is None:
        return None
    return ProjectStorage.from_store(rt.services.artifact_store)


def artifact_root(rt: StudioRuntime) -> Path | None:
    """Return the artifact store root configured on the runtime."""
    if rt.services is None:
        return None
    return rt.services.artifact_store.root


def artifact_discovery_roots(rt: StudioRuntime) -> list[Path]:
    """Return artifact roots scanned for existing projects.

    Only the configured storage root is scanned. Pre-upgrade roots are
    never adopted at runtime.
    """
    current = artifact_root(rt)
    return [current] if current is not None else []


def checkpoint_manager_for(storage: ProjectStorage, project_id: str) -> CheckpointManager:
    """Build a checkpoint manager over the project's repository.

    The storage core returns the structurally-typed repo it created; the
    application narrows it to the concrete backend it injected, keeping the
    core free of a ``checkpoints`` dependency.
    """
    backend = cast(GitBackend, storage.git_backend(project_id))
    return CheckpointManager(backend)


# --- Restore ------------------------------------------------------------------


def _restore_state_project(rt: StudioRuntime, storage: ProjectStorage, project_id: str) -> bool:
    """Load one persisted project record into the runtime registries.

    Returns whether the project was restored. Projects already loaded in memory
    are never overwritten.
    """
    if project_id in rt.projects or project_id.startswith("."):
        return False
    state = storage.read_project_record(project_id)
    if state is None:
        return False
    try:
        file_version = int(state.get("schema_version", 1))
    except (TypeError, ValueError):
        _logger.warning("Project record for %s has a malformed schema_version.", project_id)
        return False
    if file_version > ProjectRecord().schema_version:
        _logger.warning(
            "Project record %s was written by a newer layout (schema_version %d "
            "> %d); upgrade film-pipeline to load it.",
            project_id,
            file_version,
            ProjectRecord().schema_version,
        )
        return False
    try:
        state = ProjectRecord.model_validate(state).model_dump(mode="json")
    except ValueError as exc:
        _logger.warning("Skipping unreadable project record %s: %s", project_id, exc)
        return False
    # Discovered projects may carry a project_id that differs from the
    # directory name; regular persisted projects must match.
    if not state.get("discovered") and str(state.get("project_id", "")) != project_id:
        return False
    rt.projects[project_id] = state
    rt.project_roots[project_id] = storage.project_dir(project_id)
    rt.checkpoint_managers[project_id] = checkpoint_manager_for(storage, project_id)
    _restore_checkpoints(rt, storage, project_id)
    _restore_audit_events(rt, storage, project_id)
    return True


def _restore_checkpoints(rt: StudioRuntime, storage: ProjectStorage, project_id: str) -> None:
    manager = rt.checkpoint_managers.get(project_id)
    for item in storage.read_checkpoints(project_id):
        try:
            meta = CheckpointMetadata.model_validate(item)
        except ValueError:
            continue
        rt.checkpoints[meta.checkpoint_id] = meta
        if manager is not None:
            manager.checkpoints[meta.checkpoint_id] = meta


def _restore_audit_events(rt: StudioRuntime, storage: ProjectStorage, project_id: str) -> None:
    known_ids = {event.get("event_id") for event in rt.audit_events}
    for item in storage.read_audit_events(project_id):
        if isinstance(item, dict) and item.get("event_id") not in known_ids:
            rt.audit_events.append(item)
    rt.audit_events.sort(key=lambda event: str(event.get("timestamp", "")))


def _discovered_project_state(
    rt: StudioRuntime, project_id: str, storage: ProjectStorage
) -> dict[str, Any]:
    """Build the placeholder runtime state for an artifact-only project."""
    return {
        "project_id": project_id,
        "title": project_id.replace("-", " ").replace("_", " ").title(),
        "slug": project_id,
        "server_mode": rt.server_mode,
        "current_phase": storage.latest_artifact_phase(project_id),
        "approved": False,
        "human_approval_required": False,
        "human_approval_phase": "",
        "constraints_hints": {},
        "issues": [],
        "discovered": True,
    }


def _adopt_discovered_project(
    rt: StudioRuntime,
    storage: ProjectStorage,
    project_id: str,
    known_ids: set[str],
) -> int:
    """Register an artifact-only project (1 or 0).

    Mutates ``known_ids`` so dedup stays correct across multiple store roots.
    """
    if project_id in known_ids or not storage.looks_like_project(project_id):
        return 0
    rt.projects[project_id] = _discovered_project_state(rt, project_id, storage)
    rt.project_roots[project_id] = storage.project_dir(project_id)
    known_ids.add(project_id)
    storage.ensure_project_dir(project_id)
    rt.checkpoint_managers[project_id] = checkpoint_manager_for(storage, project_id)
    persist_project_state(rt, project_id)
    return 1


def load_persisted_projects(rt: StudioRuntime) -> int:
    """Restore persisted projects and adopt artifact-only projects.

    Returns the number of projects restored or discovered. Projects already
    loaded in memory are never overwritten.
    """
    storage = storage_for(rt)
    if storage is None or not storage.root.is_dir():
        return 0

    # Load projects that have a persisted typed record.
    restored = sum(
        _restore_state_project(rt, storage, project_id)
        for project_id in storage.list_project_ids()
        if storage.read_project_record(project_id) is not None
    )

    # Adopt projects that only exist in artifact storage.
    known_ids = set(rt.projects.keys())
    for _store_root in artifact_discovery_roots(rt):
        restored += sum(
            _adopt_discovered_project(rt, storage, project_id, known_ids)
            for project_id in storage.list_project_ids()
        )
    return restored


# --- Persist ------------------------------------------------------------------


def persist_checkpoints(rt: StudioRuntime, project_id: str) -> None:
    """Append checkpoint metadata not yet on disk to the project's log."""
    storage = storage_for(rt)
    if storage is None or project_id not in rt.project_roots:
        return
    records = [
        meta.model_dump(mode="json")
        for meta in rt.checkpoints.values()
        if meta.project_id == project_id
    ]
    storage.append_checkpoints(project_id, records)


def persist_audit_events(rt: StudioRuntime, project_id: str) -> None:
    """Append audit events not yet on disk to the project's log."""
    storage = storage_for(rt)
    if storage is None or project_id not in rt.project_roots:
        return
    records = [
        event
        for event in rt.audit_events
        if event.get("details", {}).get("project_id") == project_id
    ]
    storage.append_audit_events(project_id, _stringified(records))


def _stringified(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Make arbitrary audit payloads JSON-serializable (audit is best-effort)."""
    import json

    return [json.loads(json.dumps(record, default=str)) for record in records]


def persist_project_state(rt: StudioRuntime, project_id: str) -> None:
    """Persist the typed project record (``project.json``, atomic)."""
    storage = storage_for(rt)
    if storage is None:
        return
    record = ProjectRecord.model_validate(rt.projects[project_id])
    storage.write_project_record(project_id, record)
