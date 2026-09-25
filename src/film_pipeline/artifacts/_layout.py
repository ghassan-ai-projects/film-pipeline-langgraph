"""On-disk layout facts for a project folder (private to the storage core).

This module is the ONLY place that knows the names and relative locations of
the files inside a project directory. Nothing outside ``film_pipeline.artifacts``
should import it: consumers go through
:class:`~film_pipeline.artifacts.project_storage.ProjectStorage`, which returns
typed values rather than paths.

Layout (plan D3)::

    <root>/<project_id>/
    ├── project.json                     typed ProjectRecord (human/MCP entry point)
    ├── README.md                        generated index
    ├── artifacts/<NN-phase>/<id>/       versioned envelopes + views
    ├── media/scenes/<scene>/<shot>/     generated + reference binaries
    ├── index/artifacts.json             derived cache
    ├── state/graph-state.json           machine snapshot
    ├── checkpoints/checkpoints.jsonl    append-only metadata
    ├── audit/audit-log.jsonl            append-only trail
    ├── .storage.lock                    per-project write lock
    ├── .gitignore                       media/ excluded from checkpoint commits
    └── .git/                            per-project checkpoint repository
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from film_pipeline.artifacts.envelope import SchemaTooNewError
from film_pipeline.artifacts.serialization import atomic_write_text

_logger = logging.getLogger(__name__)

PROJECT_FILENAME = "project.json"
GRAPH_STATE_RELPATH = "state/graph-state.json"
CHECKPOINTS_RELPATH = "checkpoints/checkpoints.jsonl"
AUDIT_RELPATH = "audit/audit-log.jsonl"
ARTIFACTS_DIRNAME = "artifacts"
INDEX_DIRNAME = "index"
MEDIA_DIRNAME = "media"
DELIVERABLES_DIRNAME = "deliverables"
STORAGE_LOCK_FILENAME = ".storage.lock"
GITIGNORE_FILENAME = ".gitignore"

#: Storage-layout version stamped on every append-only JSONL record (§1.3: all
#: mutable state files are versioned so a newer writer is detected rather than
#: misread). Deliberately a distinct key: ``schema_version`` inside a record is
#: the per-model string version from ``SchemaBase`` and means something else.
JSONL_STORAGE_VERSION = 1
JSONL_STORAGE_VERSION_KEY = "storage_schema_version"

# Keep per-project git checkpoint repos small: media lives under media/ and is
# tracked by the asset manifest, not by checkpoint commits.
PROJECT_GITIGNORE = f"{MEDIA_DIRNAME}/\n*.mp4\n*.png\n*.jpg\n*.wav\n"


def project_relpaths() -> tuple[str, ...]:
    """Project-relative paths the storage core owns (used by boundary guards)."""
    return (
        PROJECT_FILENAME,
        GRAPH_STATE_RELPATH,
        CHECKPOINTS_RELPATH,
        AUDIT_RELPATH,
        ARTIFACTS_DIRNAME,
        INDEX_DIRNAME,
        MEDIA_DIRNAME,
        DELIVERABLES_DIRNAME,
        STORAGE_LOCK_FILENAME,
        GITIGNORE_FILENAME,
    )


def read_json_file(path: Path) -> Any | None:
    """Parse ``path`` as JSON, or ``None`` when absent/corrupt/non-object."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Could not read %s: %s", path, exc)
        return None
    return raw


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read an append-only JSONL log, skipping torn lines with a warning.

    Each record carries an explicit storage version (§1.3: every mutable state
    file is versioned). A record written by a NEWER layout is refused loudly
    rather than silently misread; an absent version means v1, which is what
    pre-versioning records are.
    """
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
        if not isinstance(item, dict):
            continue
        try:
            found = int(item.get(JSONL_STORAGE_VERSION_KEY, 1))
        except (TypeError, ValueError):
            _logger.warning("Skipping line %d in %s: malformed storage version.", number, path)
            continue
        if found > JSONL_STORAGE_VERSION:
            raise SchemaTooNewError(
                kind=path.name,
                found=found,
                max_supported=JSONL_STORAGE_VERSION,
                path=str(path),
            )
        items.append(item)
    return items


def jsonl_ids(path: Path, id_field: str) -> set[str]:
    """Ids already present in a JSONL log (used to append idempotently)."""
    return {str(item[id_field]) for item in read_jsonl(path) if item.get(id_field) is not None}


def append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Append versioned records to a JSONL log, flushed to disk."""
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps({JSONL_STORAGE_VERSION_KEY: JSONL_STORAGE_VERSION, **record}, sort_keys=True)
        for record in records
    ]
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for line in lines:
            handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def ensure_project_gitignore(project_root: Path) -> None:
    """Write the standard project ``.gitignore`` if it is missing."""
    gitignore = project_root / GITIGNORE_FILENAME
    if not gitignore.exists():
        atomic_write_text(gitignore, PROJECT_GITIGNORE)
