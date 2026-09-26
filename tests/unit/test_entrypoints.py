"""Entrypoint bootstrap tests for the console surfaces (CLI, MCP)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


def test_cli_main_configures_logging_for_request_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from film_pipeline.cli import run

    monkeypatch.delenv("FILM_PIPELINE_NO_PERSIST", raising=False)
    idea = tmp_path / "idea.txt"
    idea.write_text("A robot learns to paint.", encoding="utf-8")
    configure = MagicMock()
    monkeypatch.setattr("film_pipeline.studio.logging_setup.configure_logging", configure)
    monkeypatch.setattr(run, "_run_headless_pipeline", lambda _request: {})
    monkeypatch.setattr(run, "_print_summary", lambda _state, _project_id: None)

    runtime_root = tmp_path / "runtime"
    assert run.main([str(idea), "--runtime-root", str(runtime_root)]) == 0
    configure.assert_called_once_with(runtime_root, persist_enabled=True)


def test_mcp_main_configures_logging_before_stdio_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from film_pipeline.mcp import server

    monkeypatch.setenv("FILM_PIPELINE_NO_PERSIST", "1")
    monkeypatch.delenv("FILM_PIPELINE_PERSIST_STATE", raising=False)
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("FILM_PIPELINE_RUNTIME_ROOT", str(runtime_root))
    configure = MagicMock()
    monkeypatch.setattr("film_pipeline.studio.logging_setup.configure_logging", configure)
    monkeypatch.setattr("film_pipeline.studio.bootstrap.validate_environment", list)
    monkeypatch.setattr(server, "_serve_stdio", lambda _server: 0)

    assert server.main() == 0
    configure.assert_called_once_with(runtime_root)


def test_mcp_main_still_logs_when_no_runtime_root_is_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The persistent MCP server must keep a file log with no env override.

    This pins a regression that no test caught: `configured_runtime_root` was
    changed to return ``None`` when unset, and this call site briefly kept calling
    it. `configure_logging(None)` installs **no** file handler, silently, so the
    persistent server lost its log in the normal case (no
    `FILM_PIPELINE_RUNTIME_ROOT`). The sibling test above sets that variable
    explicitly, which is exactly why it masked the break.

    The assertion is on a real path, not on `None`: `runtime_root_from_config()`
    must supply the default when the environment supplies nothing.
    """
    from film_pipeline.mcp import server

    monkeypatch.delenv("FILM_PIPELINE_NO_PERSIST", raising=False)
    monkeypatch.delenv("FILM_PIPELINE_RUNTIME_ROOT", raising=False)
    monkeypatch.setenv("FILM_PIPELINE_PERSIST_STATE", "1")
    monkeypatch.setenv("FILM_PIPELINE_STORAGE_ROOT", str(tmp_path / "store"))

    configure = MagicMock()
    monkeypatch.setattr("film_pipeline.studio.logging_setup.configure_logging", configure)
    monkeypatch.setattr("film_pipeline.studio.bootstrap.validate_environment", list)
    monkeypatch.setattr(server, "_serve_stdio", lambda _server: 0)

    assert server.main() == 0

    configure.assert_called_once()
    (root,), _kwargs = configure.call_args
    assert root is not None, (
        "MCP main passed no runtime root to configure_logging, so the persistent "
        "server silently installs no file handler."
    )
    assert isinstance(root, Path)
