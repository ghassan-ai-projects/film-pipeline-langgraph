"""Shared mutable session state for the studio TUI.

Lives beside :mod:`film_pipeline.tui.app` so screens and widgets can depend
on the state contract without importing the App class itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from film_pipeline.app.services.models import (
    ArtifactDetail,
    DashboardSummary,
    ProjectListItem,
)
from film_pipeline.tui.view_models.models import (
    ReaderView,
    StudioSnapshot,
    TargetSelection,
)


@dataclass
class AppState:
    """Mutable, non-reactive holder for the current studio state.

    Textual's reactive descriptors live on the App; this dataclass is used
    internally to pass a coherent snapshot to screens and widgets without
    exposing every field as a reactive attribute.
    """

    snapshot: StudioSnapshot | None = None
    active_project: ProjectListItem | None = None
    dashboard: DashboardSummary | None = None
    selected_stage: str = ""
    selected_target: TargetSelection | None = None
    selected_artifact: ArtifactDetail | None = None
    reader: ReaderView | None = None
    providers_healthy: int = 0
    providers_total: int = 0
    messages: list[str] = field(default_factory=list)

    def add_message(self, text: str) -> None:
        """Append a status message, keeping the buffer bounded."""
        self.messages.append(text)
        if len(self.messages) > 40:
            self.messages = self.messages[-40:]
