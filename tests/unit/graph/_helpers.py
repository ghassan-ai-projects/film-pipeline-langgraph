"""Shared test helpers for graph unit tests."""

from __future__ import annotations

from pathlib import Path

from film_pipeline.app.mock_responses import default_mock_responses
from film_pipeline.graph.services import GraphServices


def _services(tmp_path: Path) -> GraphServices:
    return GraphServices.for_mock_runtime(
        artifacts_root=str(tmp_path / "artifacts"), mock_responses=default_mock_responses()
    )
