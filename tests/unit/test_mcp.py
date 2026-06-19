"""Tests for the MCP tool registry, project resolution, and server dispatch."""

from __future__ import annotations

import asyncio
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
    assert data["stub"] is True


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
    assert resp.success is True
    data = cast(dict[str, object], resp.data)
    assert data["stub"] is True
    assert data["phase"] == "script"


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


def test_make_registry_has_all_13_groups() -> None:
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
