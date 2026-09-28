"""What dispatch hands a tool handler, instead of the handler fetching it.

See `docs/modularity-improvements/01-one-dispatch-path.md`. This lives under
`mcp/tools/` rather than at the `mcp` root because the type alias
`contract.ToolHandler` mentions it at runtime: from the root, importing it
would make `mcp` depend on a module the tool subpackages also reach, which is
the `mcp -> tools -> mcp` cycle Enola reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolContext:
    """The dependencies one tool call needs, resolved by dispatch.

    `runtime` is the process runtime dispatch resolved — once, rather than 61
    times across the tool modules. `project_id` is the project this request acts
    on, or `None` when the tool declares it does not need one, so a handler reads
    the precondition's *result* instead of testing for it. `envelope` carries the
    request id and actor for audit.

    `args` deliberately stays a plain dict at this step: typing it per tool is doc
    04's slice, and doing both at once would conflate "where does the runtime come
    from" with "what shape are the arguments".

    It carries no `project_state()` helper: `helpers.require_project_state` already
    owns "the project's state, or a raise", and a second method for the same rule is
    the duplication this program keeps removing. Adding one here also dragged
    `filmspec` and `operations.errors` into `contract`, which sits at the `mcp`
    package root and closed an `mcp -> tools -> mcp` cycle Enola reports.
    """

    runtime: Any
    project_id: str | None
    envelope: Any


__all__ = ["ToolContext"]
