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

from film_pipeline.filmspec import NO_ACTIVE_PROJECT
from film_pipeline.operations.errors import ProjectNotFoundError


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

    It carries `project_state()` because migrating a handler means replacing its
    `require_project_state(args)` call, and the context already holds the resolved
    project — so this is where the rule belongs now, not a duplicate of it. The
    earlier placement (at the `mcp` package root) could not have it: the method
    imports `filmspec` and `operations.errors`, which made `mcp.contract` depend on
    modules the tool subpackages also reach, closing an `mcp -> tools -> mcp` cycle.
    From `mcp/tools/`, that import is internal to the subpackage Enola treats as one
    node, so the cycle does not form.
    """

    runtime: Any
    project_id: str | None
    envelope: Any

    def project_state(self) -> dict[str, Any]:
        """Return the context project's live state.

        Raises `ProjectNotFoundError` when no project resolved, mirroring
        `helpers.require_project_state` (which this replaces at migrated call
        sites): dispatch checks `requires_active_project` before the handler runs,
        so reaching here without one is a contract bug rather than a user error.
        """

        if self.project_id is None:
            raise ProjectNotFoundError(NO_ACTIVE_PROJECT)
        state: dict[str, Any] | None = self.runtime.get_project(self.project_id)
        if state is None:
            raise ProjectNotFoundError(f"Project '{self.project_id}' is not loaded.")
        return state
