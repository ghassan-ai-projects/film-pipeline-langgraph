"""Unit tests for film_pipeline.mcp.tools.config."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import cast

import pytest

from film_pipeline.app.runtime import reset_runtime
from film_pipeline.mcp.tools import get_runtime_mode, inspect_profile, list_profiles


@pytest.fixture(autouse=True)
def _reset_to_mock_mode() -> Generator[None, None, None]:
    reset_runtime("mock")
    yield
    reset_runtime("mock")


def test_list_profiles_returns_known_fields() -> None:
    result = asyncio.run(list_profiles({}))
    assert result["ok"] is True
    profiles = cast(list[dict[str, object]], result["profiles"])
    assert result["total"] == len(profiles)
    assert len(profiles) >= 1
    for key in ("id", "name", "description", "studio_mode", "file"):
        assert key in profiles[0]


def test_inspect_profile_requires_profile_id() -> None:
    result = asyncio.run(inspect_profile({}))
    assert result["ok"] is False
    assert "profile_id is required" in cast(str, result["error"])


def test_inspect_profile_not_found() -> None:
    result = asyncio.run(inspect_profile({"profile_id": "definitely-not-a-real-profile"}))
    assert result["ok"] is False


def test_get_runtime_mode_default_mock() -> None:
    result = asyncio.run(get_runtime_mode({}))
    assert result["ok"] is True
    assert result["server_mode"] == "mock"
    assert result["runtime_mode"] == "mock"
    assert result["aligned"] is True


def test_get_runtime_mode_no_active_project_uses_server_mode() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(get_runtime_mode({}))
    assert result["ok"] is True
    assert result["project_runtime_mode"] == ""
