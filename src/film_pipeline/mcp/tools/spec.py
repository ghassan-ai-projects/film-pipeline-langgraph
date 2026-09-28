"""What a tool declares about itself: its handler shape and its arguments.

These live beside `ToolContext` under `mcp/tools/` because a tool module needs
them to declare its own spec:

    from film_pipeline.mcp.tools.spec import ToolArgs, ToolSpec

    class ApprovePhaseArgs(ToolArgs):
        confirmed: bool = False

    APPROVE_PHASE = ToolSpec(...)

`mcp/contract.py` — which holds the registry that consumes specs — is at the
`mcp` package root, and `mcp/__init__` imports it. Since every tool module
imports `contract` to declare itself, any import *from* `contract` *to* a
`mcp/tools/` module closes `mcp -> tools -> mcp`. Enola reports it, and the
top-level `test_package_acyclicity` guard cannot see it because it compares
top-level packages. Keeping the declaration types here, with the tools that use
them, is what keeps the edge one-way.

See `docs/modularity-improvements/04-the-mcp-contract-is-declared-not-delivered.md`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from film_pipeline.mcp.tools.context import ToolContext


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
    requires_active_project: bool = False
    creates_checkpoint: bool = False
    idempotency_key_field: str | None = None


ToolHandler = (
    Callable[[ToolContext, dict[str, Any]], Awaitable[dict[str, Any]]]
    | Callable[[ToolContext, dict[str, Any]], dict[str, Any]]
    | Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
    | Callable[[dict[str, Any]], dict[str, Any]]
)


class ToolArgs(BaseModel):
    """Base for a tool's argument model.

    ## Why a model and not ``args.get(...)``

    `docs/modularity-improvements/04` measured the MCP boundary as the one
    boundary the architecture calls the product surface, and the one with raw
    dicts on both sides: 75 tools with 0 input schemas, and 86 `args.get(...)`
    calls with ad-hoc coercion (`bool(args.get("confirmed"))`,
    `str(args.get("note", ""))`). AGENTS.md states the rule it breaks — "Pydantic
    v2 for all schemas (never raw dicts across boundaries)".

    `extra="forbid"` is deliberate, and it is the same experiment that produced
    the schemas round's 96-failure work list: it makes an unknown argument a
    typed error instead of a silent no-op, so the first failing run enumerates
    every caller sending something no handler reads.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    confirmed: bool | None = Field(
        default=None,
        description=(
            "Required to be true for tools that ask for confirmation; consumed by "
            "dispatch before the handler runs."
        ),
    )
    project_ref: str | None = Field(
        default=None,
        description=(
            "Project to act on for this call only, leaving the active project "
            "unchanged; consumed by dispatch."
        ),
    )


@dataclass(frozen=True)
class ToolSpec:
    """One tool's declaration, next to its handler.

    The tool list used to be declared three times — `registry.py`'s
    `_register(...)` calls, `tools/__init__.py`'s `_TOOL_MODULES` lazy facade, and
    its `.pyi` stub — and adding a tool meant editing all three. A spec puts the
    declaration where the handler is, so `registry.py` becomes a list of specs and
    the facade/stub are derived rather than maintained.
    """

    name: str
    group: ToolGroup
    description: str
    args: type[ToolArgs]
    handler: ToolHandler
    mutates: bool = False
    confirm: bool = False
    active_project: bool = False
    checkpoint: bool = False
    output_schema: dict[str, Any] = field(default_factory=dict)

    def contract(self) -> Any:
        """The `ToolContract` this spec publishes, with its real input schema."""
        return ToolContract(
            name=self.name,
            description=self.description,
            group=self.group,
            input_schema=self.args.model_json_schema(),
            output_schema=self.output_schema,
            mutates_state=self.mutates,
            requires_confirmation=self.confirm,
            requires_active_project=self.active_project,
            creates_checkpoint=self.checkpoint,
        )

    def validate(self, args: dict[str, Any]) -> ToolArgs:
        """Parse request arguments into the typed model.

        Raises `pydantic.ValidationError`, which dispatch maps to a
        `VALIDATION_ERROR` response — so a malformed call is a typed refusal
        rather than a `KeyError` deep inside a handler.
        """
        return self.args.model_validate(args)


__all__ = ["ToolArgs", "ToolContext", "ToolContract", "ToolGroup", "ToolHandler", "ToolSpec"]
