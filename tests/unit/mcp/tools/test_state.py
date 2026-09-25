"""Unit tests for film_pipeline.mcp.tools.state."""

from __future__ import annotations

import asyncio
from typing import cast

from film_pipeline.mcp.tools import (
    create_film_project,
    get_blockers,
    get_current_phase,
    get_film_state,
    get_next_actions,
    get_orchestrator_summary,
    set_active_project,
)
from film_pipeline.studio.runtime import get_runtime as gr


def _make_active_project(project_id: str) -> None:
    asyncio.run(create_film_project({"project_id": project_id}))
    asyncio.run(set_active_project({"project_ref": project_id}))


def test_get_current_phase_requires_active_project() -> None:
    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(get_current_phase({}))
    assert result["ok"] is False


def test_get_current_phase_success() -> None:
    _make_active_project("state-phase-1")
    result = asyncio.run(get_current_phase({}))
    assert result["ok"] is True
    assert "current_phase" in result


def test_get_film_state_requires_active_project() -> None:
    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(get_film_state({}))
    assert result["ok"] is False


def test_get_film_state_sanitizes_internal_keys() -> None:
    _make_active_project("state-film-1")
    rt = gr()
    active = rt.get_active()
    assert active is not None
    active["_internal_secret"] = "hidden"
    rt.projects["state-film-1"] = active

    result = asyncio.run(get_film_state({}))
    assert result["ok"] is True
    state = cast(dict[str, object], result["state"])
    assert "_internal_secret" not in state
    assert "approved" not in state
    assert "human_approval_required" not in state


def test_get_next_actions_requires_active_project() -> None:
    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(get_next_actions({}))
    assert result["ok"] is False


def test_get_next_actions_success() -> None:
    _make_active_project("state-next-1")
    result = asyncio.run(get_next_actions({}))
    assert result["ok"] is True
    assert "next_action" in result


def test_read_only_action_views_do_not_mutate_state_or_expose_router_metadata() -> None:
    _make_active_project("state-read-only")
    rt = gr()
    state = rt.get_active()
    assert state is not None
    state["current_phase"] = "script"
    state["approved"] = True
    state["issues"] = [{"code": "bad-script", "severity": "blocking", "message": "Fix it."}]
    before = dict(state)

    next_actions = asyncio.run(get_next_actions({}))
    summary = asyncio.run(get_orchestrator_summary({}))

    assert state == before
    next_blocked = cast(list[dict[str, object]], next_actions["blocked"])
    summary_blocked = cast(list[dict[str, object]], summary["blocked_actions"])
    assert all("origin" not in blocker for blocker in next_blocked)
    assert all("origin" not in blocker for blocker in summary_blocked)


def test_get_blockers_requires_active_project() -> None:
    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(get_blockers({}))
    assert result["ok"] is False
