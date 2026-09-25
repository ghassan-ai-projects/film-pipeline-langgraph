"""Runtime context — holds the operational state for MCP tools.

This is the bridge between the MCP tool surface and the LangGraph backend.
In production, this would be a proper session/process manager.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from film_pipeline.app import _graph_exec, _persistence, _provider_seeds
from film_pipeline.app._persistence import (
    PROJECT_FILENAME,
    configured_runtime_root,
    project_git_backend,
    use_persistent_runtime,
)
from film_pipeline.app.safety import ProductionDataError, can_delete_project, move_to_trash
from film_pipeline.artifacts.storage import default_runtime_root, resolve_storage_root
from film_pipeline.checkpoints.manager import CheckpointManager
from film_pipeline.graph.services import GraphServices
from film_pipeline.schemas._base import FilmPhase
from film_pipeline.schemas.checkpoint import CheckpointMetadata

_logger = logging.getLogger(__name__)


@dataclass
class StudioRuntime:
    """Operational state for the film studio runtime.

    Holds active project state, graph instance, checkpoints, audit trail,
    and provider registries. MCP tools read and write through this context.
    """

    projects: dict[str, dict[str, Any]] = field(default_factory=dict)
    active_project_id: str = ""
    graph: Any = None  # CompiledStateGraph
    server_mode: str = "mock"
    services: GraphServices | None = None
    checkpoints: dict[str, CheckpointMetadata] = field(default_factory=dict)
    audit_events: list[dict[str, Any]] = field(default_factory=list)
    provider_adapters: dict[str, Any] = field(default_factory=dict)
    provider_health: dict[str, Any] = field(default_factory=dict)
    project_roots: dict[str, Path] = field(default_factory=dict)
    checkpoint_managers: dict[str, CheckpointManager] = field(default_factory=dict)
    runtime_root: Path | None = None

    def __post_init__(self) -> None:
        self.server_mode = _normalize_server_mode(self.server_mode)
        if self.runtime_root is None:
            if os.getenv("FILM_PIPELINE_RUNTIME_ROOT", "").strip():
                self.runtime_root = configured_runtime_root()
            elif use_persistent_runtime():
                self.runtime_root = default_runtime_root()
                self.runtime_root.mkdir(parents=True, exist_ok=True)
            else:
                # Non-persistent invocation: use a throwaway directory and
                # never touch the user's home or the current directory.
                self.runtime_root = Path(tempfile.gettempdir()) / (
                    f"film_pipeline_runtime_{os.getpid()}"
                )
        if self.services is None:
            # One root for the whole project folder (plan §1 / D3): the artifact
            # store opens the runtime root itself, so state and artifacts are
            # siblings inside ``<root>/<project_id>/`` rather than split across
            # two trees. A throwaway runtime root gets a throwaway store.
            self.services = _build_services_for_mode(
                self.server_mode, artifacts_root=self.runtime_root
            )
        self.load_persisted_projects()

    # --- Persistence across restarts ---

    def load_persisted_projects(self) -> int:
        """Restore projects from runtime state files and discover artifact-only projects.

        Returns the number of projects restored or discovered. Projects already
        loaded in memory are never overwritten.
        """
        return _persistence.load_persisted_projects(self)

    def _persist_checkpoints(self, project_id: str) -> None:
        _persistence.persist_checkpoints(self, project_id)

    def _persist_audit_events(self, project_id: str) -> None:
        _persistence.persist_audit_events(self, project_id)

    def _persist_project_state(self, project_id: str) -> None:
        _persistence.persist_project_state(self, project_id)

    # --- Project management ---

    def create_project(self, project_id: str, title: str = "", slug: str = "") -> dict[str, Any]:
        if project_id in self.projects:
            raise ValueError(f"Project '{project_id}' already exists.")
        assert self.runtime_root is not None
        project_root = self.runtime_root / project_id
        git = project_git_backend(project_root)
        state: dict[str, Any] = {
            "project_id": project_id,
            "title": title,
            "slug": slug or project_id,
            "server_mode": self.server_mode,
            "current_phase": "",
            "approved": False,
            "human_approval_required": False,
            "human_approval_phase": "",
            "constraints_hints": {},
            "issues": [],
        }
        self.projects[project_id] = state
        self.project_roots[project_id] = project_root
        self.checkpoint_managers[project_id] = CheckpointManager(git)
        self._persist_project_state(project_id)
        git.commit("project: initialize runtime state", [PROJECT_FILENAME])
        self._record_audit("system", "create_project", project_id=project_id)
        return state

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self.projects.get(project_id)

    def delete_project(self, project_id: str, *, force: bool = False) -> bool:
        """Remove a project from runtime state and archive its on-disk data.

        Call only while no other session is writing to the project (the
        store's per-project lock covers saves, not archival).

        Returns ``True`` when the project existed and was removed, ``False``
        otherwise. Runtime state is moved to ``~/.film-pipeline/trash`` instead
        of being deleted; artifacts are also archived when the path is safe.

        Production projects require ``force=True`` or
        ``FILM_PIPELINE_ALLOW_DELETE=1``.
        """
        if project_id not in self.projects:
            return False
        self._require_deletable_project(project_id, force=force)
        project_root = self._detach_project_state(project_id)
        if project_root is not None:
            self._archive_directory(
                project_root, trash_prefix=f"runtime-{project_id}-", force=force
            )
        self._archive_project_artifacts(project_id, force=force)
        self._drop_project_checkpoints(project_id)
        return True

    def _require_deletable_project(self, project_id: str, *, force: bool) -> None:
        """Raise ProductionDataError unless the project may be deleted."""
        state = self.projects[project_id]
        if can_delete_project(state, force=force):
            return
        raise ProductionDataError(
            f"Refusing to delete production project '{project_id}'. "
            "Set force=True or FILM_PIPELINE_ALLOW_DELETE=1 to override."
        )

    def _detach_project_state(self, project_id: str) -> Path | None:
        """Forget every in-memory registration for the project and return its former root."""
        project_root = self.project_roots.pop(project_id, None)
        self.checkpoint_managers.pop(project_id, None)
        self.projects.pop(project_id, None)
        if self.active_project_id == project_id:
            self.active_project_id = ""
        self._record_audit("system", "delete_project", project_id=project_id)
        return project_root

    def _archive_directory(self, path: Path, *, trash_prefix: str, force: bool) -> None:
        """Move a directory to the trash, hard-removing it only when ``force`` allows."""
        try:
            move_to_trash(path, prefix=trash_prefix)
        except ProductionDataError:
            if not force:
                raise
            shutil.rmtree(path, ignore_errors=True)

    def _archive_project_artifacts(self, project_id: str, *, force: bool) -> None:
        """Move the project's stored artifacts to the trash."""
        project_artifact_dir = self._artifact_root() / project_id
        if not project_artifact_dir.exists():
            return
        self._archive_directory(
            project_artifact_dir, trash_prefix=f"artifacts-{project_id}-", force=force
        )

    def _artifact_root(self) -> Path:
        """Resolve the directory where the artifact store keeps project artifacts."""
        if self.services is not None:
            return self.services.artifact_store.root
        return resolve_storage_root()

    def _drop_project_checkpoints(self, project_id: str) -> None:
        """Forget every checkpoint belonging to the deleted project."""
        self.checkpoints = {
            checkpoint_id: meta
            for checkpoint_id, meta in self.checkpoints.items()
            if meta.project_id != project_id
        }

    def set_active(self, project_id: str) -> None:
        if project_id not in self.projects:
            raise ValueError(f"Project '{project_id}' not found.")
        self.active_project_id = project_id
        self._record_audit("system", "set_active", project_id=project_id)

    def get_active(self) -> dict[str, Any] | None:
        if not self.active_project_id:
            return None
        return self.projects.get(self.active_project_id)

    # --- Graph ---

    # --- Graph execution (see _graph_exec) ---

    def ensure_graph(self) -> Any:
        """Lazy-load and cache the graph instance."""
        return _graph_exec.ensure_graph(self)

    def run_graph(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the graph with the given state, persisting results for recovery."""
        return _graph_exec.run_graph(self, state)

    def _auto_checkpoint(self, state: dict[str, Any]) -> None:
        _graph_exec.auto_checkpoint(self, state)

    def approve_phase(self) -> dict[str, Any]:
        """Approve the current phase and advance (graph resume with manual fallback)."""
        return _graph_exec.approve_phase(self)

    def run_validation(self, project_id: str | None = None) -> dict[str, Any]:
        """Run validators against current-phase artifacts without advancing."""
        return _graph_exec.run_validation(self, project_id)

    def request_revision(self, note: str = "") -> dict[str, Any]:
        """Request revision of the current phase via graph resume."""
        return _graph_exec.request_revision(self, note)

    def _run_phase_node(self, state: dict[str, Any], phase: str) -> dict[str, Any]:
        return _graph_exec.run_phase_node(self, state, phase)

    # --- Checkpoints ---

    def create_checkpoint(
        self,
        project_id: str,
        phase: str,
        reason: str,
        *,
        artifact_versions: dict[str, str] | None = None,
        graph_state_ref: str = "",
    ) -> CheckpointMetadata:
        project = self.projects.get(project_id)
        if project is None:
            raise ValueError(f"Project '{project_id}' not found.")
        manager = self.checkpoint_managers.get(project_id)
        if manager is None:
            raise ValueError(f"Checkpoint manager for project '{project_id}' not found.")
        self._persist_project_state(project_id)
        meta = manager.create(
            project_id=project_id,
            phase=FilmPhase(phase or "intake"),
            reason=reason,
            artifact_versions=artifact_versions,
            graph_state_ref=graph_state_ref,
        )
        self.checkpoints[meta.checkpoint_id] = meta
        self._persist_checkpoints(project_id)
        self._record_audit(
            "system",
            "create_checkpoint",
            project_id=project_id,
            checkpoint_id=meta.checkpoint_id,
            phase=phase,
        )
        return meta

    def list_checkpoints(self, project_id: str | None = None) -> list[CheckpointMetadata]:
        if project_id:
            return [c for c in self.checkpoints.values() if c.project_id == project_id]
        return list(self.checkpoints.values())

    def get_checkpoint(self, checkpoint_id: str) -> CheckpointMetadata | None:
        return self.checkpoints.get(checkpoint_id)

    # --- Audit ---

    def _record_audit(self, actor: str, action: str, **details: str) -> None:
        self.audit_events.append(
            {
                "event_id": f"audit:{action}:{uuid4().hex[:8]}",
                "timestamp": datetime.now(UTC).isoformat(),
                "actor": actor,
                "action": action,
                "details": details,
            }
        )
        project_id = str(details.get("project_id", ""))
        if project_id and project_id in self.project_roots:
            self._persist_audit_events(project_id)

    def get_audit_log(
        self, project_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        events = self.audit_events
        if project_id:
            events = [e for e in events if e.get("details", {}).get("project_id") == project_id]
        return events[-limit:]

    # --- Operator comments ---

    def add_operator_comment(
        self,
        project_id: str,
        *,
        target_type: str,
        target_id: str,
        body: str,
        phase: str = "",
        source: str = "operator",
    ) -> dict[str, Any]:
        """Persist an operator comment on a project target."""
        project = self.projects.get(project_id)
        if project is None:
            raise ValueError(f"Project '{project_id}' not found.")
        comment = {
            "comment_id": f"comment:{uuid4().hex[:8]}",
            "project_id": project_id,
            "target_type": target_type,
            "target_id": target_id,
            "body": body,
            "phase": phase,
            "source": source,
            "created_at": datetime.now(UTC).isoformat(),
            "resolved": False,
        }
        project.setdefault("_operator_comments", []).append(comment)
        self._persist_project_state(project_id)
        self._record_audit(
            "human",
            "add_operator_comment",
            project_id=project_id,
            target_type=target_type,
            target_id=target_id,
            phase=phase,
        )
        return comment

    def list_operator_comments(
        self,
        project_id: str,
        *,
        include_resolved: bool = False,
    ) -> list[dict[str, Any]]:
        """Return operator comments for a project."""
        project = self.projects.get(project_id)
        if project is None:
            raise ValueError(f"Project '{project_id}' not found.")
        comments = [
            comment
            for comment in cast(list[dict[str, Any]], project.get("_operator_comments", []))
            if include_resolved or not comment.get("resolved", False)
        ]
        return list(comments)

    # --- Provider registry ---

    def register_provider(self, provider_id: str, adapter: Any) -> None:
        self.provider_adapters[provider_id] = adapter

    def get_provider(self, provider_id: str) -> Any | None:
        return self.provider_adapters.get(provider_id)

    def list_providers(self) -> list[str]:
        return list(self.provider_adapters.keys())

    def clear_providers(self) -> None:
        self.provider_adapters.clear()
        self.provider_health.clear()

    # --- Provider health ---

    def set_provider_health(self, provider_id: str, status: str, reason: str = "") -> None:
        self.provider_health[provider_id] = {"status": status, "reason": reason}

    def get_provider_health(self, provider_id: str) -> dict[str, Any] | None:
        return self.provider_health.get(provider_id)

    def get_all_health(self) -> dict[str, dict[str, Any]]:
        return dict(self.provider_health)

    def seed_default_provider_health(self) -> None:
        """Seed provider health rows and adapters for the configured runtime mode."""
        _provider_seeds.seed_default_provider_health(self)

    def seed_default_provider_adapters(self) -> None:
        """Register default provider adapters for the runtime mode."""
        _provider_seeds.seed_default_provider_adapters(self)

    def default_video_provider(self) -> tuple[str, str]:
        """Return the (provider_id, model) pair generation should default to."""
        return _provider_seeds.default_video_provider(self)


def create_runtime(server_mode: str | None = None) -> StudioRuntime:
    """Create a runtime aligned to the requested or configured server mode."""
    mode = _normalize_server_mode(server_mode or _configured_server_mode())
    return StudioRuntime(server_mode=mode)


def reset_runtime(server_mode: str | None = None) -> StudioRuntime:
    """Recreate the global runtime, primarily for tests and mode changes."""
    global _RUNTIME, _RUNTIME_MODE_OVERRIDE
    _RUNTIME_MODE_OVERRIDE = (
        _normalize_server_mode(server_mode) if server_mode is not None else None
    )
    _RUNTIME = create_runtime(server_mode)
    return _RUNTIME


def get_runtime() -> StudioRuntime:
    global _RUNTIME
    configured_mode = _configured_server_mode()
    if _RUNTIME is None or _RUNTIME.server_mode != configured_mode:
        _RUNTIME = create_runtime(configured_mode)
        _RUNTIME.seed_default_provider_health()
    return _RUNTIME


def _build_services_for_mode(
    server_mode: str, *, artifacts_root: Path | None = None
) -> GraphServices:
    if server_mode == "real":
        return GraphServices.for_real_runtime(artifacts_root=artifacts_root)
    from film_pipeline.app.mock_responses import default_mock_responses

    return GraphServices.for_mock_runtime(
        artifacts_root=artifacts_root,
        mock_responses=default_mock_responses(),
    )


def _normalize_server_mode(server_mode: str) -> str:
    mode = server_mode.strip().lower()
    if mode not in {"mock", "real"}:
        raise ValueError(f"server_mode must be 'mock' or 'real', got '{server_mode}'")
    return mode


def _configured_server_mode() -> str:
    if _RUNTIME_MODE_OVERRIDE is not None:
        return _RUNTIME_MODE_OVERRIDE
    return _normalize_server_mode(os.getenv("FILM_PIPELINE_MCP_MODE", "mock"))


# Global singleton for MCP tools
_RUNTIME: StudioRuntime | None = None
_RUNTIME_MODE_OVERRIDE: str | None = None
