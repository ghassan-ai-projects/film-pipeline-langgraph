"""MCP operator surface: tool registration, dispatch, and request envelopes.

OpenClaw controls the studio through MCP tools. LangGraph runs behind this
boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from film_pipeline.mcp.contract import ToolRegistry
    from film_pipeline.mcp.envelope import RequestEnvelope, new_envelope
    from film_pipeline.mcp.errors import MCPError, MCPErrorCode, MCPResponse
    from film_pipeline.mcp.tools.context import ToolContext
    from film_pipeline.mcp.tools.spec import ToolContract, ToolGroup, ToolHandler
    from film_pipeline.projects import (
        AmbiguousProjectError,
        ProjectRecord,
        ProjectRegistry,
        ResolutionResult,
    )

__all__ = [
    "AmbiguousProjectError",
    "MCPError",
    "MCPErrorCode",
    "MCPResponse",
    "MCPServer",
    "ProjectRecord",
    "ProjectRegistry",
    "RequestEnvelope",
    "ResolutionResult",
    "ToolContext",
    "ToolContract",
    "ToolGroup",
    "ToolHandler",
    "ToolRegistry",
    "new_envelope",
]


_LAZY_ATTRS: dict[str, str] = {
    "AmbiguousProjectError": "film_pipeline.projects",
    "MCPError": "film_pipeline.mcp.errors",
    "MCPErrorCode": "film_pipeline.mcp.errors",
    "MCPResponse": "film_pipeline.mcp.errors",
    "MCPServer": "film_pipeline.mcp.server",
    "ProjectRecord": "film_pipeline.projects",
    "ProjectRegistry": "film_pipeline.projects",
    "RequestEnvelope": "film_pipeline.mcp.envelope",
    "ResolutionResult": "film_pipeline.projects",
    "ToolContract": "film_pipeline.mcp.tools.spec",
    "ToolContext": "film_pipeline.mcp.tools.context",
    "ToolGroup": "film_pipeline.mcp.tools.spec",
    "ToolHandler": "film_pipeline.mcp.tools.spec",
    "ToolRegistry": "film_pipeline.mcp.contract",
    "new_envelope": "film_pipeline.mcp.envelope",
}


def __getattr__(name: str) -> object:
    """Resolve a facade name on first access rather than at import time."""
    module_path = _LAZY_ATTRS.get(name)
    if module_path is None:
        raise AttributeError(name)
    import importlib

    return getattr(importlib.import_module(module_path), name)
