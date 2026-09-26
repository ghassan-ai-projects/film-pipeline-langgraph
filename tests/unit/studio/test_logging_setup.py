"""Tests for the entrypoint logging bootstrap [O-F10]."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest

from film_pipeline.studio.logging_setup import _MARKER_ATTR, configure_logging


@pytest.fixture()
def _clean_root_logger(monkeypatch: pytest.MonkeyPatch) -> Any:
    # The repository-wide safety fixture sets this for all tests. These tests
    # explicitly exercise both persistence branches, so start each case with
    # the flag unset and set it only in the precedence test.
    monkeypatch.delenv("FILM_PIPELINE_NO_PERSIST", raising=False)
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    root.handlers[:] = []
    yield root
    marked = [h for h in root.handlers if getattr(h, _MARKER_ATTR, False)]
    for handler in marked:
        handler.close()
    root.handlers[:] = [h for h in root.handlers if not getattr(h, _MARKER_ATTR, False)]
    root.handlers.extend(saved_handlers)
    root.setLevel(saved_level)


def test_stderr_handler_installed_and_idempotent(_clean_root_logger: logging.Logger) -> None:
    configure_logging(persist_enabled=False)
    configure_logging(persist_enabled=False)  # second call must be a no-op
    marked = [h for h in _clean_root_logger.handlers if getattr(h, _MARKER_ATTR, False)]
    assert len(marked) == 1
    assert isinstance(marked[0], logging.StreamHandler)


def test_env_level_mapping(
    _clean_root_logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FILM_PIPELINE_LOG_LEVEL", "DEBUG")
    configure_logging(persist_enabled=False)
    stderr_handler = next(h for h in _clean_root_logger.handlers if getattr(h, _MARKER_ATTR, False))
    assert stderr_handler.level == logging.WARNING


def test_unknown_level_falls_back_to_warning(
    _clean_root_logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FILM_PIPELINE_LOG_LEVEL", "CHATTY")
    configure_logging(persist_enabled=False)
    stderr_handler = next(h for h in _clean_root_logger.handlers if getattr(h, _MARKER_ATTR, False))
    assert stderr_handler.level == logging.WARNING


def test_non_int_logging_attribute_falls_back_to_warning(
    _clean_root_logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
) -> None:
    """logging.BASIC_FORMAT is a str constant — must not crash int coercion."""
    monkeypatch.setenv("FILM_PIPELINE_LOG_LEVEL", "BASIC_FORMAT")
    configure_logging(persist_enabled=False)
    stderr_handler = next(h for h in _clean_root_logger.handlers if getattr(h, _MARKER_ATTR, False))
    assert stderr_handler.level == logging.WARNING


def test_file_handler_when_persistent(
    _clean_root_logger: logging.Logger,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FILM_PIPELINE_LOG_LEVEL", raising=False)
    runtime_root = tmp_path / "runtime"
    configure_logging(runtime_root, persist_enabled=True)

    file_handlers = [
        h
        for h in _clean_root_logger.handlers
        if getattr(h, _MARKER_ATTR, False) and isinstance(h, logging.FileHandler)
    ]
    assert len(file_handlers) == 1
    expected_log = runtime_root / "logs" / "film_pipeline.log"
    assert Path(file_handlers[0].baseFilename) == expected_log
    assert file_handlers[0].level == logging.INFO


def test_no_file_handler_without_persistence(
    _clean_root_logger: logging.Logger, tmp_path: Path
) -> None:
    configure_logging(tmp_path / "runtime", persist_enabled=False)
    assert not any(
        isinstance(h, logging.FileHandler) and getattr(h, _MARKER_ATTR, False)
        for h in _clean_root_logger.handlers
    )


def test_no_file_handler_without_runtime_root(
    _clean_root_logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("film_pipeline.studio._persistence.use_persistent_runtime", lambda: True)
    configure_logging(None)  # e.g. MCP stdio server: no root to write into
    assert not any(isinstance(h, logging.FileHandler) for h in _clean_root_logger.handlers)


def test_stderr_never_drops_below_warning(
    _clean_root_logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FILM_PIPELINE_LOG_LEVEL", "DEBUG")
    configure_logging(persist_enabled=False)
    stderr_handler = next(h for h in _clean_root_logger.handlers if getattr(h, _MARKER_ATTR, False))
    assert stderr_handler.level >= logging.WARNING


def test_persistence_env_var_honored(
    _clean_root_logger: logging.Logger,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default branch defers to FILM_PIPELINE_PERSIST_STATE via persistence_enabled()."""
    monkeypatch.setattr(
        "film_pipeline.studio._persistence.use_persistent_runtime",
        lambda: bool(__import__("os").getenv("FILM_PIPELINE_PERSIST_STATE")),
    )
    monkeypatch.delenv("FILM_PIPELINE_PERSIST_STATE", raising=False)
    configure_logging(tmp_path / "runtime")
    assert not any(isinstance(h, logging.FileHandler) for h in _clean_root_logger.handlers)

    monkeypatch.setenv("FILM_PIPELINE_PERSIST_STATE", "1")
    # Idempotency guard is active from the first call; reset to exercise the
    # env-driven branch cleanly.
    _clean_root_logger.handlers[:] = [
        h for h in _clean_root_logger.handlers if not getattr(h, _MARKER_ATTR, False)
    ]
    configure_logging(tmp_path / "runtime")
    assert any(
        isinstance(h, logging.FileHandler) and getattr(h, _MARKER_ATTR, False)
        for h in _clean_root_logger.handlers
    )


