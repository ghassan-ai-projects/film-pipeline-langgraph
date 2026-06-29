"""Unit tests for film_pipeline.mcp.tools.kb."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

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


def test_kb_search_manifest_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "film_pipeline.kb.paths.kb_manifest_path", lambda: Path("/nonexistent/manifest.yaml")
    )
    result = asyncio.run(kb_search({"query": "camera"}))
    assert result["ok"] is True
    assert result["total"] == 0
    assert "not found" in cast(str, result["message"])


def test_kb_search_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    from film_pipeline.kb.retrieval import KBRetrieval

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(KBRetrieval, "by_tags", _raise)
    result = asyncio.run(kb_search({"query": "camera"}))
    assert result["ok"] is False
    assert "boom" in cast(str, result["error"])


def test_kb_get_item_manifest_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "film_pipeline.kb.paths.kb_manifest_path", lambda: Path("/nonexistent/manifest.yaml")
    )
    result = asyncio.run(kb_get_item({"item_id": "any"}))
    assert result["ok"] is False
    assert "not found" in cast(str, result["error"])


def test_kb_get_item_found() -> None:
    result = asyncio.run(kb_get_item({"item_id": "kb.policy.prompt.rctco.v1"}))
    assert result["ok"] is True
    assert result["id"] == "kb.policy.prompt.rctco.v1"


def test_kb_get_item_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    from film_pipeline.kb.manifest import KBManifest

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("manifest boom")

    monkeypatch.setattr(KBManifest, "from_yaml", _raise)
    result = asyncio.run(kb_get_item({"item_id": "kb.policy.prompt.rctco.v1"}))
    assert result["ok"] is False
    assert "manifest boom" in cast(str, result["error"])


def test_kb_get_context_packet_manifest_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(create_film_project({"project_id": "proj-kb-manifest"}))
    asyncio.run(set_active_project({"project_ref": "proj-kb-manifest"}))
    monkeypatch.setattr(
        "film_pipeline.kb.paths.kb_manifest_path", lambda: Path("/nonexistent/manifest.yaml")
    )
    result = asyncio.run(kb_get_context_packet({}))
    assert result["ok"] is True
    assert result["packet"] == {"items": []}


def test_kb_get_context_packet_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(create_film_project({"project_id": "proj-kb-exception"}))
    asyncio.run(set_active_project({"project_ref": "proj-kb-exception"}))
    from film_pipeline.kb.packets import KBContextPacketBuilder

    monkeypatch.setattr(
        KBContextPacketBuilder,
        "build",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("packet boom")),
    )
    result = asyncio.run(kb_get_context_packet({}))
    assert result["ok"] is False
    assert "packet boom" in cast(str, result["error"])
