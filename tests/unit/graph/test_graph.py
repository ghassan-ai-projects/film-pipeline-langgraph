"""Tests for the graph builder and default checkpointer."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from film_pipeline.app.graph_factory import _default_checkpointer, build_graph


def test_default_checkpointer_returns_memory_saver_without_env() -> None:
    os.environ.pop("FILM_PIPELINE_PERSIST_STATE", None)
    saver = _default_checkpointer()
    assert isinstance(saver, MemorySaver)


def test_default_checkpointer_returns_sqlite_when_persist_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from film_pipeline.app import graph_factory as graph_module

    monkeypatch.delenv("FILM_PIPELINE_NO_PERSIST", raising=False)
    monkeypatch.setenv("FILM_PIPELINE_PERSIST_STATE", "1")
    monkeypatch.setattr(graph_module, "default_checkpoints_root", lambda: tmp_path / "checkpoints")
    saver = _default_checkpointer()
    assert isinstance(saver, SqliteSaver)


def test_build_graph_uses_supplied_checkpointer() -> None:
    """A caller-supplied checkpointer is the one the compiled graph carries.

    Asserting only that ``build_graph`` returned something would pass even if
    the supplied saver were dropped in favour of the environment default.
    """
    supplied = MemorySaver()
    graph = build_graph(checkpointer=supplied)
    assert graph.checkpointer is supplied
