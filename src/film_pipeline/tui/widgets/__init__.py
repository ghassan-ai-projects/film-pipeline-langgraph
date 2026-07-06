"""Widgets for the film studio TUI."""

from __future__ import annotations

from film_pipeline.tui.widgets.action_bar import ActionBar
from film_pipeline.tui.widgets.artifact_list import ArtifactList
from film_pipeline.tui.widgets.asset_browser import AssetBrowser
from film_pipeline.tui.widgets.issue_list import IssueList
from film_pipeline.tui.widgets.project_form import ProjectForm
from film_pipeline.tui.widgets.reader import Reader
from film_pipeline.tui.widgets.scene_browser import SceneBrowser
from film_pipeline.tui.widgets.stage_nav import StageNav

__all__ = [
    "ActionBar",
    "ArtifactList",
    "AssetBrowser",
    "IssueList",
    "ProjectForm",
    "Reader",
    "SceneBrowser",
    "StageNav",
]
