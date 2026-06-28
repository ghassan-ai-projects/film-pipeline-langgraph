"""Unit tests for film_pipeline.mcp.tools.kb."""

from __future__ import annotations

import asyncio

from film_pipeline.mcp.tools import (
    create_film_project,
    kb_explain_context_choice,
    kb_get_context_packet,
    kb_get_item,
    kb_search,
    set_active_project,
)


def test_kb_search_returns_items_or_empty() -> None:
    result = asyncio.run(kb_search({"query": "camera"}))
    assert result["ok"] is True
    assert "items" in result
    assert isinstance(result["total"], int)


def test_kb_search_with_phase_filter() -> None:
    result = asyncio.run(kb_search({"query": "x", "phase": "script"}))
    assert result["ok"] is True


def test_kb_get_item_not_found() -> None:
    result = asyncio.run(kb_get_item({"item_id": "totally-bogus-kb-item-id"}))
    assert result["ok"] is False


def test_kb_get_context_packet_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(kb_get_context_packet({}))
    assert result["ok"] is False


def test_kb_get_context_packet_with_active_project() -> None:
    asyncio.run(create_film_project({"project_id": "proj-kb-1"}))
    asyncio.run(set_active_project({"project_ref": "proj-kb-1"}))
    result = asyncio.run(kb_get_context_packet({"phase": "intake"}))
    assert result["ok"] is True


def test_kb_explain_context_choice() -> None:
    result = asyncio.run(kb_explain_context_choice({}))
    assert result["ok"] is True
    assert "message" in result
