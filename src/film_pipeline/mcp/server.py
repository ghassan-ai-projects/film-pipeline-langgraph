"""MCP server orchestration: registry, project registry, dispatch."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field

from film_pipeline.mcp.contract import ToolRegistry, make_registry
from film_pipeline.mcp.envelope import RequestEnvelope, new_envelope
from film_pipeline.mcp.errors import MCPError, MCPErrorCode, MCPResponse
from film_pipeline.mcp.resolution import (
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
        try:
            reg = self.tools.get(tool_name)
        except KeyError:
            return MCPResponse(
                success=False,
                request_id=envelope.request_id,
                error=MCPError(
                    code=MCPErrorCode.UNKNOWN_TOOL,
                    message=f"Unknown tool: {tool_name}",
                ),
            )

        if reg.contract.mutates_state and envelope.project_ref:
            try:
                project = self.projects.resolve_or_raise(envelope.project_ref)
                envelope = RequestEnvelope(
                    request_id=envelope.request_id,
                    project_ref=envelope.project_ref,
                    resolved_project_id=project.project_id,
                    active_phase=envelope.active_phase,
                    user_intent=envelope.user_intent,
                    requires_confirmation=envelope.requires_confirmation,
                    actor_id=envelope.actor_id,
                    actor_type=envelope.actor_type,
                    received_at=envelope.received_at,
                )
                self.active_project_id = project.project_id
            except AmbiguousProjectError as exc:
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
            except KeyError as exc:
                return MCPResponse(
                    success=False,
                    request_id=envelope.request_id,
                    error=MCPError(code=MCPErrorCode.UNKNOWN_PROJECT, message=str(exc)),
                )

        new_args: dict[str, object] = {**arguments, "_envelope": envelope}
        handler = reg.handler
        try:
            if inspect.iscoroutinefunction(handler):
                data: object = await handler(new_args)
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


def _opt_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
