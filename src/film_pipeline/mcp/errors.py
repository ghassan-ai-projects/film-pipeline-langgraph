"""MCP error types and response shaping."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class MCPErrorCode(StrEnum):
    """Stable machine-readable MCP error codes."""

    AMBIGUOUS_PROJECT = "ambiguous_project"
    UNKNOWN_PROJECT = "unknown_project"
    UNKNOWN_TOOL = "unknown_tool"
    VALIDATION_ERROR = "validation_error"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    INTERNAL_ERROR = "internal_error"
    BUDGET_EXCEEDED = "budget_exceeded"
    PROVIDER_BLOCKED = "provider_blocked"
    CONFIRMATION_REQUIRED = "confirmation_required"


@dataclass
class MCPError(Exception):
    """A structured MCP error response."""

    code: MCPErrorCode
    message: str
    details: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, str]:
        out = {"code": self.code.value, "message": self.message}
        out.update(self.details)
        return out


@dataclass
class MCPResponse:
    """Structured MCP response envelope."""

    success: bool
    data: dict[str, object] | list[object] | str | int | float | bool | None = None
    error: MCPError | None = None
    request_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "success": self.success,
            "request_id": self.request_id,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
        }
