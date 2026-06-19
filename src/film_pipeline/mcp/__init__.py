"""MCP operator surface: tool registration, dispatch, and request envelopes.

OpenClaw controls the studio through MCP tools. LangGraph runs behind this
boundary.
"""

from __future__ import annotations

from film_pipeline.mcp.contract import ToolContract, ToolGroup, ToolHandler, ToolRegistry
from film_pipeline.mcp.envelope import RequestEnvelope, new_envelope
from film_pipeline.mcp.errors import MCPError, MCPErrorCode, MCPResponse
from film_pipeline.mcp.resolution import (
    AmbiguousProjectError,
    ProjectRecord,
    ProjectRegistry,
    ResolutionResult,
)
from film_pipeline.mcp.server import MCPServer

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
    "ToolContract",
    "ToolGroup",
    "ToolHandler",
    "ToolRegistry",
    "new_envelope",
]
