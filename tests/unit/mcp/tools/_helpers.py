"""Shared test helpers for MCP tool unit tests."""

from __future__ import annotations

import asyncio

from film_pipeline.mcp.tools import create_film_project, set_active_project


def _make_active_project(project_id: str) -> None:
    asyncio.run(create_film_project({"project_id": project_id}))
    asyncio.run(set_active_project({"project_ref": project_id}))
