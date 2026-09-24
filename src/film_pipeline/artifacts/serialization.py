"""Deterministic, atomic file writes for storage.

All storage writes go through these helpers: JSON is dumped with sorted keys
and a trailing newline (stable diffs and checksums), and file contents are
written to a sibling temp file and moved into place with
:meth:`pathlib.Path.replace` so a crash can never leave a torn file behind.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4


def dump_json(obj: Any) -> str:
    """Serialize ``obj`` to deterministic, human-readable JSON text."""
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically (sibling temp file + replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}-{uuid4().hex[:8]}")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def write_json_atomic(path: Path, obj: Any) -> None:
    """Write ``obj`` as deterministic JSON atomically."""
    atomic_write_text(path, dump_json(obj))
