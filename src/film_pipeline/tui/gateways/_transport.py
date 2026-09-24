"""Stdio JSON-RPC transport for talking to the MCP server subprocess."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import IO, Any


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
        """Launch the in-package MCP server with the running interpreter.

        Re-entering the environment through ``uv run`` made the gateway depend
        on an external ``uv`` binary and a writable uv cache just to start a
        module that ships with this package. The server has no dependency on
        the ``mcp`` extra, so the current interpreter can run it directly.
        """
        return [sys.executable, "-m", "film_pipeline.mcp.server"]

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

    def _live_pipes(self) -> tuple[IO[str], IO[str]]:
        proc = self._proc
        if proc is None or proc.stdin is None or proc.stdout is None:  # pragma: no cover
            raise RuntimeError("MCP server subprocess is not available.")
        return proc.stdin, proc.stdout

    def _call(self, method: str, params: dict[str, object] | None = None) -> dict[str, Any]:
        with self._lock:
            self._ensure_started()
            stdin, stdout = self._live_pipes()
            self._request_id += 1
            try:
                stdin.write(self._encode_request(self._request_id, method, params))
                stdin.flush()
            except (BrokenPipeError, OSError, ValueError) as exc:
                raise RuntimeError("MCP server closed stdin before request was sent") from exc
            return self._read_response(stdout, self._request_id)

    @staticmethod
    def _encode_request(request_id: int, method: str, params: dict[str, object] | None) -> str:
        request: dict[str, object] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params:
            request["params"] = params
        body = json.dumps(request)
        return f"Content-Length: {len(body)}\r\n\r\n{body}"

    def _read_response(self, stdout: IO[str], expected_id: int) -> dict[str, Any]:
        response = self._read_framed_message(stdout)
        self._reject_mismatched_id(response, expected_id)
        self._reject_rpc_error(response)
        return self._unwrap_result(response)

    @staticmethod
    def _read_framed_message(stdout: IO[str]) -> dict[str, Any]:
        content_length: int | None = None
        while True:
            line = stdout.readline()
            if not line:
                raise RuntimeError("MCP server closed stdout before response")
            if line in {"\r\n", "\n"}:
                break
            header = line.strip()
            if header.lower().startswith("content-length:"):
                content_length = int(header.split(":", 1)[1].strip())
        if content_length is None:  # pragma: no cover
            raise RuntimeError("Missing Content-Length header in MCP response")
        raw = stdout.read(content_length)
        response: dict[str, Any] = json.loads(raw)
        return response

    @staticmethod
    def _reject_mismatched_id(response: dict[str, Any], expected_id: int) -> None:
        if response.get("id") != expected_id:  # pragma: no cover
            raise RuntimeError(f"MCP response id mismatch: {response.get('id')} != {expected_id}")

    @staticmethod
    def _reject_rpc_error(response: dict[str, Any]) -> None:
        if "error" in response:
            raise RuntimeError(response["error"].get("message", "Unknown MCP error"))

    @staticmethod
    def _unwrap_result(response: dict[str, Any]) -> dict[str, Any]:
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
