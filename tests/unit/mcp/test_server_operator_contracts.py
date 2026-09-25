"""Operator action contracts at the MCP dispatcher and JSON-RPC boundary."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from film_pipeline.mcp.errors import MCPErrorCode, MCPResponse
from film_pipeline.mcp.resolution import ProjectRecord
from film_pipeline.mcp.server import MCPServer, handle_jsonrpc
from film_pipeline.studio.runtime import StudioRuntime

_OPERATOR_ACTIONS = (
    "approve_phase",
    "request_revision",
    "run_validation",
    "rollback_to_checkpoint",
)


class _KnownNewlineFramingMismatch(Exception):
    """The server consumed valid newline JSON without returning a response."""


def _make_operator_server(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[StudioRuntime, MCPServer]:
    """Build an isolated runtime and a registry-backed server for one action."""
    import film_pipeline.mcp.tools as tools_pkg

    project_id = "operator-contract"
    runtime = StudioRuntime(runtime_root=tmp_path / "runtime")
    runtime.create_project(project_id, "Operator Contract")
    runtime.set_active(project_id)
    active = runtime.get_active()
    assert active is not None
    active["current_phase"] = "intake"
    monkeypatch.setattr(tools_pkg, "get_runtime", lambda: runtime)

    server = MCPServer()
    server.register_project(
        ProjectRecord(project_id=project_id, slug=project_id, title="Operator Contract")
    )
    return runtime, server


def _action_arguments(action: str, runtime: StudioRuntime) -> dict[str, object]:
    """Prepare a deterministic active state and arguments for one real handler."""
    if action == "approve_phase":
        return {"confirmed": True}
    if action == "request_revision":
        return {"confirmed": True, "note": "Add a clearer character goal."}
    if action == "run_validation":
        active = runtime.get_active()
        assert active is not None
        active["current_phase"] = "intake"
        return {}
    if action == "rollback_to_checkpoint":
        active = runtime.get_active()
        assert active is not None
        project_id = str(active["project_id"])
        checkpoint = runtime.create_checkpoint(
            project_id=project_id,
            phase="qc",
            reason="operator contract target",
        )
        return {"confirmed": True, "checkpoint_id": checkpoint.checkpoint_id}
    raise AssertionError(f"unexpected operator action: {action}")


def _expected_data_keys(action: str) -> set[str]:
    return {
        "approve_phase": {"ok", "project_id", "current_phase"},
        "request_revision": {"ok", "project_id", "current_phase", "issues"},
        "run_validation": {"ok", "message"},
        "rollback_to_checkpoint": {
            "ok",
            "rollback_target",
            "phase",
            "reason",
            "invalidation_report_ref",
            "rollback_record_ref",
            "message",
        },
    }[action]


@pytest.mark.parametrize("action", _OPERATOR_ACTIONS)
def test_server_call_freezes_operator_action_response_shape(
    action: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, server = _make_operator_server(tmp_path, monkeypatch)
    arguments = _action_arguments(action, runtime)

    response = asyncio.run(server.call(action, arguments))

    assert isinstance(response, MCPResponse)
    assert response.success is True
    assert response.request_id
    data = cast(dict[str, object], response.data)
    assert set(data) == _expected_data_keys(action)
    assert data["ok"] is True
    if action in {"approve_phase", "request_revision"}:
        assert data["project_id"] == "operator-contract"
        assert isinstance(data["current_phase"], str)
        if action == "request_revision":
            assert isinstance(data["issues"], list)
    elif action == "run_validation":
        assert data["message"] == "No validators found for this phase."
    else:
        assert data["phase"] == "qc"
        assert isinstance(data["invalidation_report_ref"], str)
        assert isinstance(data["rollback_record_ref"], str)


@pytest.mark.parametrize("action", _OPERATOR_ACTIONS)
def test_jsonrpc_call_preserves_operator_action_result(
    action: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, server = _make_operator_server(tmp_path, monkeypatch)
    arguments = _action_arguments(action, runtime)
    request = {
        "jsonrpc": "2.0",
        "id": f"{action}-request",
        "method": "tools/call",
        "params": {"name": action, "arguments": arguments},
    }

    response = asyncio.run(handle_jsonrpc(server, request))

    assert response is not None
    assert response["id"] == f"{action}-request"
    result = cast(dict[str, object], response["result"])
    data = cast(dict[str, object], result["structuredContent"])
    assert set(data) == _expected_data_keys(action)
    assert data["ok"] is True
    assert result["isError"] is False
    assert result["content"] == [{"type": "text", "text": json.dumps(data, default=str)}]


@pytest.mark.parametrize("boundary", ["call", "jsonrpc"])
def test_run_validation_report_and_ref_shape(
    boundary: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import film_pipeline.mcp.tools.validation as validation_tools

    runtime, server = _make_operator_server(tmp_path, monkeypatch)
    active = runtime.get_active()
    assert active is not None
    active["current_phase"] = "script"
    reports = [{"validator_id": "script-structure", "status": "pass", "score": 100.0}]
    saved_refs = ["artifact:script:validation_report:v1"]

    def deterministic_validation(
        _store: object,
        _project_id: str,
        _phase: object,
    ) -> tuple[list[dict[str, object]], list[str]]:
        return reports, saved_refs

    monkeypatch.setattr(validation_tools, "_validate_script", deterministic_validation)
    arguments: dict[str, object] = {}

    if boundary == "call":
        call_response = asyncio.run(server.call("run_validation", arguments))
        assert call_response.success is True
        data = cast(dict[str, object], call_response.data)
    else:
        rpc_response = asyncio.run(
            handle_jsonrpc(
                server,
                {
                    "jsonrpc": "2.0",
                    "id": "validation-report",
                    "method": "tools/call",
                    "params": {"name": "run_validation", "arguments": arguments},
                },
            )
        )
        assert rpc_response is not None
        result = cast(dict[str, object], rpc_response["result"])
        data = cast(dict[str, object], result["structuredContent"])
        assert result["isError"] is False
        assert result["content"] == [{"type": "text", "text": json.dumps(data, default=str)}]

    assert set(data) == {"ok", "phase", "reports", "saved_refs"}
    assert data == {"ok": True, "phase": "script", "reports": reports, "saved_refs": saved_refs}


@pytest.mark.parametrize(
    ("action", "arguments"),
    [
        ("approve_phase", {}),
        ("request_revision", {"note": "revise"}),
        ("rollback_to_checkpoint", {"checkpoint_id": "checkpoint-missing"}),
    ],
)
def test_server_call_requires_confirmation_for_mutating_operator_actions(
    action: str,
    arguments: dict[str, object],
) -> None:
    response = asyncio.run(MCPServer().call(action, arguments))

    assert response.success is False
    assert response.error is not None
    assert response.error.code == MCPErrorCode.CONFIRMATION_REQUIRED
    assert response.error.details == {"tool": action}


def test_jsonrpc_maps_confirmation_refusal_to_jsonrpc_error() -> None:
    response = asyncio.run(
        handle_jsonrpc(
            MCPServer(),
            {
                "jsonrpc": "2.0",
                "id": "approval-request",
                "method": "tools/call",
                "params": {"name": "approve_phase", "arguments": {}},
            },
        )
    )

    assert response == {
        "jsonrpc": "2.0",
        "id": "approval-request",
        "error": {
            "code": -32000,
            "message": (
                "Tool 'approve_phase' requires explicit confirmation. "
                "Pass 'confirmed': true to proceed."
            ),
        },
    }


@pytest.fixture
def newline_stdio_messages(tmp_path: Path) -> list[dict[str, object]]:
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "operator-contract-test", "version": "1.0.0"},
        },
    }
    env = dict(os.environ)
    env.update(
        {
            "FILM_PIPELINE_MCP_MODE": "mock",
            "FILM_PIPELINE_NO_PERSIST": "1",
            "FILM_PIPELINE_RUNTIME_ROOT": str(tmp_path / "runtime"),
            "FILM_PIPELINE_STORAGE_ROOT": str(tmp_path / "storage"),
        }
    )

    process = subprocess.run(
        [sys.executable, "-m", "film_pipeline.mcp.server"],
        input=(json.dumps(request) + "\n").encode("utf-8"),
        capture_output=True,
        check=False,
        cwd=Path(__file__).resolve().parents[3],
        env=env,
        timeout=10,
    )

    assert process.returncode == 0, process.stderr.decode("utf-8")
    assert b"Server ready" in process.stderr
    lines = [line for line in process.stdout.splitlines() if line]
    if not lines:
        return []
    messages = [json.loads(line) for line in lines]
    assert messages == [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "film-pipeline-mcp", "version": "0.4.0"},
            },
        },
    ]
    return cast(list[dict[str, object]], messages)


@pytest.mark.xfail(
    strict=True,
    raises=_KnownNewlineFramingMismatch,
    reason="O-01 records that the current stdio loop consumes newline JSON as a header.",
)
def test_stdio_process_accepts_newline_delimited_json(
    newline_stdio_messages: list[dict[str, object]],
) -> None:
    if not newline_stdio_messages:
        raise _KnownNewlineFramingMismatch("newline-delimited request received no response")
