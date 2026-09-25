"""MCP compatibility imports retain project-resolution identity."""

from __future__ import annotations

from film_pipeline import projects
from film_pipeline.mcp import resolution as mcp_resolution


def test_mcp_resolution_names_are_project_names() -> None:
    assert mcp_resolution.ProjectRecord is projects.ProjectRecord
    assert mcp_resolution.ProjectRegistry is projects.ProjectRegistry
    assert mcp_resolution.ResolutionResult is projects.ResolutionResult
    assert mcp_resolution.AmbiguousProjectError is projects.AmbiguousProjectError
