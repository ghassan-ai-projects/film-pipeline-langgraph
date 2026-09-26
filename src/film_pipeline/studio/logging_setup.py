"""Logging bootstrap for the console entrypoints [O-F10].

Only console-script binaries configure logging (``mcp.server.main``,
``cli.run.main``); libraries never do. The stderr handler
defaults to WARNING because the MCP stdio transport shares the stderr stream —
anything chattier corrupts the protocol channel. When state persistence is
enabled and a runtime root is known, a rotating file handler records INFO+.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from film_pipeline.studio import _persistence

_LEVEL_ENV_VAR = "FILM_PIPELINE_LOG_LEVEL"
_MARKER_ATTR = "_film_pipeline_bootstrap"
_MAX_BYTES = 1_000_000
_BACKUP_COUNT = 5


def _resolve_level() -> int:
    """Map FILM_PIPELINE_LOG_LEVEL to a logging level; unknown values warn to WARNING."""
    raw = os.getenv(_LEVEL_ENV_VAR, "").strip().upper()
    level = getattr(logging, raw, None) if raw else None
    # Guard isinstance: logging also exposes non-level constants (e.g.
    # BASIC_FORMAT) that would crash the int() coercion below.
    if not isinstance(level, int):
        return logging.WARNING
    return level


def configure_logging(
    runtime_root: Path | str | None = None,
    *,
    persist_enabled: bool | None = None,
) -> None:
    """Install stderr and, when requested, a rotating-file handler.

    Idempotent: handlers carry a marker attribute and re-invocations never
    duplicate them. A later call may add the file handler if an earlier
    stdio-only bootstrap ran before persistence or a runtime root was known.

    Args:
        runtime_root: project runtime root; required for the file handler,
            which writes to ``<runtime_root>/logs/film_pipeline.log``.
        persist_enabled: override the ``FILM_PIPELINE_PERSIST_STATE`` check
            (tests); ``None`` defers to the environment as usual.
    """
    root = logging.getLogger()
    level = _resolve_level()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Stdio transports may share stderr with operator diagnostics.  A verbose
    # environment setting may enrich the file, but it must never make stderr
    # noisier than WARNING.
    stderr_level = max(level, logging.WARNING)
    stderr_handler = next(
        (
            handler
            for handler in root.handlers
            if getattr(handler, _MARKER_ATTR, False)
            and isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, logging.FileHandler)
        ),
        None,
    )
    if stderr_handler is None:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(stderr_level)
        stderr_handler.setFormatter(formatter)
        setattr(stderr_handler, _MARKER_ATTR, True)
        root.addHandler(stderr_handler)

    enabled = (
        False
        if os.getenv("FILM_PIPELINE_NO_PERSIST")
        else (_persistence.use_persistent_runtime() if persist_enabled is None else persist_enabled)
    )
    if not enabled:
        for handler in list(root.handlers):
            if getattr(handler, _MARKER_ATTR, False) and isinstance(handler, logging.FileHandler):
                root.removeHandler(handler)
                handler.close()

    expected_log: Path | None = None
    if runtime_root is not None and enabled:
        log_dir = Path(runtime_root) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        expected_log = (log_dir / "film_pipeline.log").resolve()
        # A process may serve more than one runtime in tests or an embedded
        # host. Do not let the first runtime's marked handler capture the
        # second runtime's records.
        for handler in list(root.handlers):
            if not (
                getattr(handler, _MARKER_ATTR, False) and isinstance(handler, logging.FileHandler)
            ):
                continue
            if Path(handler.baseFilename).resolve() != expected_log:
                root.removeHandler(handler)
                handler.close()

    has_file_handler = any(
        getattr(handler, _MARKER_ATTR, False) and isinstance(handler, logging.FileHandler)
        for handler in root.handlers
    )
    if expected_log is not None and not has_file_handler:
        file_handler = RotatingFileHandler(
            expected_log,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
        )
        # The file sees everything from INFO up regardless of stderr verbosity.
        file_handler.setLevel(min(level, logging.INFO))
        file_handler.setFormatter(formatter)
        setattr(file_handler, _MARKER_ATTR, True)
        root.addHandler(file_handler)

    marked_levels = [
        handler.level for handler in root.handlers if getattr(handler, _MARKER_ATTR, False)
    ]
    if marked_levels:
        root.setLevel(min(marked_levels))
