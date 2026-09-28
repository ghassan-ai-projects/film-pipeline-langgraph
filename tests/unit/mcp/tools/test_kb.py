"""Unit tests for film_pipeline.mcp.tools.kb."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from film_pipeline.mcp.tools import (
    create_film_project,
    kb_explain_context_choice,
    kb_get_context_packet,
    kb_get_item,
    kb_search,
    set_active_project,
)

CallTool = Callable[..., Any]


def test_kb_search_returns_items_or_empty(call_tool: CallTool) -> None:
    result = call_tool(kb_search, {"query": "camera"})
    assert result["ok"] is True
    assert "items" in result
    assert isinstance(result["total"], int)


def test_kb_search_with_phase_filter(call_tool: CallTool) -> None:
    result = call_tool(kb_search, {"query": "x", "phase": "script"})
    assert result["ok"] is True


def test_kb_get_item_not_found(call_tool: CallTool) -> None:
    result = call_tool(kb_get_item, {"item_id": "totally-bogus-kb-item-id"})
    assert result["ok"] is False


def test_kb_get_context_packet_with_active_project(call_tool: CallTool) -> None:
    call_tool(create_film_project, {"project_id": "proj-kb-1"})
    call_tool(set_active_project, {"project_ref": "proj-kb-1"})
    result = call_tool(kb_get_context_packet, {"phase": "intake"})
    assert result["ok"] is True


def test_kb_explain_context_choice(call_tool: CallTool) -> None:
    result = call_tool(kb_explain_context_choice, {})
    assert result["ok"] is True
    assert "message" in result


def test_kb_search_manifest_not_found(monkeypatch: pytest.MonkeyPatch, call_tool: CallTool) -> None:
    monkeypatch.setattr(
        "film_pipeline.kb.paths.kb_manifest_path", lambda: Path("/nonexistent/manifest.yaml")
    )
    result = call_tool(kb_search, {"query": "camera"})
    assert result["ok"] is True
    assert result["total"] == 0
    assert "not found" in cast(str, result["message"])


def test_kb_search_exception(monkeypatch: pytest.MonkeyPatch, call_tool: CallTool) -> None:
    from film_pipeline.kb.retrieval import KBRetrieval

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(KBRetrieval, "by_tags", _raise)
    result = call_tool(kb_search, {"query": "camera"})
    assert result["ok"] is False
    assert "boom" in cast(str, result["error"])


def test_kb_get_item_manifest_not_found(
    monkeypatch: pytest.MonkeyPatch, call_tool: CallTool
) -> None:
    monkeypatch.setattr(
        "film_pipeline.kb.paths.kb_manifest_path", lambda: Path("/nonexistent/manifest.yaml")
    )
    result = call_tool(kb_get_item, {"item_id": "any"})
    assert result["ok"] is False
    assert "not found" in cast(str, result["error"])


def test_kb_get_item_found(call_tool: CallTool) -> None:
    result = call_tool(kb_get_item, {"item_id": "kb.policy.prompt.rctco.v1"})
    assert result["ok"] is True
    assert result["id"] == "kb.policy.prompt.rctco.v1"


def test_kb_get_item_exception(monkeypatch: pytest.MonkeyPatch, call_tool: CallTool) -> None:
    from film_pipeline.kb.manifest import KBManifest

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("manifest boom")

    monkeypatch.setattr(KBManifest, "from_yaml", _raise)
    result = call_tool(kb_get_item, {"item_id": "kb.policy.prompt.rctco.v1"})
    assert result["ok"] is False
    assert "manifest boom" in cast(str, result["error"])


def test_kb_get_context_packet_manifest_not_found(
    monkeypatch: pytest.MonkeyPatch, call_tool: CallTool
) -> None:
    call_tool(create_film_project, {"project_id": "proj-kb-manifest"})
    call_tool(set_active_project, {"project_ref": "proj-kb-manifest"})
    monkeypatch.setattr(
        "film_pipeline.kb.paths.kb_manifest_path", lambda: Path("/nonexistent/manifest.yaml")
    )
    result = call_tool(kb_get_context_packet, {})
    assert result["ok"] is True
    assert result["packet"] == {"items": []}


def test_kb_get_context_packet_exception(
    monkeypatch: pytest.MonkeyPatch, call_tool: CallTool
) -> None:
    call_tool(create_film_project, {"project_id": "proj-kb-exception"})
    call_tool(set_active_project, {"project_ref": "proj-kb-exception"})
    from film_pipeline.kb.packets import KBContextPacketBuilder

    monkeypatch.setattr(
        KBContextPacketBuilder,
        "build",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("packet boom")),
    )
    result = call_tool(kb_get_context_packet, {})
    assert result["ok"] is False
    assert "packet boom" in cast(str, result["error"])
