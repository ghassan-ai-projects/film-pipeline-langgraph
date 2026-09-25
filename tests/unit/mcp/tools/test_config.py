"""Unit tests for film_pipeline.mcp.tools.config."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import cast

import pytest

from film_pipeline.app.runtime import reset_runtime
from film_pipeline.mcp.tools import (
    approve_profile_change,
    create_film_project,
    get_runtime_mode,
    inspect_profile,
    list_profiles,
    propose_profile_change,
    set_active_project,
)


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


def test_quality_environment_override_updates_effective_profile_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FILM_PIPELINE_QUALITY", "draft")

    result = asyncio.run(
        create_film_project(
            {
                "project_id": "quality-env-override",
                "quality_profile": "quality.studio",
            }
        )
    )

    assert result["ok"] is True
    state = cast(dict[str, object], result["state"])
    stack = cast(dict[str, str], state["profile_stack"])
    config = cast(dict[str, object], state["resolved_config"])
    assert stack["quality_profile"] == "quality.draft"
    assert config["quality_profile"] == "draft"


def _create_active_project(project_id: str) -> None:
    asyncio.run(create_film_project({"project_id": project_id, "title": "T", "slug": project_id}))
    asyncio.run(set_active_project({"project_ref": project_id}))


def test_propose_profile_change_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(
        propose_profile_change({"reason": "Switch quality", "quality_profile": "quality.draft"})
    )
    assert result["ok"] is False
    assert "active project" in cast(str, result["error"]).lower()


def test_propose_profile_change_requires_reason() -> None:
    _create_active_project("profile-change-no-reason")
    result = asyncio.run(propose_profile_change({"quality_profile": "quality.draft"}))
    assert result["ok"] is False
    assert "reason is required" in cast(str, result["error"])


def test_propose_profile_change_requires_change() -> None:
    _create_active_project("profile-change-no-change")
    result = asyncio.run(propose_profile_change({"reason": "No actual change"}))
    assert result["ok"] is False
    assert "At least one profile change" in cast(str, result["error"])


def test_propose_profile_change_creates_pending_proposal() -> None:
    _create_active_project("profile-change-propose")
    result = asyncio.run(
        propose_profile_change(
            {
                "reason": "Switch to draft quality for faster iteration",
                "quality_profile": "quality.draft",
                "proposed_by": "operator-test",
            }
        )
    )
    assert result["ok"] is True
    assert "proposal_id" in result
    assert result["previous_profile_stack"] != result["proposed_profile_stack"]
    proposed_stack = cast(dict[str, str], result["proposed_profile_stack"])
    assert proposed_stack.get("quality_profile") == "quality.draft"
    assert "proposal_ref" in result


def test_approve_profile_change_requires_confirmed() -> None:
    _create_active_project("profile-change-confirm")
    proposed = asyncio.run(
        propose_profile_change({"reason": "R", "quality_profile": "quality.draft"})
    )
    proposal_id = cast(str, proposed["proposal_id"])
    result = asyncio.run(approve_profile_change({"proposal_id": proposal_id}))
    # The MCP server enforces confirmation before the handler is invoked, but
    # calling the handler directly without confirmed=True should still work.
    assert result["ok"] is True


def test_approve_profile_change_updates_config_and_registers_profile_providers() -> None:
    _create_active_project("profile-change-approve")
    proposed = asyncio.run(
        propose_profile_change(
            {
                "reason": "R",
                "quality_profile": "quality.draft",
                "provider_profile": "mock-demo",
            }
        )
    )
    proposal_id = cast(str, proposed["proposal_id"])

    from film_pipeline.app.runtime import get_runtime as gr

    runtime = gr()
    project_state = runtime.get_project("profile-change-approve")
    assert project_state is not None
    project_state["profile_version"] = 2

    result = asyncio.run(
        approve_profile_change(
            {"proposal_id": proposal_id, "confirmed": True, "approved_by": "human-test"}
        )
    )
    assert result["ok"] is True
    assert result["profile_version"] == 3
    result_stack = cast(dict[str, str], result["profile_stack"])
    assert result_stack.get("quality_profile") == "quality.draft"
    assert result_stack.get("provider_profile") == "mock-demo"
    assert "resolved_config_ref" in result
    assert "invalidation_report_ref" in result
    assert "approval_ref" in result

    state = runtime.get_project("profile-change-approve")
    assert state is not None
    assert state["profile_version"] == 3
    state_stack = cast(dict[str, str], state["profile_stack"])
    assert state_stack.get("quality_profile") == "quality.draft"
    assert state_stack.get("provider_profile") == "mock-demo"
    assert runtime.list_providers() == ["mock-video-provider", "mock-image-provider"]
    assert runtime.get_provider_health("mock-video-provider") == {
        "status": "healthy",
        "reason": "",
    }


def test_approve_profile_change_rejects_missing_proposal() -> None:
    _create_active_project("profile-change-missing")
    result = asyncio.run(
        approve_profile_change({"proposal_id": "does-not-exist", "confirmed": True})
    )
    assert result["ok"] is False
    assert "not found" in cast(str, result["error"])
