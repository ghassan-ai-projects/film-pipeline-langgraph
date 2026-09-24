"""JSON-RPC stdio transport for the MCP server.

Routes JSON-RPC requests onto :class:`~film_pipeline.mcp.server.MCPServer`,
frames messages with Content-Length headers, and runs the stdio serve loop.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from film_pipeline.mcp.server import MCPServer


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
        return _jsonrpc_success(request_id, _initialize_result())
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
        return await _serve_tools_call(server, request_id, params)
    return _jsonrpc_error(request_id, -32601, f"Method not found: {method}")


async def _serve_tools_call(
    server: MCPServer,
    request_id: object,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Run one tools/call request and map the MCP response onto JSON-RPC framing."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    if not isinstance(tool_name, str):
        return _jsonrpc_error(request_id, -32602, "tools/call requires string param 'name'.")
    if not isinstance(arguments, dict):
        return _jsonrpc_error(request_id, -32602, "tools/call requires object param 'arguments'.")
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


def _initialize_result() -> dict[str, Any]:
    """Static capabilities payload for the initialize handshake."""
    return {
        "protocolVersion": "2025-03-26",
        "capabilities": {
            "tools": {"listChanged": False},
        },
        "serverInfo": {
            "name": "film-pipeline-mcp",
            "version": "0.3.0",
        },
    }


def _jsonrpc_success(request_id: object, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: object, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _warn_bootstrap_issues(issues: list[str]) -> None:
    """Print bootstrap warnings to stderr without blocking startup."""
    print("[film-pipeline-mcp] Bootstrap warnings:", file=sys.stderr)
    for issue in issues:
        print(f"  - {issue}", file=sys.stderr)
    print(
        "[film-pipeline-mcp] Server starting anyway — "
        "tools that require missing resources will return errors.",
        file=sys.stderr,
    )


def _serve_stdio(server: MCPServer) -> int:
    """Serve JSON-RPC over stdio until stdin closes; returns the process exit code."""
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    print("[film-pipeline-mcp] Server ready, waiting for JSON-RPC on stdin.", file=sys.stderr)
    sys.stderr.flush()

    while True:
        message = _read_message(stdin)
        if message is None:
            print("[film-pipeline-mcp] stdin closed, exiting.", file=sys.stderr)
            return 0
        response = asyncio.run(handle_jsonrpc(server, message))
        if response is not None:
            _write_message(stdout, response)


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
    header = f"Content-Length: {len(body)}\r\n\r\n".encode()
    stream.write(header)
    stream.write(body)
    stream.flush()
