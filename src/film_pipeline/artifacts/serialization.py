"""Deterministic, atomic file writes for storage.

All storage writes go through these helpers: JSON is dumped with sorted keys
and a trailing newline (stable diffs and checksums), and file contents are
written to a sibling temp file and moved into place with
:meth:`pathlib.Path.replace` so a crash can never leave a torn file behind.

Non-finite floats (``NaN``/``Infinity``) are rejected rather than written:
Python emits them as bare literals, which is not legal JSON, and a reader that
normalizes them would recompute a different checksum — turning a silent bad
write into a permanently unreadable artifact. Failing closed at this single
write boundary keeps every stored artifact readable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4


class NonFiniteNumberError(ValueError):
    """Raised when a value to be stored contains NaN or a non-finite float."""


def _reject_non_finite(value: Any, path: str = "payload") -> None:
    """Raise if ``value`` contains a non-finite float anywhere.

    ``bool`` is excluded explicitly because it subclasses ``int``, and dict
    keys are checked so a non-finite key cannot slip through as a string.
    """
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise NonFiniteNumberError(
                f"{path} contains a non-finite number ({value!r}), which is not "
                "valid JSON and would make the stored artifact unreadable. "
                "Pass a finite value instead."
            )
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_non_finite(key, f"{path}.{key}")
            _reject_non_finite(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple, set, frozenset)):
        for index, item in enumerate(value):
            _reject_non_finite(item, f"{path}[{index}]")


def dump_json(obj: Any) -> str:
    """Serialize ``obj`` to deterministic, human-readable JSON text.

    Raises :class:`NonFiniteNumberError` if ``obj`` holds NaN or infinities,
    so an unreadable artifact can never be written.
    """
    _reject_non_finite(obj)
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
