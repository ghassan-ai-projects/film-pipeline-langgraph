"""MCP server orchestration: registry, project registry, dispatch."""

from __future__ import annotations

import inspect
import os
from dataclasses import dataclass, field, replace
from typing import Any

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
    ToolHandler,
    ToolRegistration,
    ToolRegistry,
    make_registry,
)
from film_pipeline.mcp.envelope import RequestEnvelope, new_envelope
from film_pipeline.mcp.errors import MCPError, MCPErrorCode, MCPResponse
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
    active_project_id: str | None = None

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
        return await self._dispatch_handler(reg.handler, arguments, resolved_envelope)

    def _resolve_tool_and_project(
        self,
        tool_name: str,
        envelope: RequestEnvelope,
    ) -> MCPResponse | tuple[ToolRegistration, RequestEnvelope]:
        """Resolve the tool registration and project ref into a pair or an early error."""
        reg = self._registration_for(tool_name, envelope)
        if isinstance(reg, MCPResponse):
            return reg
        resolved = self._resolve_project_ref(reg, envelope)
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
        reg: ToolRegistration,
        envelope: RequestEnvelope,
    ) -> MCPResponse | RequestEnvelope:
        """Resolve envelope.project_ref against the registry when present."""
        if not envelope.project_ref:
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
            return self._unknown_project_fallback(reg, envelope, exc)
        envelope = _resolved_envelope(envelope, project.project_id)
        if reg.contract.mutates_state:
            self.active_project_id = project.project_id
        return envelope

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
        reg: ToolRegistration,
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
        if reg.contract.mutates_state:
            self.active_project_id = pid
        return _resolved_envelope(envelope, pid)

    def _auto_register_from_runtime(self, project_ref: str | None) -> str | None:
        """Register a runtime-known project missing here; None when unknown everywhere."""
        if not project_ref:
            return None
        from film_pipeline.app.runtime import get_runtime

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
        handler: ToolHandler,
        arguments: dict[str, object],
        envelope: RequestEnvelope,
    ) -> MCPResponse:
        """Invoke the handler (sync or async) and shape result or failure into a response."""
        new_args: dict[str, object] = {**arguments, "_envelope": envelope}
        try:
            if inspect.iscoroutinefunction(handler):
                data: Any = await handler(new_args)
            else:
                data = handler(new_args)
            return MCPResponse(success=True, request_id=envelope.request_id, data=data)
        except MCPError as exc:
            return MCPResponse(success=False, request_id=envelope.request_id, error=exc)
        except Exception as exc:  # pragma: no cover — defensive
            return MCPResponse(
                success=False,
                request_id=envelope.request_id,
                error=MCPError(code=MCPErrorCode.INTERNAL_ERROR, message=str(exc)),
            )

    def catalog(self) -> list[dict[str, object]]:
        return self.tools.catalog()

    def register_project(self, record: ProjectRecord) -> None:
        self.projects.register(record)
        if self.active_project_id is None:
            self.active_project_id = record.project_id


def main() -> int:
    """Run a minimal stdio MCP server.

    Bootstrap validation logs warnings to stderr but never prevents the
    server from starting — individual tool calls will fail with actionable
    errors if their required resources are missing.
    """
    from film_pipeline.app.bootstrap import validate_environment

    if not os.getenv("FILM_PIPELINE_NO_PERSIST"):
        os.environ.setdefault("FILM_PIPELINE_PERSIST_STATE", "1")

    # Stdio transport owns stderr's cleanliness; persistent runs also retain a
    # file log under the same runtime root used by StudioRuntime.
    from film_pipeline.app._persistence import configured_runtime_root
    from film_pipeline.app.logging_setup import configure_logging

    configure_logging(configured_runtime_root())

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
