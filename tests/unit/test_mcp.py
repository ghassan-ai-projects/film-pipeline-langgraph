"""Tests for the MCP tool registry, project resolution, and server dispatch."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from typing import cast

import pytest

from film_pipeline.mcp import (
    AmbiguousProjectError,
    MCPError,
    MCPServer,
    ProjectRecord,
    ProjectRegistry,
    ResolutionResult,
    ToolContract,
    ToolGroup,
    ToolRegistry,
    new_envelope,
)
from film_pipeline.mcp.errors import MCPErrorCode, MCPResponse

# --- Tool registry -------------------------------------------------------


def test_tool_registry_register_and_lookup() -> None:
    reg = ToolRegistry()
    contract = ToolContract(name="hello", description="hi", group=ToolGroup.STATE)

    def _h(_a: dict[str, object]) -> dict[str, object]:
        return {"ok": True}

    reg.register(contract, _h)
    found = reg.get("hello")
    assert found.contract.description == "hi"


def test_tool_registry_duplicate_raises() -> None:
    reg = ToolRegistry()
    c = ToolContract(name="x", description="x", group=ToolGroup.STATE)

    def _h(_a: dict[str, object]) -> dict[str, object]:
        return {}

    reg.register(c, _h)
    with pytest.raises(ValueError):
        reg.register(c, _h)


def test_tool_registry_unknown_lookup_raises() -> None:
    reg = ToolRegistry()
    with pytest.raises(KeyError):
        reg.get("missing")


def test_tool_registry_list_by_group() -> None:
    reg = ToolRegistry()

    def _h(_a: dict[str, object]) -> dict[str, object]:
        return {}

    reg.register(ToolContract(name="a", description="", group=ToolGroup.STATE), _h)
    reg.register(ToolContract(name="b", description="", group=ToolGroup.KB), _h)
    reg.register(ToolContract(name="c", description="", group=ToolGroup.STATE), _h)
    assert sorted(reg.list_by_group(ToolGroup.STATE)) == ["a", "c"]
    assert reg.list_by_group(ToolGroup.KB) == ["b"]


def test_tool_registry_catalog_shape() -> None:
    reg = ToolRegistry()

    def _h(_a: dict[str, object]) -> dict[str, object]:
        return {}

    reg.register(
        ToolContract(name="x", description="x", group=ToolGroup.STATE, mutates_state=True),
        _h,
    )
    catalog = reg.catalog()
    assert catalog[0]["name"] == "x"
    assert catalog[0]["mutates_state"] is True


# --- Project resolution --------------------------------------------------


def _make_registry() -> ProjectRegistry:
    pr = ProjectRegistry()
    pr.register(
        ProjectRecord(project_id="film_2026_0001", slug="memory-in-rain", title="Memory In Rain")
    )
    pr.register(
        ProjectRecord(project_id="film_2026_0002", slug="memory-in-snow", title="Memory In Snow")
    )
    pr.register(
        ProjectRecord(
            project_id="film_2026_0003",
            slug="the-painter",
            title="The Painter",
            aliases=["painter film"],
        )
    )
    return pr


def test_project_registry_exact_id() -> None:
    pr = _make_registry()
    out = pr.resolve("film_2026_0001")
    assert out.resolved is not None
    assert out.resolved.project_id == "film_2026_0001"


def test_project_registry_slug() -> None:
    pr = _make_registry()
    out = pr.resolve("memory-in-rain")
    assert out.resolved is not None
    assert out.resolved.project_id == "film_2026_0001"


def test_project_registry_alias() -> None:
    pr = _make_registry()
    out = pr.resolve("painter film")
    assert out.resolved is not None
    assert out.resolved.project_id == "film_2026_0003"


def test_project_registry_ambiguous() -> None:
    pr = _make_registry()
    out = pr.resolve("memory")
    assert out.ambiguous is True
    assert out.count >= 2


def test_project_registry_fuzzy_match() -> None:
    pr = _make_registry()
    out = pr.resolve("mrmory-in-rain")
    assert out.count > 0
    assert out.count == 2  # matches both memory-in-rain and memory-in-snow


def test_project_registry_empty_ref() -> None:
    pr = _make_registry()
    out = pr.resolve("")
    assert out.candidates == []
    assert out.resolved is None


def test_project_registry_no_match() -> None:
    pr = _make_registry()
    out = pr.resolve("nothing-here-zzz")
    assert out.resolved is None


def test_resolve_or_raise_ambiguous() -> None:
    pr = _make_registry()
    with pytest.raises(AmbiguousProjectError) as exc_info:
        pr.resolve_or_raise("memory")
    assert len(exc_info.value.candidates) >= 2


def test_resolve_or_raise_unknown() -> None:
    pr = _make_registry()
    with pytest.raises(KeyError):
        pr.resolve_or_raise("nope")


# --- Request envelope ----------------------------------------------------


def test_envelope_has_unique_id() -> None:
    a = new_envelope()
    b = new_envelope()
    assert a.request_id != b.request_id


def test_envelope_carries_intent() -> None:
    e = new_envelope(project_ref="x", user_intent="inspect")
    assert e.user_intent == "inspect"
    assert e.actor_type == "human"


def test_envelope_actor_type_override() -> None:
    e = new_envelope(actor_type="mock_human")
    assert e.actor_type == "mock_human"


# --- MCP server dispatch -------------------------------------------------


def _build_server_with_projects() -> MCPServer:
    server = MCPServer()
    server.register_project(
        ProjectRecord(project_id="film_2026_0001", slug="memory-in-rain", title="Memory In Rain")
    )
    server.register_project(
        ProjectRecord(project_id="film_2026_0002", slug="memory-in-snow", title="Memory In Snow")
    )
    return server


def test_server_dispatches_known_tool() -> None:
    server = MCPServer()
    resp = asyncio.run(server.call("list_projects", {}))
    assert resp.success is True
    assert resp.data is not None
    data = cast(dict[str, object], resp.data)
    assert data.get("ok") is True


def test_server_returns_unknown_tool() -> None:
    server = MCPServer()
    resp = asyncio.run(server.call("nope", {}))
    assert resp.success is False
    assert resp.error is not None
    assert resp.error.code == MCPErrorCode.UNKNOWN_TOOL


def test_server_blocks_ambiguous_mutation() -> None:
    server = _build_server_with_projects()
    resp = asyncio.run(server.call("approve_phase", {"project_ref": "memory", "phase": "script"}))
    assert resp.success is False
    assert resp.error is not None
    assert resp.error.code == MCPErrorCode.AMBIGUOUS_PROJECT


def test_server_blocks_unknown_project() -> None:
    server = MCPServer()
    resp = asyncio.run(server.call("approve_phase", {"project_ref": "nope", "phase": "script"}))
    assert resp.success is False
    assert resp.error is not None
    assert resp.error.code == MCPErrorCode.UNKNOWN_PROJECT


def test_server_resolves_then_dispatches_mutation() -> None:
    server = _build_server_with_projects()
    resp = asyncio.run(
        server.call("approve_phase", {"project_ref": "memory-in-rain", "phase": "script"})
    )
    # approve_phase is wired to runtime — returns ok=False without active project
    assert resp.success is True  # handler didn't raise
    data = cast(dict[str, object], resp.data)
    # Either wired response or stub response
    assert data.get("ok") is not None or data.get("stub") is not None


def test_server_handles_handler_exception() -> None:
    from film_pipeline.mcp.contract import ToolContract, ToolGroup, ToolRegistry

    server = MCPServer(tools=ToolRegistry())

    async def boom(_args: dict[str, object]) -> dict[str, object]:
        raise ValueError("kaboom")

    server.tools.register(
        ToolContract(name="boom", description="x", group=ToolGroup.STATE, mutates_state=True),
        boom,
    )
    resp = asyncio.run(server.call("boom", {}))
    assert resp.success is False
    assert resp.error is not None
    assert resp.error.code == MCPErrorCode.INTERNAL_ERROR


def test_server_jsonrpc_initialize() -> None:
    from film_pipeline.mcp.server import handle_jsonrpc

    server = MCPServer()
    response = asyncio.run(
        handle_jsonrpc(
            server,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {},
            },
        )
    )
    assert response is not None
    result = cast(dict[str, object], response["result"])
    assert result["protocolVersion"] == "2025-03-26"


def test_server_stdio_initialize_and_tools_list() -> None:
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {},
    }
    tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }
    call_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "list_profiles", "arguments": {}},
    }
    wire = b"".join(_frame_message(req) for req in (init_request, tools_request, call_request))
    proc = subprocess.run(
        [sys.executable, "-m", "film_pipeline.mcp.server"],
        input=wire,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    responses = _read_framed_messages(proc.stdout)
    assert len(responses) == 3
    init_result = cast(dict[str, object], responses[0]["result"])
    assert init_result["protocolVersion"] == "2025-03-26"
    tools_result = cast(dict[str, object], responses[1]["result"])
    tools = cast(list[object], tools_result["tools"])
    assert any(cast(dict[str, object], tool)["name"] == "create_film_project" for tool in tools)
    call_result = cast(dict[str, object], responses[2]["result"])
    structured = cast(dict[str, object], call_result["structuredContent"])
    assert structured["ok"] is True


def test_server_handles_mcp_error() -> None:
    from film_pipeline.mcp.contract import ToolContract, ToolGroup, ToolRegistry

    server = MCPServer(tools=ToolRegistry())

    async def raise_mcp(_args: dict[str, object]) -> dict[str, object]:
        raise MCPError(code=MCPErrorCode.BUDGET_EXCEEDED, message="over budget")

    server.tools.register(
        ToolContract(name="over", description="x", group=ToolGroup.STATE, mutates_state=True),
        raise_mcp,
    )
    resp = asyncio.run(server.call("over", {}))
    assert resp.success is False
    assert resp.error is not None
    assert resp.error.code == MCPErrorCode.BUDGET_EXCEEDED


def test_server_catalog_returns_full_toolset() -> None:
    server = MCPServer()
    catalog = server.catalog()
    names = {c["name"] for c in catalog}
    assert "create_film_project" in names
    assert "submit_idea" in names
    assert "approve_phase" in names
    assert "rollback_to_checkpoint" in names
    assert "export_delivery_package" in names


def test_make_registry_has_all_14_groups() -> None:
    server = MCPServer()
    groups_present = {c["group"] for c in server.catalog()}
    expected_groups = {g.value for g in ToolGroup}
    assert groups_present == expected_groups


def test_response_to_dict_shape() -> None:
    r = MCPResponse(success=True, data={"a": 1}, request_id="r1")
    out = r.to_dict()
    assert out["success"] is True
    assert out["data"] == {"a": 1}
    assert out["request_id"] == "r1"
    assert out["error"] is None


def test_response_with_error_to_dict() -> None:
    e = MCPError(code=MCPErrorCode.NOT_FOUND, message="no")
    r = MCPResponse(success=False, error=e)
    out = r.to_dict()
    err = out["error"]
    assert isinstance(err, dict)
    assert err["code"] == "not_found"
    assert err["message"] == "no"


def test_active_project_set_after_resolution() -> None:
    server = _build_server_with_projects()
    # already set by register_project (first registration becomes active)
    assert server.active_project_id == "film_2026_0001"
    # resolving a mutation confirms the active project is retained
    asyncio.run(server.call("approve_phase", {"project_ref": "memory-in-snow", "phase": "script"}))
    assert server.active_project_id == "film_2026_0002"


def test_resolution_result_dataclass() -> None:
    r = ResolutionResult(candidates=[])
    assert r.count == 0
    assert r.ambiguous is False


# --- Wired MCP tool tests (runtime integration) --------------------------


def test_wired_get_orchestrator_summary() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.create_project(project_id="test-os", title="OS Test", slug="os-test")
    rt.set_active("test-os")

    from film_pipeline.mcp.tools import get_orchestrator_summary

    result = asyncio.run(get_orchestrator_summary({"project_ref": "test-os"}))
    assert result["ok"] is True
    assert result["project_id"] == "test-os"
    assert "current_phase" in result


def test_wired_get_blockers_empty() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.create_project(project_id="test-bl", title="Blocker Test", slug="bl-test")
    rt.set_active("test-bl")

    from film_pipeline.mcp.tools import get_blockers

    result = asyncio.run(get_blockers({}))
    assert result["ok"] is True
    assert result["has_blockers"] is False
    assert result["blockers"] == []


def test_wired_get_blockers_with_issues() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.create_project(project_id="test-bl2", title="Blocker Test 2", slug="bl-test2")
    rt.set_active("test-bl2")
    rt.add_blocker("test-bl2", "script", "Script validation failed")

    from film_pipeline.mcp.tools import get_blockers

    result = asyncio.run(get_blockers({}))
    assert result["ok"] is True
    assert result["has_blockers"] is True
    assert len(cast(list[object], result["blockers"])) == 1


def test_wired_create_and_list_checkpoints() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.create_project(project_id="test-cp", title="CP Test", slug="cp-test")
    rt.set_active("test-cp")

    from film_pipeline.mcp.tools import create_checkpoint, list_checkpoints

    cp_result = asyncio.run(create_checkpoint({"reason": "test checkpoint"}))
    assert cp_result["ok"] is True
    assert cast(str, cp_result["checkpoint_id"]).startswith("checkpoint:test-cp:")

    list_result = asyncio.run(list_checkpoints({"project_id": "test-cp"}))
    assert list_result["ok"] is True
    assert len(cast(list[object], list_result["checkpoints"])) >= 1


def test_wired_get_checkpoint() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.create_project(project_id="test-gcp", title="GCP Test", slug="gcp-test")
    rt.set_active("test-gcp")

    from film_pipeline.mcp.tools import create_checkpoint, get_checkpoint

    cp_result = asyncio.run(create_checkpoint({"reason": "get test"}))
    cid = cp_result["checkpoint_id"]

    result = asyncio.run(get_checkpoint({"checkpoint_id": cid}))
    assert result["ok"] is True
    assert result["checkpoint_id"] == cid

    # Missing checkpoint
    missing = asyncio.run(get_checkpoint({"checkpoint_id": "nonexistent"}))
    assert missing["ok"] is False


def test_wired_compare_versions() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.create_project(project_id="test-cv", title="CV Test", slug="cv-test")
    rt.set_active("test-cv")

    from film_pipeline.mcp.tools import compare_versions, create_checkpoint

    cp_a = asyncio.run(create_checkpoint({"reason": "first"}))
    cp_b = asyncio.run(create_checkpoint({"reason": "second"}))

    result = asyncio.run(
        compare_versions(
            {
                "checkpoint_id_a": cp_a["checkpoint_id"],
                "checkpoint_id_b": cp_b["checkpoint_id"],
            }
        )
    )
    assert result["ok"] is True
    assert "older_phase" in result


def test_wired_rollback_to_checkpoint() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.create_project(project_id="test-rb", title="RB Test", slug="rb-test")
    rt.set_active("test-rb")

    from film_pipeline.mcp.tools import create_checkpoint, rollback_to_checkpoint

    cp = asyncio.run(create_checkpoint({"reason": "rollback target"}))
    result = asyncio.run(rollback_to_checkpoint({"checkpoint_id": cp["checkpoint_id"]}))
    assert result["ok"] is True
    assert result["rollback_target"] == cp["checkpoint_id"]


def test_wired_get_invalidation_report() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.create_project(project_id="test-ir", title="IR Test", slug="ir-test")
    rt.set_active("test-ir")

    from film_pipeline.mcp.tools import create_checkpoint, get_invalidation_report

    cp = asyncio.run(create_checkpoint({"reason": "invalidation test"}))
    result = asyncio.run(get_invalidation_report({"checkpoint_id": cp["checkpoint_id"]}))
    assert result["ok"] is True
    assert "will_revert" in result
    assert "will_invalidate" in result


def test_wired_get_audit_log() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.create_project(project_id="test-audit", title="Audit Test", slug="audit-test")

    from film_pipeline.mcp.tools import get_audit_log

    result = asyncio.run(get_audit_log({"project_id": "test-audit"}))
    assert result["ok"] is True
    assert isinstance(result["events"], list)


def test_wired_explain_last_decision() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.create_project(project_id="test-eld", title="ELD Test", slug="eld-test")

    from film_pipeline.mcp.tools import explain_last_decision

    result = asyncio.run(explain_last_decision({}))
    assert result["ok"] is True
    assert "event_id" in result
    assert result["action"] == "create_project"


def test_wired_provider_health_tools() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.set_provider_health("mock-video-provider", "healthy")

    from film_pipeline.mcp.tools import check_provider_health, list_providers

    health = asyncio.run(check_provider_health({"provider_id": "mock-video-provider"}))
    assert health["ok"] is True
    assert health["status"] == "healthy"

    providers = asyncio.run(list_providers({}))
    assert providers["ok"] is True


def test_wired_resolve_provider_block() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.set_provider_health("mock-video-provider", "blocked_quota", "rate limited")

    from film_pipeline.mcp.tools import resolve_provider_block

    result = asyncio.run(resolve_provider_block({"provider_id": "mock-video-provider"}))
    assert result["ok"] is True
    assert result["status"] == "healthy"

    health = rt.get_provider_health("mock-video-provider")
    assert health is not None
    assert health["status"] == "healthy"


def test_wired_get_next_actions() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.create_project(project_id="test-na", title="NA Test", slug="na-test")
    rt.set_active("test-na")

    from film_pipeline.mcp.tools import get_next_actions

    result = asyncio.run(get_next_actions({}))
    assert result["ok"] is True
    assert "next_action" in result


def test_wired_explain_agent_routing() -> None:
    from film_pipeline.mcp.tools import explain_agent_routing

    result = asyncio.run(explain_agent_routing({}))
    assert result["ok"] is True


def test_wired_explain_kb_context() -> None:
    from film_pipeline.mcp.tools import explain_kb_context

    result = asyncio.run(explain_kb_context({}))
    assert result["ok"] is True


def test_wired_kb_explain_context_choice() -> None:
    from film_pipeline.mcp.tools import kb_explain_context_choice

    result = asyncio.run(kb_explain_context_choice({}))
    assert result["ok"] is True


# --- Profile / Config tools ----------------------------------------------


def test_wired_list_profiles() -> None:
    from film_pipeline.mcp.tools import list_profiles

    result = asyncio.run(list_profiles({}))
    assert result["ok"] is True
    profiles = cast(list[object], result["profiles"])
    assert len(profiles) >= 1
    first = cast(dict[str, object], profiles[0])
    assert "id" in first
    assert "name" in first
    assert "studio_mode" in first


def test_wired_inspect_profile() -> None:
    from film_pipeline.mcp.tools import inspect_profile

    # Valid profile
    result = asyncio.run(inspect_profile({"profile_id": "mock-demo"}))
    assert result["ok"] is True
    assert result["profile_id"] == "mock-demo"
    assert "raw" in result

    # Non-existent profile
    missing = asyncio.run(inspect_profile({"profile_id": "nonexistent"}))
    assert missing["ok"] is False


def test_wired_get_runtime_mode_default_mock() -> None:
    from film_pipeline.app.runtime import reset_runtime
    from film_pipeline.mcp.tools import get_runtime_mode

    reset_runtime("mock")
    result = asyncio.run(get_runtime_mode({}))
    assert result["ok"] is True
    assert result["server_mode"] == "mock"
    assert result["runtime_mode"] == "mock"


def test_wired_get_runtime_mode_after_project() -> None:
    from film_pipeline.app import runtime as runtime_mod

    runtime_mod.reset_runtime("real")
    rt = runtime_mod.get_runtime()
    rt.create_project(project_id="test-mode-real", title="Mode Test", slug="mode-test")
    rt.set_active("test-mode-real")
    # Simulate what create_film_project stores
    rt.projects["test-mode-real"]["runtime_mode"] = "real"
    rt.projects["test-mode-real"]["profile_stack"] = {
        "provider_profile": "seedance_primary",
        "quality_profile": "studio",
    }

    from film_pipeline.mcp.tools import get_runtime_mode

    result = asyncio.run(get_runtime_mode({}))
    assert result["ok"] is True
    assert result["server_mode"] == "real"
    assert result["runtime_mode"] == "real"
    stack = cast(dict[str, str], result["profile_stack"])
    assert stack["provider_profile"] == "seedance_primary"


def test_wired_get_runtime_mode_rejects_mismatch() -> None:
    from film_pipeline.app import runtime as runtime_mod
    from film_pipeline.mcp.tools import get_runtime_mode

    runtime_mod.reset_runtime("real")
    rt = runtime_mod.get_runtime()
    rt.create_project(project_id="test-mode-mismatch", title="Mismatch", slug="mismatch")
    rt.set_active("test-mode-mismatch")
    rt.projects["test-mode-mismatch"]["runtime_mode"] = "mock"

    result = asyncio.run(get_runtime_mode({}))
    assert result["ok"] is False
    assert result["server_mode"] == "real"
    assert result["project_runtime_mode"] == "mock"


def test_wired_create_film_project_rejects_mock_in_real_mode() -> None:
    from film_pipeline.app import runtime as runtime_mod
    from film_pipeline.mcp.tools import create_film_project

    runtime_mod.reset_runtime("real")
    rt = runtime_mod.get_runtime()

    # Create with mock provider in real mode — should reject
    result = asyncio.run(
        create_film_project(
            {
                "project_id": "test-real-reject-provider",
                "title": "Test",
                "slug": "test",
                "runtime_mode": "real",
                "provider_profile": "mock-demo",
            }
        )
    )
    assert result["ok"] is False
    error = cast(str, result.get("error", ""))
    assert "mock-" in error or "not allowed" in error

    # Clean up (project shouldn't have been created)
    assert rt.get_project("test-real-reject-provider") is None


def test_wired_create_film_project_accepts_real_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from film_pipeline.app import runtime as runtime_mod
    from film_pipeline.mcp.tools import create_film_project

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-openrouter")
    monkeypatch.setenv("GOOGLE_API_KEY", "AIza-test-google")
    runtime_mod.reset_runtime("real")
    # Create with real provider in real mode — should accept
    result = asyncio.run(
        create_film_project(
            {
                "project_id": "test-real-accept",
                "title": "Test",
                "slug": "test",
                "runtime_mode": "real",
                "provider_profile": "seedance_primary",
            }
        )
    )
    assert result["ok"] is True
    state = cast(dict[str, object], result["state"])
    assert state["runtime_mode"] == "real"
    assert state["resolved_config"]  # type: ignore[truthy-function]
    assert "base.studio" in cast(list[str], state["resolved_config_sources"])

    # Verify profile_stack persisted
    pstack = cast(dict[str, str], state.get("profile_stack", {}))
    assert pstack.get("provider_profile") == "provider.seedance_primary"

    rt = runtime_mod.get_runtime()
    providers = rt.list_providers()
    assert "seedance-openrouter" in providers
    assert "gemini-imagen-4" in providers
    health = rt.get_provider_health("seedance-openrouter")
    assert health is not None
    assert health["status"] == "healthy"
    image_health = rt.get_provider_health("gemini-imagen-4")
    assert image_health is not None
    assert image_health["status"] == "healthy"


def test_wired_create_film_project_rejects_invalid_runtime_mode() -> None:
    from film_pipeline.app.runtime import reset_runtime
    from film_pipeline.mcp.tools import create_film_project

    reset_runtime("mock")
    result = asyncio.run(
        create_film_project(
            {
                "project_id": "test-invalid-mode",
                "title": "Test",
                "runtime_mode": "production",
            }
        )
    )
    assert result["ok"] is False
    error = cast(str, result.get("error", ""))
    assert "mock" in error or "real" in error


def test_wired_create_film_project_defaults_to_mock_mode() -> None:
    from film_pipeline.app import runtime as runtime_mod
    from film_pipeline.mcp.tools import create_film_project

    runtime_mod.reset_runtime("mock")
    rt = runtime_mod.get_runtime()

    result = asyncio.run(
        create_film_project(
            {
                "project_id": "test-default-mock",
                "title": "Test",
                "slug": "test",
            }
        )
    )
    assert result["ok"] is True
    state = cast(dict[str, object], result["state"])
    assert state["runtime_mode"] == "mock"

    # Clean up
    rt.projects.pop("test-default-mock", None)


def test_wired_create_film_project_defaults_to_real_mode_when_server_is_real(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from film_pipeline.app.runtime import reset_runtime
    from film_pipeline.mcp.tools import create_film_project

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-openrouter")
    monkeypatch.setenv("GOOGLE_API_KEY", "AIza-test-google")
    reset_runtime("real")
    result = asyncio.run(
        create_film_project(
            {
                "project_id": "test-default-real",
                "title": "Test",
                "slug": "test-real",
                "provider_profile": "provider.seedance_primary",
            }
        )
    )
    assert result["ok"] is True
    state = cast(dict[str, object], result["state"])
    assert state["runtime_mode"] == "real"
    assert state["server_mode"] == "real"
    pstack = cast(dict[str, str], state.get("profile_stack", {}))
    assert pstack["provider_profile"] == "provider.seedance_primary"


def test_wired_create_film_project_rejects_missing_google_key_for_real_image_provider() -> None:
    from film_pipeline.app.runtime import reset_runtime
    from film_pipeline.mcp.tools import create_film_project

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-openrouter")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        reset_runtime("real")
        result = asyncio.run(
            create_film_project(
                {
                    "project_id": "test-missing-google-key",
                    "title": "Test",
                    "slug": "test-missing-google-key",
                    "runtime_mode": "real",
                    "provider_profile": "provider.seedance_primary",
                }
            )
        )

    assert result["ok"] is False
    assert result["error"] == "Real-mode provider credentials are missing."
    missing = cast(list[dict[str, str]], result["missing_credentials"])
    assert {"provider_id": "gemini-imagen-4", "env_var": "GOOGLE_API_KEY"} in missing


def test_wired_create_film_project_rejects_mode_mismatch() -> None:
    from film_pipeline.app.runtime import reset_runtime
    from film_pipeline.mcp.tools import create_film_project

    reset_runtime("mock")
    result = asyncio.run(
        create_film_project(
            {
                "project_id": "test-mode-mismatch-reject",
                "title": "Mismatch",
                "runtime_mode": "real",
                "provider_profile": "provider.seedance_primary",
            }
        )
    )
    assert result["ok"] is False
    assert result["server_mode"] == "mock"
    assert result["requested_runtime_mode"] == "real"


def test_wired_inspect_profile_accepts_friendly_provider_name() -> None:
    from film_pipeline.mcp.tools import inspect_profile

    result = asyncio.run(inspect_profile({"profile_id": "seedance_primary"}))
    assert result["ok"] is True
    assert result["profile_id"] == "provider.seedance_primary"


def test_tool_registry_has_config_group() -> None:
    from film_pipeline.mcp.contract import ToolGroup

    assert ToolGroup.CONFIG.value == "config"

    server = MCPServer()
    catalog = server.catalog()
    config_tools = [c for c in catalog if c["group"] == "config"]
    assert len(config_tools) == 3
    names = {c["name"] for c in config_tools}
    assert names == {"list_profiles", "inspect_profile", "get_runtime_mode"}


def test_list_providers_real_mode_has_no_mock_fallback() -> None:
    from film_pipeline.app.runtime import reset_runtime
    from film_pipeline.mcp.tools import list_providers

    reset_runtime("real")
    result = asyncio.run(list_providers({}))
    assert result["ok"] is True
    assert result["providers"] == []
    assert result["total"] == 0


def test_server_stdio_real_mode_requires_bootstrap() -> None:
    env = dict(os.environ)
    env["FILM_PIPELINE_MCP_MODE"] = "real"
    env.pop("OPENROUTER_API_KEY", None)
    proc = subprocess.run(
        [sys.executable, "-m", "film_pipeline.mcp.server"],
        input=b"",
        capture_output=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 1
    assert "OPENROUTER_API_KEY" in proc.stderr.decode("utf-8")


def _frame_message(payload: dict[str, object]) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode() + body


def _read_framed_messages(data: bytes) -> list[dict[str, object]]:
    messages: list[dict[str, object]] = []
    idx = 0
    while idx < len(data):
        header_end = data.find(b"\r\n\r\n", idx)
        assert header_end != -1
        header_block = data[idx:header_end].decode("utf-8")
        length = 0
        for line in header_block.splitlines():
            if line.lower().startswith("content-length:"):
                length = int(line.split(":", 1)[1].strip())
                break
        assert length > 0
        start = header_end + 4
        end = start + length
        messages.append(cast(dict[str, object], json.loads(data[start:end].decode("utf-8"))))
        idx = end
    return messages
