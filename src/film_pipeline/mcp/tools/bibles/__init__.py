"""Character / environment / camera / style / shot bible generation tools.

Split per bible family; this facade preserves the original import surface.
"""

from __future__ import annotations

from film_pipeline.mcp.tools.bibles._shared import _extract_script_text
from film_pipeline.mcp.tools.bibles.camera import generate_camera_bible
from film_pipeline.mcp.tools.bibles.character import generate_character_bible
from film_pipeline.mcp.tools.bibles.environment import generate_environment_bible
from film_pipeline.mcp.tools.bibles.shot import generate_shot_bible
from film_pipeline.mcp.tools.bibles.style import generate_style_bible

__all__ = [
    "_extract_script_text",
    "generate_camera_bible",
    "generate_character_bible",
    "generate_environment_bible",
    "generate_shot_bible",
    "generate_style_bible",
]
