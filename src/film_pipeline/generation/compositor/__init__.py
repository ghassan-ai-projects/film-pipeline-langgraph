"""Composite sheet construction — Pillow-based templates for reference sheets.

Builds production-ready composite sheets (Character Identity, Environment Board)
from generated master frames. Pure image processing — no AI involved.
"""

from __future__ import annotations

from film_pipeline.generation.compositor.environment import build_environment_board
from film_pipeline.generation.compositor.extras import (
    build_expression_sheet,
    build_scale_sheet,
    build_style_board,
)
from film_pipeline.generation.compositor.identity import (
    build_character_identity_sheet,
    replace_tile,
)

__all__ = [
    "build_character_identity_sheet",
    "build_environment_board",
    "build_expression_sheet",
    "build_scale_sheet",
    "build_style_board",
    "replace_tile",
]
