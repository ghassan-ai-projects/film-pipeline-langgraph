"""TUI gateway implementations."""

from __future__ import annotations

from film_pipeline.tui.gateways.inprocess import InProcessStudioGateway
from film_pipeline.tui.gateways.mcp import MCPStudioGateway, default_gateway

__all__ = ["InProcessStudioGateway", "MCPStudioGateway", "default_gateway"]
