"""Runtime persistence: restore and persist project state, checkpoints, audit logs.

All disk I/O for surviving restarts lives here. ``StudioRuntime`` delegates to
these functions; they mutate the runtime's in-memory registries directly.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from film_pipeline.artifacts.paths import PHASE_DIR_MAP
from film_pipeline.artifacts.serialization import write_json_atomic
from film_pipeline.artifacts.storage import default_runtime_root
from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.checkpoints.manager import CheckpointManager
from film_pipeline.schemas.checkpoint import CheckpointMetadata
from film_pipeline.schemas.runtime_state import ProjectRecord

_logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from film_pipeline.app.runtime import StudioRuntime

PROJECT_FILENAME = "project.json"
LEGACY_STATE_FILENAME = "project-state.json"  # read-only fallback
GRAPH_STATE_RELPATH = "state/graph-state.json"
CHECKPOINTS_RELPATH = "checkpoints/checkpoints.jsonl"
AUDIT_RELPATH = "audit/audit-log.jsonl"
LEGACY_CHECKPOINTS_FILENAME = "checkpoints.json"
LEGACY_AUDIT_FILENAME = "audit-log.json"

# Keep per-project git checkpoint repos small: media lives in the artifact
# tree and is tracked by the asset manifest, not by checkpoint commits.
_PROJECT_GITIGNORE = "07-generated-assets/\nreferences/\n*.mp4\n*.png\n*.jpg\n*.wav\n"

# Phase directories ordered newest-first; the first one holding any JSON
# artifact decides a discovered project's current phase. Derived from the
# canonical map so discovery can never drift from the write side.
_DISCOVERED_PHASE_ORDER: tuple[tuple[str, str], ...] = tuple(
    (dirname, phase) for phase, dirname in reversed(PHASE_DIR_MAP.items())
)


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


def looks_like_project_dir(project_dir: Path) -> bool:
    """Recognize both storage layouts: legacy sidecars and v2 artifact trees."""
    if any(project_dir.rglob("*.meta.json")) or any(project_dir.rglob("*.v*.json")):
        return True
    return any(project_dir.glob("artifacts/*/*/meta.json"))


def latest_discovered_phase(project_dir: Path) -> str:
    for dirname, phase in _DISCOVERED_PHASE_ORDER:
        for candidate in (
            project_dir / dirname,
            project_dir / "artifacts" / dirname,
        ):
            if candidate.exists() and any(candidate.rglob("*.json")):
                return phase
    return ""


# Backend factory used to initialize a project's checkpoint repository. Defaults
# to real git; tests swap in a fast in-process double via ``set_git_backend_type``
# to avoid spawning a ``git`` subprocess (and writing a ``.git`` tree) per project.
_GIT_BACKEND_TYPE: type[GitBackend] = GitBackend


def set_git_backend_type(backend_type: type[GitBackend]) -> None:
    """Override the backend used by :func:`project_git_backend` (test seam)."""
    global _GIT_BACKEND_TYPE
    _GIT_BACKEND_TYPE = backend_type


def reset_git_backend_type() -> None:
    """Restore the real git backend."""
    global _GIT_BACKEND_TYPE
    _GIT_BACKEND_TYPE = GitBackend


def project_git_backend(project_root: Path) -> GitBackend:
    """Initialize (or reuse) the checkpoint git repo for a project root."""
    already_initialized = (project_root / ".git").exists()
    git = _GIT_BACKEND_TYPE.init_temp(project_root)
    gitignore = project_root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(_PROJECT_GITIGNORE)
    if not already_initialized:
        with contextlib.suppress(RuntimeError):
            git.commit("checkpoint: initialize project repository")
    return git


def artifact_root(rt: StudioRuntime) -> Path | None:
    """Return the artifact store root configured on the runtime."""
    if rt.services is None:
        return None
    return rt.services.artifact_store.root


def artifact_discovery_roots(rt: StudioRuntime) -> list[Path]:
    """Return artifact roots scanned for existing projects.

    Only the configured storage root is scanned. Legacy CWD-relative
    ``projects/`` and ``.film-pipeline-run/artifacts`` are never adopted at
    runtime; old projects come forward through the storage migration command.
    """
    current = artifact_root(rt)
    return [current] if current is not None else []


def _read_json_file(path: Path) -> Any | None:
    """Return the parsed JSON payload of ``path``.

    Returns ``None`` when the file is unreadable or not valid JSON; callers
    treat that as "nothing persisted here" rather than a fatal error.
    """
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _restore_state_project(rt: StudioRuntime, state_path: Path) -> bool:
    """Load one persisted project record into the registries.

    ``state_path`` is a ``project.json``; the legacy ``project-state.json``
    name is accepted read-only until the storage migration. Returns whether
    the project was restored. Projects already loaded in memory and hidden
    directories are never overwritten.
    """
    project_root = state_path.parent
    project_id = project_root.name
    if project_id in rt.projects or project_id.startswith("."):
        return False
    state = _read_json_file(state_path)
    if not isinstance(state, dict):
        return False
    try:
        file_version = int(state.get("schema_version", 1))
    except (TypeError, ValueError):
        _logger.warning("Project record %s has a malformed schema_version.", state_path)
        return False
    if file_version > ProjectRecord().schema_version:
        _logger.warning(
            "Project record %s was written by a newer layout (schema_version %d "
            "> %d); upgrade film-pipeline to load it.",
            state_path,
            file_version,
            ProjectRecord().schema_version,
        )
        return False
    try:
        state = ProjectRecord.model_validate(state).model_dump(mode="json")
    except ValueError as exc:
        _logger.warning("Skipping unreadable project record %s: %s", state_path, exc)
        return False
    # Discovered projects may carry a project_id that differs from the
    # directory name; regular persisted projects must match.
    if not state.get("discovered") and str(state.get("project_id", "")) != project_id:
        return False
    rt.projects[project_id] = state
    rt.project_roots[project_id] = project_root
    rt.checkpoint_managers[project_id] = CheckpointManager(project_git_backend(project_root))
    restore_checkpoints(rt, project_id, project_root)
    restore_audit_events(rt, project_root)
    return True


def _discovered_project_state(
    rt: StudioRuntime, project_id: str, project_dir: Path
) -> dict[str, Any]:
    """Build the placeholder runtime state for an artifact-only project."""
    return {
        "project_id": project_id,
        "title": project_id.replace("-", " ").replace("_", " ").title(),
        "slug": project_id,
        "server_mode": rt.server_mode,
        "current_phase": latest_discovered_phase(project_dir),
        "approved": False,
        "human_approval_required": False,
        "human_approval_phase": "",
        "constraints_hints": {},
        "issues": [],
        "discovered": True,
    }


def _adopt_discovered_project(
    rt: StudioRuntime,
    runtime_root: Path,
    project_dir: Path,
    known_ids: set[str],
) -> int:
    """Register an artifact-only project under the runtime root (1 or 0).

    Mutates ``known_ids`` so dedup stays correct across multiple store roots.
    """
    project_id = project_dir.name
    if project_id in known_ids or not looks_like_project_dir(project_dir):
        return 0
    project_root = runtime_root / project_id
    rt.projects[project_id] = _discovered_project_state(rt, project_id, project_dir)
    rt.project_roots[project_id] = project_root
    known_ids.add(project_id)
    project_root.mkdir(parents=True, exist_ok=True)
    rt.checkpoint_managers[project_id] = CheckpointManager(project_git_backend(project_root))
    if not (project_root / PROJECT_FILENAME).exists():
        persist_project_state(rt, project_id)
    return 1


def _discover_artifact_projects(
    rt: StudioRuntime,
    store_root: Path | None,
    runtime_root: Path,
    known_ids: set[str],
) -> int:
    """Adopt every artifact-only project found below one store root."""
    if store_root is None or not store_root.exists():
        return 0
    restored = 0
    for project_dir in sorted(p for p in store_root.iterdir() if p.is_dir()):
        restored += _adopt_discovered_project(rt, runtime_root, project_dir, known_ids)
    return restored


def load_persisted_projects(rt: StudioRuntime) -> int:
    """Restore projects from runtime state files and discover artifact-only projects.

    Returns the number of projects restored or discovered. Projects already
    loaded in memory are never overwritten.
    """
    root = rt.runtime_root
    if root is None or not root.is_dir():
        return 0

    # 1. Load projects that have a persisted runtime state file.
    # Typed records win: restore every project.json first, then legacy
    # project-state.json files only for projects without one (the stale
    # legacy file must never shadow the newer record).
    seen: set[Path] = set()
    restored = 0
    for state_path in sorted(root.glob(f"*/{PROJECT_FILENAME}")):
        if _restore_state_project(rt, state_path):
            restored += 1
        seen.add(state_path.parent.resolve())
    for state_path in sorted(root.glob(f"*/{LEGACY_STATE_FILENAME}")):
        if state_path.parent.resolve() in seen:
            continue
        if _restore_state_project(rt, state_path):
            restored += 1

    # 2. Discover projects that only exist in artifact storage.
    known_ids = set(rt.projects.keys())
    for store_root in artifact_discovery_roots(rt):
        restored += _discover_artifact_projects(rt, store_root, root, known_ids)
    return restored


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            _logger.warning(
                "Skipping unparseable line %d in %s (torn or corrupt JSONL).",
                number,
                path,
            )
            continue
        if isinstance(item, dict):
            items.append(item)
    return items


def _jsonl_ids(path: Path, id_field: str) -> set[str]:
    return {str(item[id_field]) for item in _read_jsonl(path) if item.get(id_field) is not None}


def _append_jsonl(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for line in lines:
            handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def restore_checkpoints(rt: StudioRuntime, project_id: str, project_root: Path) -> None:
    items = _read_jsonl(project_root / CHECKPOINTS_RELPATH)
    if not items:
        # Legacy rewritten-array file, read-only until the storage migration.
        legacy = _read_json_file(project_root / LEGACY_CHECKPOINTS_FILENAME)
        items = legacy if isinstance(legacy, list) else []
    manager = rt.checkpoint_managers.get(project_id)
    for item in items:
        try:
            meta = CheckpointMetadata.model_validate(item)
        except ValueError:
            continue
        rt.checkpoints[meta.checkpoint_id] = meta
        if manager is not None:
            manager.checkpoints[meta.checkpoint_id] = meta


def restore_audit_events(rt: StudioRuntime, project_root: Path) -> None:
    events = _read_jsonl(project_root / AUDIT_RELPATH)
    if not events:
        legacy = _read_json_file(project_root / LEGACY_AUDIT_FILENAME)
        events = legacy if isinstance(legacy, list) else []
    known_ids = {event.get("event_id") for event in rt.audit_events}
    for item in events:
        if isinstance(item, dict) and item.get("event_id") not in known_ids:
            rt.audit_events.append(item)
    rt.audit_events.sort(key=lambda event: str(event.get("timestamp", "")))


def persist_checkpoints(rt: StudioRuntime, project_id: str) -> None:
    """Append checkpoint metadata not yet on disk to the project's JSONL log."""
    project_root = rt.project_roots.get(project_id)
    if project_root is None:
        return
    log_path = project_root / CHECKPOINTS_RELPATH
    known = _jsonl_ids(log_path, "checkpoint_id")
    lines: list[str] = []
    for meta in rt.checkpoints.values():
        if meta.project_id != project_id or meta.checkpoint_id in known:
            continue
        lines.append(json.dumps(meta.model_dump(mode="json"), sort_keys=True))
    if lines:
        _append_jsonl(log_path, lines)


def persist_audit_events(rt: StudioRuntime, project_id: str) -> None:
    """Append audit events not yet on disk to the project's JSONL log."""
    project_root = rt.project_roots.get(project_id)
    if project_root is None:
        return
    log_path = project_root / AUDIT_RELPATH
    known = _jsonl_ids(log_path, "event_id")
    lines: list[str] = []
    for event in rt.audit_events:
        if event.get("details", {}).get("project_id") != project_id:
            continue
        if event.get("event_id") in known:
            continue
        lines.append(json.dumps(event, sort_keys=True, default=str))
    if lines:
        _append_jsonl(log_path, lines)


def persist_project_state(rt: StudioRuntime, project_id: str) -> None:
    """Persist the typed project record (``project.json``, atomic)."""
    project = rt.projects[project_id]
    project_root = rt.project_roots[project_id]
    project_root.mkdir(parents=True, exist_ok=True)
    record = ProjectRecord.model_validate(project)
    write_json_atomic(project_root / PROJECT_FILENAME, record.model_dump(mode="json"))