def test_no_persist_wins_over_inherited_persistence(
    _clean_root_logger: logging.Logger,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FILM_PIPELINE_PERSIST_STATE", "1")
    monkeypatch.setenv("FILM_PIPELINE_NO_PERSIST", "1")

    configure_logging(tmp_path / "runtime")

    assert not any(
        isinstance(h, logging.FileHandler) and getattr(h, _MARKER_ATTR, False)
        for h in _clean_root_logger.handlers
    )


def test_no_persist_wins_for_runtime_checkpointer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from langgraph.checkpoint.memory import MemorySaver

    from film_pipeline.studio._persistence import use_persistent_runtime
    from film_pipeline.studio.graph_factory import _default_checkpointer

    monkeypatch.setenv("FILM_PIPELINE_PERSIST_STATE", "1")
    monkeypatch.setenv("FILM_PIPELINE_NO_PERSIST", "1")

    assert use_persistent_runtime() is False
    assert isinstance(_default_checkpointer(), MemorySaver)


def test_disabling_persistence_removes_an_existing_file_handler(
    _clean_root_logger: logging.Logger, tmp_path: Path
) -> None:
    configure_logging(tmp_path / "runtime", persist_enabled=True)
    configure_logging(persist_enabled=False)

    assert not any(
        isinstance(h, logging.FileHandler) and getattr(h, _MARKER_ATTR, False)
        for h in _clean_root_logger.handlers
    )


def test_later_persistent_call_completes_stdio_only_bootstrap(
    _clean_root_logger: logging.Logger, tmp_path: Path
) -> None:
    configure_logging(persist_enabled=False)
    configure_logging(tmp_path / "runtime", persist_enabled=True)

    marked = [h for h in _clean_root_logger.handlers if getattr(h, _MARKER_ATTR, False)]
    stderr_handlers = [
        h
        for h in marked
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
    ]
    assert len(stderr_handlers) == 1
    assert len([h for h in marked if isinstance(h, logging.FileHandler)]) == 1


def test_persistent_call_replaces_handler_for_a_new_runtime_root(
    _clean_root_logger: logging.Logger, tmp_path: Path
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    configure_logging(first_root, persist_enabled=True)
    configure_logging(second_root, persist_enabled=True)

    file_handlers = [
        h
        for h in _clean_root_logger.handlers
        if getattr(h, _MARKER_ATTR, False) and isinstance(h, logging.FileHandler)
    ]
    assert len(file_handlers) == 1
    assert Path(file_handlers[0].baseFilename) == second_root / "logs" / "film_pipeline.log"
