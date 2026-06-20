"""MCP server orchestration: registry, project registry, dispatch."""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
from dataclasses import dataclass, field
from typing import Any

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
            return MCPResponse(success=True, request_id=envelope.request_id, data=data)  # type: ignore[arg-type]
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


async def handle_jsonrpc(server: MCPServer, request: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC request for the MCP stdio transport."""
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params", {})
    if not isinstance(method, str):
        return _jsonrpc_error(request_id, -32600, "Invalid request: missing method.")
    if not isinstance(params, dict):
        params = {}

    if method == "initialize":
        return _jsonrpc_success(
            request_id,
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "film-pipeline-mcp",
                    "version": "0.2.0",
                },
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return _jsonrpc_success(request_id, {})
    if method == "tools/list":
        tools = [
            {
                "name": item["name"],
                "description": item["description"],
                "inputSchema": item["input_schema"],
            }
            for item in server.catalog()
        ]
        return _jsonrpc_success(request_id, {"tools": tools})
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(tool_name, str):
            return _jsonrpc_error(request_id, -32602, "tools/call requires string param 'name'.")
        if not isinstance(arguments, dict):
            return _jsonrpc_error(
                request_id, -32602, "tools/call requires object param 'arguments'."
            )
        tool_response = await server.call(tool_name, arguments)
        if not tool_response.success:
            error = tool_response.error
            message = error.message if error is not None else "Tool call failed."
            return _jsonrpc_error(request_id, -32000, message)
        structured = tool_response.data if isinstance(tool_response.data, dict) else {}
        is_error = bool(isinstance(structured, dict) and structured.get("ok") is False)
        return _jsonrpc_success(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(structured, default=str),
                    }
                ],
                "structuredContent": structured,
                "isError": is_error,
            },
        )
    return _jsonrpc_error(request_id, -32601, f"Method not found: {method}")


def main() -> int:
    """Run a minimal stdio MCP server."""
    from film_pipeline.app.bootstrap import validate_environment

    issues = validate_environment()
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1

    server = MCPServer()
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    while True:
        message = _read_message(stdin)
        if message is None:
            return 0
        response = asyncio.run(handle_jsonrpc(server, message))
        if response is not None:
            _write_message(stdout, response)


def _opt_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _jsonrpc_success(request_id: object, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: object, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _read_message(stream: Any) -> dict[str, Any] | None:
    content_length: int | None = None
    while True:
        line = stream.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        header = line.decode("utf-8").strip()
        if header.lower().startswith("content-length:"):
            value = header.split(":", 1)[1].strip()
            content_length = int(value)
    if content_length is None:
        raise ValueError("Missing Content-Length header.")
    body = stream.read(content_length)
    if not body:
        return None
    raw: Any = json.loads(body.decode("utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Expected JSON object request.")
    return raw


def _write_message(stream: Any, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    stream.write(header)
    stream.write(body)
    stream.flush()


if __name__ == "__main__":
    raise SystemExit(main())
