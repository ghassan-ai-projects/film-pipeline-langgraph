"""Reusable widgets for the redesigned film studio TUI."""

from __future__ import annotations

from film_pipeline.tui.widgets.action_bar import ActionBar
from film_pipeline.tui.widgets.artifact_list import ArtifactList
from film_pipeline.tui.widgets.inspector import Inspector
from film_pipeline.tui.widgets.issue_list import IssueList
from film_pipeline.tui.widgets.project_form import ProjectForm
from film_pipeline.tui.widgets.stage_nav import StageNav

__all__ = [
    "ActionBar",
    "ArtifactList",
    "Inspector",
    "IssueList",
    "ProjectForm",
    "StageNav",
]
