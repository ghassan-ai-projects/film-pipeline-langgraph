"""Character / environment / camera / style / shot bible generation tools.

Split per bible family; this facade preserves the original import surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from film_pipeline.mcp.tools.spec import ToolSpec

from film_pipeline.mcp.tools.bibles._shared import _extract_script_text
from film_pipeline.mcp.tools.bibles.camera import GENERATE_CAMERA_BIBLE, generate_camera_bible
from film_pipeline.mcp.tools.bibles.character import (
    GENERATE_CHARACTER_BIBLE,
    generate_character_bible,
)
from film_pipeline.mcp.tools.bibles.environment import (
    GENERATE_ENVIRONMENT_BIBLE,
    generate_environment_bible,
)
from film_pipeline.mcp.tools.bibles.shot import GENERATE_SHOT_BIBLE, generate_shot_bible
from film_pipeline.mcp.tools.bibles.style import GENERATE_STYLE_BIBLE, generate_style_bible

BIBLE_TOOLS: tuple[ToolSpec, ...] = (
    GENERATE_CHARACTER_BIBLE,
    GENERATE_ENVIRONMENT_BIBLE,
    GENERATE_CAMERA_BIBLE,
    GENERATE_STYLE_BIBLE,
    GENERATE_SHOT_BIBLE,
)

__all__ = [
    "BIBLE_TOOLS",
    "GENERATE_CAMERA_BIBLE",
    "GENERATE_CHARACTER_BIBLE",
    "GENERATE_ENVIRONMENT_BIBLE",
    "GENERATE_SHOT_BIBLE",
    "GENERATE_STYLE_BIBLE",
    "_extract_script_text",
    "generate_camera_bible",
    "generate_character_bible",
    "generate_environment_bible",
    "generate_shot_bible",
    "generate_style_bible",
]
