"""Production-data safety guards.

The goal is simple: production directories must never be deleted by tests,
scripts, or accidental code paths.  All destructive operations go through this
module and are refused unless the target is inside an explicitly temporary or
user-persist-root location.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from film_pipeline.storage.storage import resolve_storage_root


class ProductionDataError(RuntimeError):
    """Raised when an operation would destroy data outside a safe zone."""


def persist_root() -> Path:
    """Return the configured persistence base.

    Derived from the resolved storage root; destructive-operation safe zones
    are evaluated against this tree. Resolved before taking the parent so a
    relative root can never widen the safe zone to the whole CWD.
    """
    return resolve_storage_root().resolve().parent


def _temp_roots() -> set[Path]:
    """Collect candidate temporary filesystem roots."""
    roots: set[Path] = set()
    for name in ("TMPDIR", "TEMP", "TMP"):
        value = os.getenv(name)
        if value:
            roots.add(Path(value).resolve())
    roots.add(Path(tempfile.gettempdir()).resolve())
    # pytest/tmp_path roots often live under /private/var/folders on macOS but
    # still resolve into the system temp tree.
    return roots


def _is_under(path: Path, root: Path) -> bool:
    """Return True when *path* equals or is inside *root* after resolving."""
    try:
        resolved_path = path.resolve()
        resolved_root = root.resolve()
    except (OSError, RuntimeError):
        return False
    return resolved_path == resolved_root or resolved_root in resolved_path.parents


def is_safe_to_delete(path: Path) -> bool:
    """Return True only when *path* is in an explicitly disposable location.

    Safe zones are:
    - a system temp directory,
    - the configured storage-root base tree (``FILM_PIPELINE_STORAGE_ROOT``),
    - a directory that contains a ``.film-pipeline-allow-delete`` marker file.
    """
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        return False

    for temp_root in _temp_roots():
        if _is_under(resolved, temp_root):
            return True

    if _is_under(resolved, persist_root()):
        return True

    marker = resolved / ".film-pipeline-allow-delete"
    return bool(marker.exists())


def require_safe_to_delete(path: Path) -> None:
    """Raise ``ProductionDataError`` if *path* is not in a safe zone."""
    if not is_safe_to_delete(path):
        raise ProductionDataError(
            f"Refusing to delete production path: {path}. "
            "Set FILM_PIPELINE_STORAGE_ROOT under a temp directory, "
            "or create a .film-pipeline-allow-delete marker in the target directory."
        )


def safe_rmtree(path: Path) -> None:
    """Delete a directory tree only if it is in a safe zone."""
    require_safe_to_delete(path)
    shutil.rmtree(path, ignore_errors=True)


def move_to_trash(
    source: Path,
    *,
    trash_root: Path | None = None,
    prefix: str = "",
) -> Path:
    """Move *source* to a timestamped trash directory instead of deleting.

    The destination lives under ``<persist_root>/trash`` unless a custom
    ``trash_root`` is supplied.  The operation itself is still guarded by
    ``is_safe_to_delete`` for the destination's parent.
    """
    resolved = source.resolve()
    root = trash_root or (persist_root() / "trash")
    require_safe_to_delete(root)
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    name = f"{prefix}{timestamp}-{resolved.name}"
    destination = root / name
    shutil.move(resolved, destination)
    return destination


def can_delete_project(state: dict[str, Any], *, force: bool = False) -> bool:
    """Return True when the project represented by *state* may be destroyed.

    Test projects are always deletable.  Production projects require either
    ``force=True`` or the ``FILM_PIPELINE_ALLOW_DELETE=1`` environment variable.
    """
    if force:
        return True
    if os.getenv("FILM_PIPELINE_ALLOW_DELETE") == "1":
        return True
    kind = str(state.get("project_kind", "")).strip().lower()
    return kind in {"", "test"}
