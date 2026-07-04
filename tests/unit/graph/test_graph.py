"""Tests for the graph builder and default checkpointer."""

from __future__ import annotations

import os
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from film_pipeline.graph.graph import _default_checkpointer, build_graph


def test_default_checkpointer_returns_memory_saver_without_env() -> None:
    os.environ.pop("FILM_PIPELINE_PERSIST_STATE", None)
    saver = _default_checkpointer()
    assert isinstance(saver, MemorySaver)


def test_default_checkpointer_returns_sqlite_when_persist_enabled(
    tmp_path: Path,
) -> None:
    from film_pipeline.graph import graph as graph_module

    original_dir = graph_module._CHECKPOINT_DIR
    try:
        graph_module._CHECKPOINT_DIR = tmp_path
        graph_module._CHECKPOINT_DB = tmp_path / "cp.sqlite"
        os.environ["FILM_PIPELINE_PERSIST_STATE"] = "1"
        saver = _default_checkpointer()
        assert isinstance(saver, SqliteSaver)
    finally:
        os.environ.pop("FILM_PIPELINE_PERSIST_STATE", None)
        graph_module._CHECKPOINT_DIR = original_dir
        graph_module._CHECKPOINT_DB = original_dir / "checkpoints.sqlite"


def test_build_graph_uses_supplied_checkpointer() -> None:
    graph = build_graph(checkpointer=MemorySaver())
    assert graph is not None
