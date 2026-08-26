"""Behavioral tests for the canonical blocker projection."""

from __future__ import annotations

from film_pipeline.graph import orchestrator_state as ostate
from film_pipeline.graph.router import get_blockers_for_state, public_blocked_actions


def test_blocking_issue_is_specific_and_not_duplicated() -> None:
    state = {
        "current_phase": "script",
        "approved": True,
        "issues": [{"code": "script_below_floor", "severity": "blocking", "message": "Too short."}],
    }

    assert get_blockers_for_state(state) == [
        {"action": "resolve_blocking_issue", "reason": "script_below_floor: Too short."}
    ]


def test_blocker_projection_does_not_initialize_live_state() -> None:
    state = {"current_phase": "script", "approved": True, "issues": []}

    assert get_blockers_for_state(state) == []
    assert state == {"current_phase": "script", "approved": True, "issues": []}


def test_human_approval_issue_is_specific_and_not_duplicated() -> None:
    state = {
        "current_phase": "script",
        "approved": False,
        "human_approval_required": True,
        "issues": [{"code": "script_invalid", "severity": "blocking", "message": "Fix it."}],
    }

    assert get_blockers_for_state(state) == [
        {"action": "resolve_blocking_issue", "reason": "script_invalid: Fix it."}
    ]


def test_budget_blocker_is_reported_from_router() -> None:
    state = {"current_phase": "gen_planning", "approved": True, "issues": []}
    ostate.update_budget_snapshot(state, cap_usd=10.0, spent_usd=10.0, threshold_exceeded=True)

    assert {"action": "advance_phase", "reason": "budget threshold exceeded"} in (
        get_blockers_for_state(state)
    )


def test_provider_blocker_is_reported_from_router() -> None:
    state = {"current_phase": "generation", "approved": True, "issues": []}
    ostate.update_provider_health(state, "seedance-openrouter", {"status": "blocked_quota"})

    assert get_blockers_for_state(state) == [
        {
            "action": "advance_to_generation",
            "reason": "provider(s) blocked: seedance-openrouter",
        }
    ]


def test_pending_revision_is_reported_from_router() -> None:
    state = {"current_phase": "script", "approved": True, "issues": []}
    ostate.add_revision_request(state, ["artifact:script:v1"], note="Repair dialogue")

    assert get_blockers_for_state(state) == [
        {"action": "approve_phase", "reason": "pending revision must be resolved first"}
    ]


def test_public_blocked_actions_strip_internal_provenance() -> None:
    from film_pipeline.graph.router import RouterResult

    result = RouterResult(
        blocked=[
            {
                "action": "advance_phase",
                "reason": "blocking issue: script_invalid",
                "origin": "state_issue",
            }
        ]
    )

    assert public_blocked_actions(result) == [
        {"action": "advance_phase", "reason": "blocking issue: script_invalid"}
    ]
