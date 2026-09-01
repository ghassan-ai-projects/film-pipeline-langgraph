"""Unit tests for film_pipeline.mcp.tools.providers."""

from __future__ import annotations

import asyncio
from typing import cast

from film_pipeline.mcp.tools import (
    check_provider_health,
    list_providers,
    resolve_provider_block,
)


def test_check_provider_health_defaults_to_mock_provider() -> None:
    result = asyncio.run(check_provider_health({}))
    assert result["ok"] is True
    assert result["provider_id"]


def test_check_provider_health_unknown_provider() -> None:
    result = asyncio.run(check_provider_health({"provider_id": "unknown-provider-xyz"}))
    assert result["ok"] is True
    assert result["status"] == "unknown"


def test_resolve_provider_block_requires_provider_id() -> None:
    result = asyncio.run(resolve_provider_block({}))
    assert result["ok"] is False


def test_resolve_provider_block_sets_healthy() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.set_provider_health("test-provider-block", "blocked_quota", "rate limited")
    result = asyncio.run(resolve_provider_block({"provider_id": "test-provider-block"}))
    assert result["ok"] is True
    assert result["status"] == "healthy"
    health = rt.get_provider_health("test-provider-block")
    assert health is not None
    assert health["status"] == "healthy"


def test_list_providers_returns_mock_fallback_when_empty_in_mock_mode() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    if rt.server_mode == "mock":
        rt.clear_providers()
        result = asyncio.run(list_providers({}))
        assert result["ok"] is True
        assert cast(int, result["total"]) >= 1


def test_list_providers_includes_real_chat_provider_health() -> None:
    from film_pipeline.app.runtime import reset_runtime

    rt = reset_runtime("real")
    rt.seed_default_provider_health()

    result = asyncio.run(list_providers({}))

    assert result["ok"] is True
    providers = cast(list[dict[str, object]], result["providers"])
    zai = next(provider for provider in providers if provider["provider_id"] == "zai")
    assert zai["status"] in {"healthy", "unconfigured"}
