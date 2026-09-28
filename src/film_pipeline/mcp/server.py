"""MCP server orchestration: registry, project registry, dispatch."""

from __future__ import annotations

import inspect
import os
from dataclasses import dataclass, field, replace
from typing import Any, cast

from pydantic import ValidationError

from film_pipeline.filmspec import NO_ACTIVE_PROJECT
from film_pipeline.mcp._stdio_transport import (
    _read_message as _read_message,
)
from film_pipeline.mcp._stdio_transport import (
    _serve_stdio,
    _warn_bootstrap_issues,
)
from film_pipeline.mcp._stdio_transport import (
    _write_message as _write_message,
)
from film_pipeline.mcp._stdio_transport import (
    handle_jsonrpc as handle_jsonrpc,
)
from film_pipeline.mcp.contract import (
    ToolRegistration,
    ToolRegistry,
    make_registry,
)
from film_pipeline.mcp.envelope import RequestEnvelope, new_envelope
from film_pipeline.mcp.errors import MCPError, MCPErrorCode, MCPResponse
from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolHandler
from film_pipeline.operations.errors import ProjectNotFoundError
from film_pipeline.projects import (
    AmbiguousProjectError,
    ProjectRecord,
    ProjectRegistry,
)


@dataclass
class MCPServer:
    """The MCP server: registry + project registry + dispatcher."""

    tools: ToolRegistry = field(default_factory=make_registry)
    projects: ProjectRegistry = field(default_factory=ProjectRegistry)

    async def call(
        self,
        tool_name: str,
        arguments: dict[str, object],
        *,
        actor_id: str | None = None,
        actor_type: str = "human",
    ) -> MCPResponse:
        """Dispatch a tool call through project resolution and the tool handler."""
        envelope = new_envelope(
            project_ref=_opt_str(arguments.get("project_ref")),
            actor_id=actor_id,
            actor_type=actor_type,
        )
        resolved = self._resolve_tool_and_project(tool_name, envelope)
        if isinstance(resolved, MCPResponse):
            return resolved
        reg, resolved_envelope = resolved
        confirmation = self._check_confirmation(reg, tool_name, arguments, resolved_envelope)
        if confirmation is not None:
            return confirmation
        missing_project = self._check_active_project(reg, resolved_envelope)
        if missing_project is not None:
            return missing_project
        return await self._dispatch_handler(reg, arguments, resolved_envelope)

    def _resolve_tool_and_project(
        self,
        tool_name: str,
        envelope: RequestEnvelope,
    ) -> MCPResponse | tuple[ToolRegistration, RequestEnvelope]:
        """Resolve the tool registration and project ref into a pair or an early error."""
        reg = self._registration_for(tool_name, envelope)
        if isinstance(reg, MCPResponse):
            return reg
        resolved = self._resolve_project_ref(envelope)
        if isinstance(resolved, MCPResponse):
            return resolved
        return reg, resolved

    def _registration_for(
        self,
        tool_name: str,
        envelope: RequestEnvelope,
    ) -> ToolRegistration | MCPResponse:
        """Look up the tool registration; UNKNOWN_TOOL response on a miss."""
        try:
            return self.tools.get(tool_name)
        except KeyError:
            return MCPResponse(
                success=False,
                request_id=envelope.request_id,
                error=MCPError(
                    code=MCPErrorCode.UNKNOWN_TOOL,
                    message=f"Unknown tool: {tool_name}",
                ),
            )

    def _resolve_project_ref(
        self,
        envelope: RequestEnvelope,
    ) -> MCPResponse | RequestEnvelope:
        """Resolve the request's project, explicit ref first, then the session's."""
        if not envelope.project_ref:
            # No explicit ref: fall back to the active project. It is read from
            # the runtime, which owns project state, rather than from a second
            # copy here — doc 01's slice 3. The server kept its own
            # `active_project_id` and reconciled the two after the fact with
            # `_auto_register_from_runtime`, whose own comment conceded that
            # "the server's ProjectRegistry is a separate in-memory structure".
            active = self._active_project_from_runtime()
            if active:
                return _resolved_envelope(envelope, active)
            return envelope
        try:
            project = self.projects.resolve_or_raise(envelope.project_ref)
        except AmbiguousProjectError as exc:
            return self._ambiguous_response(envelope, exc)
        except KeyError as exc:
            # Fall back: if the project exists in the runtime but not in
            # the server's registry, auto-register it. This fixes the gap
            # where create_film_project registers with the runtime but the
            # server's ProjectRegistry is a separate in-memory structure.
            return self._unknown_project_fallback(envelope, exc)
        return _resolved_envelope(envelope, project.project_id)

    def _ambiguous_response(
        self,
        envelope: RequestEnvelope,
        exc: AmbiguousProjectError,
    ) -> MCPResponse:
        """Shape an ambiguous project_ref into an AMBIGUOUS_PROJECT response."""
        return MCPResponse(
            success=False,
            request_id=envelope.request_id,
            error=MCPError(
                code=MCPErrorCode.AMBIGUOUS_PROJECT,
                message=str(exc),
                details={
                    "candidates": ", ".join(p.project_id for p in exc.candidates),
                },
            ),
        )

    def _unknown_project_fallback(
        self,
        envelope: RequestEnvelope,
        exc: KeyError,
    ) -> MCPResponse | RequestEnvelope:
        """Auto-register a runtime-known project; UNKNOWN_PROJECT otherwise."""
        pid = self._auto_register_from_runtime(envelope.project_ref)
        if pid is None:
            return MCPResponse(
                success=False,
                request_id=envelope.request_id,
                error=MCPError(code=MCPErrorCode.UNKNOWN_PROJECT, message=str(exc)),
            )
        return _resolved_envelope(envelope, pid)

    def _auto_register_from_runtime(self, project_ref: str | None) -> str | None:
        """Register a runtime-known project missing here; None when unknown everywhere."""
        if not project_ref:
            return None
        from film_pipeline.studio.runtime import get_runtime

        rt = get_runtime()
        rt_project = rt.get_project(project_ref)
        if rt_project is None:
            return None
        pid = str(rt_project.get("project_id", project_ref))
        record = ProjectRecord(
            project_id=pid,
            slug=str(rt_project.get("slug", pid)),
            title=str(rt_project.get("title", pid)),
        )
        self.projects.register(record)
        return pid

    def _check_active_project(
        self,
        registration: ToolRegistration,
        envelope: RequestEnvelope,
    ) -> MCPResponse | None:
        """Return a NO_ACTIVE_PROJECT response, or None when the precondition holds.

        The precondition — "is there a project to act on?" — was checked inside
        48 handlers with three wordings and five different emptiness tests
        (`if not active` and `if active is None` disagree on an empty dict).
        Declaring it on the contract and checking it once at dispatch means the
        condition has a single answer, and handlers state the requirement rather
        than re-deriving it.

        The envelope already carries the resolved project, so this needs no
        resolution work of its own.
        """
        if not registration.contract.requires_active_project:
            return None
        if envelope.resolved_project_id:
            return None
        return MCPResponse(
            success=False,
            request_id=envelope.request_id,
            error=MCPError(
                code=MCPErrorCode.NO_ACTIVE_PROJECT,
                message=NO_ACTIVE_PROJECT,
                details={"tool": registration.contract.name},
            ),
        )

    def _check_confirmation(
        self,
        registration: ToolRegistration,
        tool_name: str,
        arguments: dict[str, object],
        envelope: RequestEnvelope,
    ) -> MCPResponse | None:
        """Return a CONFIRMATION_REQUIRED response, or None when the gate passes."""
        if registration.contract.requires_confirmation and not arguments.get("confirmed"):
            return MCPResponse(
                success=False,
                request_id=envelope.request_id,
                error=MCPError(
                    code=MCPErrorCode.CONFIRMATION_REQUIRED,
                    message=(
                        f"Tool '{tool_name}' requires explicit confirmation. "
                        "Pass 'confirmed': true to proceed."
                    ),
                    details={"tool": tool_name},
                ),
            )
        return None

    async def _dispatch_handler(
        self,
        reg: ToolRegistration,
        arguments: dict[str, object],
        envelope: RequestEnvelope,
    ) -> MCPResponse:
        """Invoke the handler and shape result or failure into a response.

        Handlers come in two shapes while doc 01's migration is in flight:

        - `handler(ctx, args)` — the target. Dispatch builds the `ToolContext`, so
          the handler never resolves the runtime or the project itself.
        - `handler(args)` — the legacy shape, still receiving `"_envelope"` inside
          the argument dict. Deleted group by group; when the last one moves, this
          branch and the `"_envelope"` key both go.
        """

        handler = reg.handler
        # A tool declared with a `ToolSpec` validates its arguments first, so a
        # malformed call is a typed `VALIDATION_ERROR` rather than a `KeyError`
        # deep inside a handler (doc 04 slice 1). Tools registered the older way
        # have no spec and pass through unchanged.
        try:
            reg.validate(dict(arguments))
        except ValidationError as exc:
            return MCPResponse(
                success=False,
                request_id=envelope.request_id,
                error=MCPError(
                    code=MCPErrorCode.VALIDATION_ERROR,
                    message=(
                        f"Invalid arguments for '{reg.contract.name}': "
                        f"{exc.error_count()} error(s)."
                    ),
                    details={"tool": reg.contract.name, "errors": str(exc)},
                ),
            )
        new_args: dict[str, object] = {**arguments, "_envelope": envelope}
        # The union in `ToolHandler` admits both shapes, so mypy cannot narrow it
        # from a runtime signature check. `_accepts_context` just proved which
        # call this is; the cast states that.
        any_handler = cast("Any", handler)
        is_async = inspect.iscoroutinefunction(handler)
        try:
            if _accepts_context(handler):
                context = self._build_context(envelope)
                data: Any = (
                    await any_handler(context, dict(arguments))
                    if is_async
                    else any_handler(context, dict(arguments))
                )
            else:
                data = await any_handler(new_args) if is_async else any_handler(new_args)
            return MCPResponse(success=True, request_id=envelope.request_id, data=data)
        except MCPError as exc:
            return MCPResponse(success=False, request_id=envelope.request_id, error=exc)
        except ProjectNotFoundError as exc:
            # Handlers assert the active-project precondition instead of
            # checking it (`require_project_id`). A raise here means the
            # precondition did not actually hold, so it is reported with the
            # same code the dispatch check would have used.
            return MCPResponse(
                success=False,
                request_id=envelope.request_id,
                error=MCPError(
                    code=MCPErrorCode.NO_ACTIVE_PROJECT,
                    message=str(exc),
                ),
            )
        except Exception as exc:  # pragma: no cover — defensive
            return MCPResponse(
                success=False,
                request_id=envelope.request_id,
                error=MCPError(code=MCPErrorCode.INTERNAL_ERROR, message=str(exc)),
            )

    def _build_context(self, envelope: RequestEnvelope) -> ToolContext:
        """Build the per-request context dispatch hands a context-style handler.

        The runtime is resolved once here rather than 61 times across the tool
        modules, and the resolved project is read from the envelope instead of
        being smuggled through the argument dict.
        """
        from film_pipeline.studio.runtime import get_runtime

        return ToolContext(
            runtime=get_runtime(),
            project_id=envelope.resolved_project_id,
            envelope=envelope,
        )

    def catalog(self) -> list[dict[str, object]]:
        return self.tools.catalog()

    def register_project(self, record: ProjectRecord) -> None:
        self.projects.register(record)

    def _active_project_from_runtime(self) -> str | None:
        """The runtime's active project id, or ``None`` when there is none.

        `StudioRuntime` owns project state, so it owns "active". Reading it here
        keeps one owner: a mutating call through the runtime and a
        `set_active_project` tool now move the same value, where they used to
        move two.
        """
        from film_pipeline.studio.runtime import get_runtime

        active = get_runtime().get_active()
        if active is None:
            return None
        return str(active.get("project_id", "")) or None


