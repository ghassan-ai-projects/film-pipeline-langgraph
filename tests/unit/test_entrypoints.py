"""Entrypoint bootstrap tests for the three console surfaces."""

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
    monkeypatch.setattr("film_pipeline.app.logging_setup.configure_logging", configure)
    monkeypatch.setattr(run, "_run_headless_pipeline", lambda _request: {})
    monkeypatch.setattr(run, "_print_summary", lambda _state, _project_id: None)

    runtime_root = tmp_path / "runtime"
    assert run.main([str(idea), "--runtime-root", str(runtime_root)]) == 0
    configure.assert_called_once_with(runtime_root, persist_enabled=True)


def test_tui_main_configures_logging_for_runtime_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from film_pipeline.tui import app

    fake_app = MagicMock()
    monkeypatch.setattr(app, "FilmStudioApp", MagicMock(return_value=fake_app))
    configure = MagicMock()
    monkeypatch.setattr("film_pipeline.app.logging_setup.configure_logging", configure)
    runtime_root = tmp_path / "runtime"
    monkeypatch.delenv("FILM_PIPELINE_PERSIST_STATE", raising=False)
    monkeypatch.setenv("FILM_PIPELINE_RUNTIME_ROOT", str(runtime_root))

    assert app.main(["--create"]) == 0
    # The real entrypoint sets this flag; remove the mutation explicitly so
    # later tests cannot accidentally build a persistent SQLite checkpointer.
    monkeypatch.delenv("FILM_PIPELINE_PERSIST_STATE", raising=False)
    configure.assert_called_once_with(runtime_root)
    fake_app.run.assert_called_once_with()


def test_mcp_main_configures_logging_before_stdio_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from film_pipeline.mcp import server

    monkeypatch.setenv("FILM_PIPELINE_NO_PERSIST", "1")
    monkeypatch.delenv("FILM_PIPELINE_PERSIST_STATE", raising=False)
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("FILM_PIPELINE_RUNTIME_ROOT", str(runtime_root))
    configure = MagicMock()
    monkeypatch.setattr("film_pipeline.app.logging_setup.configure_logging", configure)
    monkeypatch.setattr("film_pipeline.app.bootstrap.validate_environment", list)
    monkeypatch.setattr(server, "_serve_stdio", lambda _server: 0)

    assert server.main() == 0
    configure.assert_called_once_with(runtime_root)
