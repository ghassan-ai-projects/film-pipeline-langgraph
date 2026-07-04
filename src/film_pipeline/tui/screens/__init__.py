"""Textual screens for the redesigned film studio TUI."""

from __future__ import annotations

from film_pipeline.tui.screens.asset_viewer import AssetViewerScreen
from film_pipeline.tui.screens.home import ProjectGalleryScreen
from film_pipeline.tui.screens.legacy import NewProjectScreen, ReviseIdeaScreen
from film_pipeline.tui.screens.review import ReviewGateScreen
from film_pipeline.tui.screens.studio import StudioScreen

__all__ = [
    "AssetViewerScreen",
    "NewProjectScreen",
    "ProjectGalleryScreen",
    "ReviewGateScreen",
    "ReviseIdeaScreen",
    "StudioScreen",
]
