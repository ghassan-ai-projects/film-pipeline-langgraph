"""Stdio JSON-RPC transport for talking to the MCP server subprocess."""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path
from typing import Any


class MCPProcessTransport:
    """Owns the MCP server subprocess and framed JSON-RPC request/response IO."""

    def __init__(self, command: list[str] | None = None) -> None:
        self._command = command or self._default_command()
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._request_id = 0
        self._ensure_started()

    @staticmethod
    def _default_command() -> list[str]:
        return [
            "uv",
            "run",
            "--python",
            "3.12",
            "--group",
            "dev",
            "python",
            "-m",
            "film_pipeline.mcp.server",
        ]

    def _ensure_started(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        self._proc = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path.cwd()),
        )

    def _call(self, method: str, params: dict[str, object] | None = None) -> dict[str, Any]:
        with self._lock:
            self._ensure_started()
            if (
                self._proc is None or self._proc.stdin is None or self._proc.stdout is None
            ):  # pragma: no cover
                raise RuntimeError("MCP server subprocess is not available.")
            self._request_id += 1
            request: dict[str, object] = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
            }
            if params:
                request["params"] = params
            body = json.dumps(request)
            self._proc.stdin.write(f"Content-Length: {len(body)}\r\n\r\n{body}")
            self._proc.stdin.flush()
            return self._read_response(self._request_id)

    def _read_response(self, expected_id: int) -> dict[str, Any]:
        if self._proc is None or self._proc.stdout is None:  # pragma: no cover
            raise RuntimeError("MCP server subprocess is not available.")
        content_length: int | None = None
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP server closed stdout before response")
            if line in {"\r\n", "\n"}:
                break
            header = line.strip()
            if header.lower().startswith("content-length:"):
                content_length = int(header.split(":", 1)[1].strip())
        if content_length is None:  # pragma: no cover
            raise RuntimeError("Missing Content-Length header in MCP response")
        raw = self._proc.stdout.read(content_length)
        response = json.loads(raw)
        if response.get("id") != expected_id:  # pragma: no cover
            raise RuntimeError(f"MCP response id mismatch: {response.get('id')} != {expected_id}")
        if "error" in response:
            raise RuntimeError(response["error"].get("message", "Unknown MCP error"))
        result = response.get("result", {})
        if not isinstance(result, dict):  # pragma: no cover
            raise RuntimeError("MCP result is not an object")
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        return result

    def _tool(self, tool_name: str, arguments: dict[str, object]) -> dict[str, Any]:
        return self._call("tools/call", {"name": tool_name, "arguments": arguments})

    def _set_active(self, project_id: str | None) -> None:
        if project_id:
            self._tool("set_active_project", {"project_ref": project_id})

    def close(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover
                self._proc.kill()

    def __del__(self) -> None:  # pragma: no cover
        self.close()
