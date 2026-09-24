"""Storage root resolution and layout markers.

Single authority for where project storage lives:

1. explicit argument,
2. ``FILM_PIPELINE_STORAGE_ROOT``,
3. ``FILM_PIPELINE_PERSIST_ROOT`` (deprecated alias, derived as ``<root>/projects``),
4. the default home location (entry points only).

Library constructors never fall back to an implicit root — they require one.
Opening a root is marker-gated: a fresh directory is initialized with a
``storage.json`` marker, a legacy-shaped store is marked for upgrade, and any
other pre-existing directory is refused so stray folders are never silently
adopted as project storage.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from film_pipeline.artifacts.paths import PHASE_DIR_MAP
from film_pipeline.artifacts.serialization import write_json_atomic

_logger = logging.getLogger(__name__)

STORAGE_ROOT_ENV = "FILM_PIPELINE_STORAGE_ROOT"
LEGACY_PERSIST_ROOT_ENV = "FILM_PIPELINE_PERSIST_ROOT"
MARKER_FILENAME = "storage.json"

#: On-disk layout version this build writes. Roots written before the storage
#: upgrade carry no marker at all (layout v0) and are marked when first opened.
LAYOUT_VERSION = 1
MARKER_SCHEMA_VERSION = 1

PROFILE_PRODUCTION = "production"
PROFILE_SANDBOX = "sandbox"

_LEGACY_ALIAS_WARNED = False


class StorageRootError(RuntimeError):
    """Raised when a directory cannot be opened as project storage."""


@dataclass(frozen=True)
class StorageMarker:
    """Marker file contents identifying an initialized storage root."""

    layout_version: int
    schema_version: int
    profile: str
    created_at: str


def default_storage_root() -> Path:
    """Return the default storage root (entry points only)."""
    return Path.home() / ".film-pipeline" / "projects"


def default_runtime_root() -> Path:
    """Return the default runtime-state root, derived from the storage root."""
    return resolve_storage_root().parent / "runtime"


def default_checkpoints_root() -> Path:
    """Return the default LangGraph checkpointer directory."""
    return resolve_storage_root().parent / "checkpoints"


def default_run_root() -> Path:
    """Return the default headless CLI run directory."""
    return resolve_storage_root().parent / "runs" / "default"


def resolve_storage_root(explicit: Path | str | None = None) -> Path:
    """Resolve the storage root: argument, then env vars, then the default.

    ``FILM_PIPELINE_PERSIST_ROOT`` is honored as a deprecated alias and maps
    to ``<persist_root>/projects``.
    """
    global _LEGACY_ALIAS_WARNED
    if explicit is not None:
        return Path(explicit)
    from_env = os.getenv(STORAGE_ROOT_ENV, "").strip()
    if from_env:
        return Path(from_env)
    legacy = os.getenv(LEGACY_PERSIST_ROOT_ENV, "").strip()
    if legacy:
        if not _LEGACY_ALIAS_WARNED:
            _logger.warning(
                "%s is deprecated; set %s instead.",
                LEGACY_PERSIST_ROOT_ENV,
                STORAGE_ROOT_ENV,
            )
            _LEGACY_ALIAS_WARNED = True
        return Path(legacy) / "projects"
    return default_storage_root()


def marker_path(root: Path) -> Path:
    """Return the marker file path inside ``root``."""
    return root / MARKER_FILENAME


def read_marker(root: Path) -> StorageMarker | None:
    """Return the storage marker for ``root``, or ``None`` when absent/invalid."""
    try:
        raw = json.loads(marker_path(root).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    try:
        return StorageMarker(
            layout_version=int(raw["layout_version"]),
            schema_version=int(raw["schema_version"]),
            profile=str(raw["profile"]),
            created_at=str(raw["created_at"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def init_storage_root(root: Path, *, profile: str = PROFILE_PRODUCTION) -> Path:
    """Create ``root`` if needed, write the storage marker, and return ``root``."""
    marker = StorageMarker(
        layout_version=LAYOUT_VERSION,
        schema_version=MARKER_SCHEMA_VERSION,
        profile=profile,
        created_at=datetime.now(UTC).isoformat(),
    )
    root.mkdir(parents=True, exist_ok=True)
    write_json_atomic(marker_path(root), asdict(marker))
    return root


def ensure_storage_root(root: Path, *, profile: str = PROFILE_PRODUCTION) -> Path:
    """Return ``root`` as an openable storage root, initializing or refusing.

    - A non-existent or empty directory is initialized with a marker.
    - A directory already carrying a marker is returned as-is; a marker from a
      newer layout version is refused.
    - An unmarked directory that looks like a legacy film-pipeline store is
      marked for upgrade in place.
    - Anything else is refused: it was not created by this application and must
      not be silently adopted as project storage.
    """
    existing = read_marker(root)
    if existing is not None:
        if existing.layout_version > LAYOUT_VERSION:
            raise StorageRootError(
                f"Storage root {root} was written by a newer layout "
                f"(v{existing.layout_version} > v{LAYOUT_VERSION}). "
                "Upgrade film-pipeline to open it."
            )
        # Older markers (pre-upgrade trees stamped v1) are accepted; the
        # artifact engine migrates them forward (storage-upgrade-plan.md P2).
        return root
    if marker_path(root).exists():
        raise StorageRootError(
            f"Storage marker at {marker_path(root)} is corrupt. Delete the "
            "marker file to re-initialize this root, or restore it from backup."
        )
    if not root.exists():
        init_storage_root(root, profile=profile)
        return root
    if not root.is_dir():
        raise StorageRootError(f"Storage root {root} is not a directory.")
    if not any(root.iterdir()):
        init_storage_root(root, profile=profile)
        return root
    if _looks_like_legacy_store(root):
        _logger.info("Marking legacy storage root %s (layout v0) for upgrade.", root)
        init_storage_root(root, profile=profile)
        return root
    raise StorageRootError(
        f"Refusing to use {root} as project storage: it exists without a "
        f"{MARKER_FILENAME} marker and does not look like a film-pipeline "
        f"store. Set {STORAGE_ROOT_ENV} to your storage root, or remove the "
        "directory if it is not needed."
    )


def _looks_like_legacy_store(root: Path) -> bool:
    """Heuristic: does ``root`` contain pre-upgrade film-pipeline projects?"""
    legacy_phase_names = set(PHASE_DIR_MAP.values()) | {"intake"}
    try:
        children = [p for p in sorted(root.iterdir()) if p.is_dir()]
    except OSError:
        return False
    for child in children[:200]:
        if child.name in legacy_phase_names:
            return True
        if (child / "project-state.json").is_file():
            return True
        if (child / "asset-manifest.json").is_file():
            return True
        if any(
            grandchild.is_dir() and grandchild.name in legacy_phase_names
            for grandchild in child.iterdir()
        ):
            return True
        if _has_legacy_sidecar(child):
            return True
    return False


def _has_legacy_sidecar(project_dir: Path) -> bool:
    """Depth-limited search for any legacy metadata sidecar under one project."""
    for pattern in ("*.meta.json", "*/*.meta.json", "*/*/*.meta.json"):
        if next(project_dir.glob(pattern), None) is not None:
            return True
    return False
