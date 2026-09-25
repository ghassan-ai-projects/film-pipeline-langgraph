"""Compatibility aliases for :mod:`film_pipeline.storage.rendering`."""

from __future__ import annotations

from film_pipeline.storage.rendering import Renderer as Renderer

# Private helpers still reached through this path during migration.
from film_pipeline.storage.rendering import _bullets as _bullets
from film_pipeline.storage.rendering import _finding_lines as _finding_lines
from film_pipeline.storage.rendering import _rows as _rows
from film_pipeline.storage.rendering import _section as _section
from film_pipeline.storage.rendering import _table as _table
from film_pipeline.storage.rendering import render_bible as render_bible
from film_pipeline.storage.rendering import render_consensus_report as render_consensus_report
from film_pipeline.storage.rendering import render_prose as render_prose
from film_pipeline.storage.rendering import render_review_package as render_review_package
from film_pipeline.storage.rendering import render_scene_list as render_scene_list
from film_pipeline.storage.rendering import render_script as render_script
from film_pipeline.storage.rendering import render_shot_matrix as render_shot_matrix
from film_pipeline.storage.rendering import render_validation_report as render_validation_report

__all__ = [
    "Renderer",
    "render_bible",
    "render_consensus_report",
    "render_prose",
    "render_review_package",
    "render_scene_list",
    "render_script",
    "render_shot_matrix",
    "render_validation_report",
]
