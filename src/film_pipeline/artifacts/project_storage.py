"""The single gateway to a project's on-disk layout.

Everything that reads or writes inside a project folder goes through
:class:`ProjectStorage`. It is the only component that knows where files live:
consumers pass typed values and project ids in, and get typed values and
project-relative facts back. They never build paths, never import layout
constants, and never touch the serialization primitives.

Boundary rules (AGENTS.md):

- This module imports only ``artifacts`` internals and ``schemas``. It must not
  import ``graph``, ``mcp``, ``app``, ``generation``, or ``checkpoints``.
- The per-project git backend is **injected** at construction (a
  ``backend_type``) so the core stays free of a ``checkpoints`` dependency and
  tests can substitute an in-process double.
- Layout facts live in :mod:`film_pipeline.artifacts._layout`, which is private
  to this package.

Typical use::

    storage = ProjectStorage(store)  # store supplies the root
    storage.write_project_record("p1", record)
    snapshot = storage.read_graph_state("p1")
    storage.append_audit_events("p1", events)
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from film_pipeline.artifacts import _layout
from film_pipeline.artifacts.serialization import write_json_atomic
from film_pipeline.schemas.runtime_state import GraphStateSnapshot, ProjectRecord

if TYPE_CHECKING:
    from film_pipeline.artifacts.store import ArtifactStore

_logger = logging.getLogger(__name__)


class CheckpointRepo(Protocol):
    """The slice of a checkpoint backend the storage core needs.

    Declared structurally so the core never imports ``checkpoints``: the
    application injects any object satisfying this protocol.
    """

    def commit(self, message: str, paths: list[str] | None = ...) -> Any: ...

    def list_files(self, ref: str = ...) -> list[str]: ...

    @classmethod
    def init_temp(cls, project_root: Path) -> CheckpointRepo: ...


#: Sentinel for "no backend type injected" so the core never imports checkpoints
#: at module scope.
_BACKEND_TYPE: type[Any] | None = None


class ProjectStorage:
    """Reads and writes every file inside a project folder.

    Construct with the :class:`~film_pipeline.artifacts.store.ArtifactStore`
    that owns the storage root, so both the artifact tree and the state files
    resolve to the same single project directory.
    """

    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    # --- Location (project-relative facts, not paths) -----------------------

    @property
    def root(self) -> Path:
        """The storage root every project directory lives under."""
        return self._store.root

    def project_dir(self, project_id: str) -> Path:
        """The one directory holding everything for ``project_id``."""
        return self._store.root / project_id

    def project_exists(self, project_id: str) -> bool:
        return self.project_dir(project_id).is_dir()

    def project_record_name(self) -> str:
        """The typed project record's filename (for git path tracking)."""
        return _layout.PROJECT_FILENAME

    def list_project_ids(self) -> list[str]:
        """Project ids present on disk (hidden directories excluded)."""
        root = self._store.root
        if not root.is_dir():
            return []
        return sorted(
            entry.name
            for entry in root.iterdir()
            if entry.is_dir() and not entry.name.startswith(".")
        )

    def looks_like_project(self, project_id: str) -> bool:
        """Whether a directory is a v2 project (typed record or artifact tree)."""
        project_dir = self.project_dir(project_id)
        if (project_dir / _layout.PROJECT_FILENAME).is_file():
            return True
        return any(project_dir.glob(f"{_layout.ARTIFACTS_DIRNAME}/*/*/meta.json"))

    def latest_artifact_phase(self, project_id: str) -> str:
        """Newest phase that has stored artifacts, or ``""`` when none.

        Derived from the canonical phase map, so discovery cannot drift from
        the write side.
        """
        from film_pipeline.artifacts.paths import PHASE_DIR_MAP

        base = self.project_dir(project_id) / _layout.ARTIFACTS_DIRNAME
        for phase, dirname in reversed(PHASE_DIR_MAP.items()):
            candidate = base / dirname
            if candidate.exists() and any(candidate.rglob("*.json")):
                return phase
        return ""

    # --- Typed project record (project.json) --------------------------------

    def read_project_record(self, project_id: str) -> dict[str, Any] | None:
        """The raw record dict (validated), or ``None`` when absent/unreadable."""
        path = self.project_dir(project_id) / _layout.PROJECT_FILENAME
        raw = _layout.read_json_file(path)
        if not isinstance(raw, dict):
            return None
        return raw

    def write_project_record(self, project_id: str, record: ProjectRecord) -> None:
        """Persist the typed project record atomically."""
        project_dir = self.project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(project_dir / _layout.PROJECT_FILENAME, record.model_dump(mode="json"))

    def ensure_project_dir(self, project_id: str) -> Path:
        """Create the project directory (and standard .gitignore) if needed."""
        project_dir = self.project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        _layout.ensure_project_gitignore(project_dir)
        return project_dir

    # --- Machine state snapshot (state/graph-state.json) --------------------

    def read_graph_state(self, project_id: str) -> GraphStateSnapshot | None:
        """The machine snapshot, or ``None`` when absent/unreadable."""
        path = self.project_dir(project_id) / _layout.GRAPH_STATE_RELPATH
        raw = _layout.read_json_file(path)
        if not isinstance(raw, dict):
            return None
        try:
            return GraphStateSnapshot.model_validate(raw)
        except ValueError as exc:
            _logger.warning("Skipping unreadable graph state %s: %s", path, exc)
            return None

    def write_graph_state(self, project_id: str, snapshot: GraphStateSnapshot) -> None:
        """Persist one machine snapshot atomically."""
        path = self.project_dir(project_id) / _layout.GRAPH_STATE_RELPATH
        write_json_atomic(path, snapshot.model_dump(mode="json"))

    # --- Append-only JSONL logs ---------------------------------------------

    def read_checkpoints(self, project_id: str) -> list[dict[str, Any]]:
        return _layout.read_jsonl(self.project_dir(project_id) / _layout.CHECKPOINTS_RELPATH)

    def append_checkpoints(self, project_id: str, records: list[dict[str, Any]]) -> None:
        known = _layout.jsonl_ids(
            self.project_dir(project_id) / _layout.CHECKPOINTS_RELPATH, "checkpoint_id"
        )
        fresh = [r for r in records if str(r.get("checkpoint_id", "")) not in known]
        _layout.append_jsonl(self.project_dir(project_id) / _layout.CHECKPOINTS_RELPATH, fresh)

    def read_audit_events(self, project_id: str) -> list[dict[str, Any]]:
        return _layout.read_jsonl(self.project_dir(project_id) / _layout.AUDIT_RELPATH)

    def append_audit_events(self, project_id: str, records: list[dict[str, Any]]) -> None:
        known = _layout.jsonl_ids(self.project_dir(project_id) / _layout.AUDIT_RELPATH, "event_id")
        fresh = [r for r in records if str(r.get("event_id", "")) not in known]
        _layout.append_jsonl(self.project_dir(project_id) / _layout.AUDIT_RELPATH, fresh)

    # --- Media --------------------------------------------------------------

    def media_dir(self, project_id: str, scene_id: str, shot_id: str) -> Path:
        """The directory holding one shot's media, created if needed."""
        directory = (
            self.project_dir(project_id) / _layout.MEDIA_DIRNAME / "scenes" / scene_id / shot_id
        )
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    # --- Per-project checkpoint repository ----------------------------------

    def git_backend(self, project_id: str) -> CheckpointRepo:
        """Initialize (or reuse) the checkpoint repository for a project."""
        if _BACKEND_TYPE is None:
            raise RuntimeError(
                "No git backend type is configured for ProjectStorage. Call "
                "set_git_backend_type() at start-up (see app._persistence)."
            )
        project_dir = self.project_dir(project_id)
        already_initialized = (project_dir / ".git").exists()
        project_dir.mkdir(parents=True, exist_ok=True)
        git: CheckpointRepo = _BACKEND_TYPE.init_temp(project_dir)
        _layout.ensure_project_gitignore(project_dir)
        if not already_initialized:
            with contextlib.suppress(RuntimeError):
                git.commit("checkpoint: initialize project repository")
        return git


def set_git_backend_type(backend_type: type[Any]) -> None:
    """Inject the checkpoint backend used for per-project repositories.

    Kept here (rather than importing ``checkpoints``) so the storage core has no
    dependency on another sub-package; the application wires the real backend.
    """
    global _BACKEND_TYPE
    _BACKEND_TYPE = backend_type


def get_git_backend_type() -> type[Any] | None:
    """The injected backend type, or ``None`` when unset."""
    return _BACKEND_TYPE


def graph_state_location() -> str:
    """Project-relative location of the machine snapshot.

    Exposed as data so callers can record it as a checkpoint reference without
    knowing (or importing) the layout constant.
    """
    return _layout.GRAPH_STATE_RELPATH