def _accepts_context(handler: ToolHandler) -> bool:
    """True when ``handler`` is declared as ``(ctx, args)`` rather than ``(args)``.

    Read from the signature rather than a registry flag: the handler's own
    declaration is the single source of truth for how it wants to be called, and
    a flag would be a second place to forget. A handler whose first parameter is
    named ``ctx`` is context-style; the name is the declaration.
    """
    try:
        parameters = list(inspect.signature(handler).parameters)
    except (TypeError, ValueError):  # pragma: no cover - builtins and C callables
        return False
    return bool(parameters) and parameters[0] == "ctx"


def main() -> int:
    """Run a minimal stdio MCP server.

    Bootstrap validation logs warnings to stderr but never prevents the
    server from starting — individual tool calls will fail with actionable
    errors if their required resources are missing.
    """
    from film_pipeline.studio.bootstrap import validate_environment

    if not os.getenv("FILM_PIPELINE_NO_PERSIST"):
        os.environ.setdefault("FILM_PIPELINE_PERSIST_STATE", "1")

    # Stdio transport owns stderr's cleanliness; persistent runs also retain a
    # file log. The file handler is placed under the configured runtime root when
    # one is set. Note this is NOT always the root `StudioRuntime` will use: with
    # neither `FILM_PIPELINE_RUNTIME_ROOT` nor persistence enabled the runtime
    # falls back to a throwaway tempdir. `configure_logging` tolerates `None` and
    # adds the file handler only when it has a root.
    from film_pipeline.studio._persistence import runtime_root_from_config
    from film_pipeline.studio.logging_setup import configure_logging

    configure_logging(runtime_root_from_config())

    issues = validate_environment()
    if issues:
        _warn_bootstrap_issues(issues)

    return _serve_stdio(MCPServer())


def _resolved_envelope(envelope: RequestEnvelope, project_id: str) -> RequestEnvelope:
    """Copy the envelope with resolved_project_id set; every other field verbatim."""
    return replace(envelope, resolved_project_id=project_id)


def _opt_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


if __name__ == "__main__":
    raise SystemExit(main())
