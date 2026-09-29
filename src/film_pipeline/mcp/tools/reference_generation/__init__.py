"""The `generate_reference_images` MCP tool.

The use case it drives lives in `film_pipeline.generation.reference` (doc 03 slice
2). This package holds only the MCP-facing half: argument validation, response
shaping, and the spec declaration.
"""

from __future__ import annotations

from film_pipeline.mcp.tools.reference_generation.tool import (
    GENERATE_REFERENCE_IMAGES,
    generate_reference_images,
)

__all__ = [
    "GENERATE_REFERENCE_IMAGES",
    "generate_reference_images",
]
