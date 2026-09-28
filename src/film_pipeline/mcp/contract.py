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

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from film_pipeline.mcp.tools.spec import ToolContract, ToolGroup

ToolHandler = Callable[..., Any]


@dataclass
class ToolRegistration:
    """A tool registered with the server, pairing a contract with a handler.

    `spec` is set when the tool declared itself with a `ToolSpec` (doc 04's
    slice 1). Dispatch validates arguments through it, so a tool declared with a
    spec gets typed args and a real `input_schema`; one registered the older way
    has no spec and dispatch passes its arguments through unchanged. The register
    path is removed once every tool declares a spec.
    """

    contract: ToolContract
    handler: ToolHandler
    spec: Any = None

    def validate(self, args: dict[str, Any]) -> Any:
        """Return the parsed args model, or `None` when this tool has no spec."""
        if self.spec is None:
            return None
        return self.spec.validate(args)


class ToolRegistry:
    """In-memory registry mapping tool names to registrations."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolRegistration] = {}

    def register(
        self,
        contract: ToolContract,
        handler: ToolHandler,
        spec: Any = None,
    ) -> None:
        if contract.name in self._tools:
            raise ValueError(f"Tool already registered: {contract.name}")
        self._tools[contract.name] = ToolRegistration(contract=contract, handler=handler, spec=spec)

    def register_spec(self, spec: Any) -> None:
        """Register a tool from its own declaration.

        The target path: the spec carries the contract *and* the args model, so
        there is nothing to keep in step between a `_register(...)` call and the
        handler's signature.
        """
        self.register(spec.contract(), spec.handler, spec)

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
