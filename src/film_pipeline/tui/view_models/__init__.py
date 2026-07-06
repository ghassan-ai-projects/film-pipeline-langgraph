"""View models for the film studio TUI.

Shared dataclasses plus the artifact/scene rendering builders used by the
studio screens and widgets.
"""

from __future__ import annotations

from film_pipeline.tui.view_models.builders_reader import (
    build_artifact_reader,
    build_overview_reader,
    validation_issue_rows,
)
from film_pipeline.tui.view_models.models import (
    GRAPH_PHASES,
    ReaderView,
    StudioSnapshot,
    TargetSelection,
)

__all__ = [
    "GRAPH_PHASES",
    "ReaderView",
    "StudioSnapshot",
    "TargetSelection",
    "build_artifact_reader",
    "build_overview_reader",
    "validation_issue_rows",
]
