"""Compatibility checks for the lazy MCP tool export surface."""

from __future__ import annotations

import film_pipeline.mcp.tools as tools
from film_pipeline.mcp.registry import register_all_tools
from film_pipeline.mcp.tools.bibles import generate_shot_bible
from film_pipeline.mcp.tools.generation import plan_generation_batch
from film_pipeline.mcp.tools.reference_generation import generate_reference_images


def test_facade_preserves_tool_callable_identity_and_registry() -> None:
    assert tools.register_all_tools is register_all_tools
    assert tools.generate_shot_bible is generate_shot_bible
    assert tools.plan_generation_batch is plan_generation_batch
    assert tools.generate_reference_images is generate_reference_images
