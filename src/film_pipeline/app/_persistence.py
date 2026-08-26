"""Runtime persistence: restore and persist project state, checkpoints, audit logs.

All disk I/O for surviving restarts lives here. ``StudioRuntime`` delegates to
these functions; they mutate the runtime's in-memory registries directly.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.checkpoints.manager import CheckpointManager
from film_pipeline.schemas.checkpoint import CheckpointMetadata

if TYPE_CHECKING:
    from film_pipeline.app.runtime import StudioRuntime

STATE_FILENAME = "project-state.json"
CHECKPOINTS_FILENAME = "checkpoints.json"
AUDIT_FILENAME = "audit-log.json"

# Keep per-project git checkpoint repos small: media lives in the artifact
# tree and is tracked by the asset manifest, not by checkpoint commits.
_PROJECT_GITIGNORE = "07-generated-assets/\nreferences/\n*.mp4\n*.png\n*.jpg\n*.wav\n"

# Phase directories ordered newest-first; the first one holding any JSON
# artifact decides a discovered project's current phase.
_DISCOVERED_PHASE_ORDER: tuple[tuple[str, str], ...] = (
    ("10-delivery", "delivery"),
    ("09-post", "post"),
    ("08-validation", "qc"),
    ("07-generated-assets", "generation"),
    ("06-generation-plan", "gen_planning"),
    ("05-shot-bible", "shot_bible"),
    ("04-visual-dev", "visual_dev"),
    ("03-script", "script"),
    ("02-development", "development"),
    ("01-vision", "constitution"),
    ("intake", "intake"),
)

PERSIST_ROOT = Path(os.getenv("FILM_PIPELINE_PERSIST_ROOT", Path.home() / ".film-pipeline"))
RUNTIME_ROOT = PERSIST_ROOT / "runtime"


def use_persistent_runtime() -> bool:
    return bool(os.getenv("FILM_PIPELINE_PERSIST_STATE"))


def is_same_or_child(child: Path, parent: Path) -> bool:
    try:
        resolved_child = child.resolve()
        resolved_parent = parent.resolve()
    except OSError:
        return False
    return resolved_child == resolved_parent or resolved_parent in resolved_child.parents


def looks_like_project_dir(project_dir: Path) -> bool:
    return any(project_dir.rglob("*.meta.json")) or any(project_dir.rglob("*.v*.json"))


def latest_discovered_phase(project_dir: Path) -> str:
    for dirname, phase in _DISCOVERED_PHASE_ORDER:
        candidate = project_dir / dirname
        if candidate.exists() and any(candidate.rglob("*.json")):
            return phase
    return ""


def project_git_backend(project_root: Path) -> GitBackend:
    """Initialize (or reuse) the checkpoint git repo for a project root."""
    already_initialized = (project_root / ".git").exists()
    git = GitBackend.init_temp(project_root)
    gitignore = project_root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(_PROJECT_GITIGNORE)
    if not already_initialized:
        with contextlib.suppress(RuntimeError):
            git.commit("checkpoint: initialize project repository")
    return git


def artifact_root(rt: StudioRuntime) -> Path | None:
    store = rt.services.artifact_store if rt.services is not None else None
    root = getattr(store, "_root", None)
    return root if isinstance(root, Path) else None


def artifact_discovery_roots(rt: StudioRuntime) -> list[Path]:
    """Return artifact roots to scan for existing projects.

    The current configured root is checked first.  Legacy CWD-relative
    ``projects/`` and ``.film-pipeline-run/artifacts`` are scanned
    read-only so older projects remain loadable after the migration to
    ``~/.film-pipeline/artifacts``.
    """
    roots: list[Path] = []
    current = artifact_root(rt)
    if current is not None:
        roots.append(current)
    legacy = [Path("projects"), Path(".film-pipeline-run") / "artifacts"]
    for candidate in legacy:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved not in roots and all(
            not is_same_or_child(resolved, existing) for existing in roots
        ):
            roots.append(resolved)
    return roots


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
    """Load one persisted runtime state file into the registries.

    Returns whether the project was restored. Projects already loaded in
    memory and hidden directories are never overwritten.
    """
    project_root = state_path.parent
    project_id = project_root.name
    if project_id in rt.projects or project_id.startswith("."):
        return False
    state = _read_json_file(state_path)
    if not isinstance(state, dict):
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
    restored = sum(
        _restore_state_project(rt, state_path)
        for state_path in sorted(root.glob(f"*/{STATE_FILENAME}"))
    )

    # 2. Discover projects that only exist in artifact storage.
    known_ids = set(rt.projects.keys())
    for store_root in artifact_discovery_roots(rt):
        restored += _discover_artifact_projects(rt, store_root, root, known_ids)
    return restored


def restore_checkpoints(rt: StudioRuntime, project_id: str, project_root: Path) -> None:
    path = project_root / CHECKPOINTS_FILENAME
    raw = _read_json_file(path)
    if not isinstance(raw, list):
        return
    manager = rt.checkpoint_managers.get(project_id)
    for item in raw:
        try:
            meta = CheckpointMetadata.model_validate(item)
        except ValueError:
            continue
        rt.checkpoints[meta.checkpoint_id] = meta
        if manager is not None:
            manager.checkpoints[meta.checkpoint_id] = meta


def restore_audit_events(rt: StudioRuntime, project_root: Path) -> None:
    path = project_root / AUDIT_FILENAME
    raw = _read_json_file(path)
    if not isinstance(raw, list):
        return
    known_ids = {event.get("event_id") for event in rt.audit_events}
    for item in raw:
        if isinstance(item, dict) and item.get("event_id") not in known_ids:
            rt.audit_events.append(item)
    rt.audit_events.sort(key=lambda event: str(event.get("timestamp", "")))


def persist_checkpoints(rt: StudioRuntime, project_id: str) -> None:
    project_root = rt.project_roots.get(project_id)
    if project_root is None:
        return
    metas = [
        json.loads(meta.model_dump_json())
        for meta in rt.checkpoints.values()
        if meta.project_id == project_id
    ]
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / CHECKPOINTS_FILENAME).write_text(json.dumps(metas, indent=2))


def persist_audit_events(rt: StudioRuntime, project_id: str) -> None:
    project_root = rt.project_roots.get(project_id)
    if project_root is None:
        return
    events = [
        event
        for event in rt.audit_events
        if event.get("details", {}).get("project_id") == project_id
    ]
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / AUDIT_FILENAME).write_text(json.dumps(events, indent=2, default=str))


def persist_project_state(rt: StudioRuntime, project_id: str) -> None:
    project = rt.projects[project_id]
    project_root = rt.project_roots[project_id]
    project_root.mkdir(parents=True, exist_ok=True)
    state_path = project_root / STATE_FILENAME
    state_path.write_text(json.dumps(project, indent=2, sort_keys=True, default=str))
