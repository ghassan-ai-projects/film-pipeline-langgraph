"""MCP tool contracts and the registry that powers them.

Every tool exposes:

- name, description
- input schema (JSON Schema)
- output schema (JSON Schema)
- mutates_state flag
- requires_confirmation flag
- creates_checkpoint flag
- idempotency_key field (optional)

The registry stores these contracts and dispatches calls to handlers
implemented in ``film_pipeline.mcp.tools.*``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ToolGroup(StrEnum):
    """High-level grouping for tools."""

    PROJECT = "project"
    INTAKE = "intake"
    STATE = "state"
    REVIEW = "review"
    ARTIFACT = "artifact"
    VALIDATION = "validation"
    GENERATION = "generation"
    KB = "kb"
    CHECKPOINT = "checkpoint"
    AUDIT = "audit"
    PROVIDER = "provider"
    CONFIG = "config"
    COVERAGE = "coverage"
    ASSEMBLY = "assembly"
    OPERATOR = "operator"


@dataclass(frozen=True)
class ToolContract:
    """Formal contract for one MCP tool."""

    name: str
    description: str
    group: ToolGroup
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    mutates_state: bool = False
    requires_confirmation: bool = False
    creates_checkpoint: bool = False
    idempotency_key_field: str | None = None


ToolHandler = (
    Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
    | Callable[[dict[str, Any]], dict[str, Any]]
)


@dataclass
class ToolRegistration:
    """A tool registered with the server, pairing a contract with a handler."""

    contract: ToolContract
    handler: ToolHandler


class ToolRegistry:
    """In-memory registry mapping tool names to registrations."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolRegistration] = {}

    def register(self, contract: ToolContract, handler: ToolHandler) -> None:
        if contract.name in self._tools:
            raise ValueError(f"Tool already registered: {contract.name}")
        self._tools[contract.name] = ToolRegistration(contract=contract, handler=handler)

    def get(self, name: str) -> ToolRegistration:
        if name not in self._tools:
            raise KeyError(f"Unknown MCP tool: {name}")
        return self._tools[name]

    def list_by_group(self, group: ToolGroup) -> list[str]:
        return [name for name, reg in self._tools.items() if reg.contract.group == group]

    def all_names(self) -> list[str]:
        return sorted(self._tools)

    def catalog(self) -> list[dict[str, Any]]:
        """Return a serializable catalog for discovery via MCP."""
        out: list[dict[str, Any]] = []
        for name in self.all_names():
            reg = self._tools[name]
            c = reg.contract
            out.append(
                {
                    "name": c.name,
                    "description": c.description,
                    "group": c.group.value,
                    "mutates_state": c.mutates_state,
                    "requires_confirmation": c.requires_confirmation,
                    "creates_checkpoint": c.creates_checkpoint,
                    "idempotency_key_field": c.idempotency_key_field,
                    "input_schema": c.input_schema,
                    "output_schema": c.output_schema,
                }
            )
        return out


def make_registry() -> ToolRegistry:
    """Build the canonical MCP tool registry.

    Importing this lazily avoids circular import problems at module load.
    """
    from film_pipeline.mcp.registry import register_all_tools

    registry = ToolRegistry()
    register_all_tools(registry)
    return registry
