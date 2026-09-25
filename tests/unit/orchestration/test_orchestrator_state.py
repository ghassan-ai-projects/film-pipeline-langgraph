"""Tests for orchestrator_state helpers — candidate/approved refs, review
cycles, revision requests, routing decisions, convergence, failure decisions,
provider health, and budget awareness."""

from __future__ import annotations

from typing import Any

from film_pipeline.orchestration import orchestrator_state as ostate


def _empty_state() -> dict[str, Any]:
    state: dict[str, Any] = {"project_id": "test-p1", "current_phase": "script"}
    ostate.ensure_orchestrator_state(state)
    return state


# --- Candidate vs approved refs ----------------------------------------------


def test_init_refs_sets_empty_dicts() -> None:
    state: dict[str, Any] = {}
    ostate.init_refs(state)
    assert ostate.get_candidate_refs(state) == {}
    assert ostate.get_approved_refs(state) == {}


def test_set_and_get_candidate_ref() -> None:
    state = _empty_state()
    ostate.set_candidate_ref(state, "script", "artifact:script:v2")
    assert ostate.get_candidate_refs(state)["script"] == "artifact:script:v2"


def test_set_and_get_approved_ref() -> None:
    state = _empty_state()
    ostate.set_approved_ref(state, "script", "artifact:script:v1")
    assert ostate.get_approved_refs(state)["script"] == "artifact:script:v1"


def test_resolve_artifact_prefers_approved() -> None:
    state = _empty_state()
    ostate.set_candidate_ref(state, "script", "artifact:script:v3")
    ostate.set_approved_ref(state, "script", "artifact:script:v2")
    assert ostate.resolve_artifact(state, "script") == "artifact:script:v2"


def test_resolve_artifact_fallback_to_candidate() -> None:
    state = _empty_state()
    ostate.set_candidate_ref(state, "script", "artifact:script:v3")
    assert ostate.resolve_artifact(state, "script") == "artifact:script:v3"


def test_resolve_artifact_require_approved_blocks_candidate() -> None:
    state = _empty_state()
    ostate.set_candidate_ref(state, "script", "artifact:script:v3")
    assert ostate.resolve_artifact(state, "script", require_approved=True) is None


# --- Review cycles -----------------------------------------------------------


def test_start_and_get_review_cycle() -> None:
    state = _empty_state()
    cycle = ostate.start_review_cycle(state, "script", strategy="parallel_independent")
    assert cycle["phase"] == "script"
    assert cycle["round_count"] == 0
    assert cycle["status"] == "active"
    assert cycle["strategy"] == "parallel_independent"


def test_advance_review_round_increments() -> None:
    state = _empty_state()
    ostate.start_review_cycle(state, "script")
    ostate.advance_review_round(state, "script")
    cycle = ostate.get_active_review_cycle(state, "script")
    assert cycle is not None
    assert cycle["round_count"] == 1


def test_close_review_cycle() -> None:
    state = _empty_state()
    ostate.start_review_cycle(state, "script")
    ostate.close_review_cycle(state, "script", status="completed")
    cycle = ostate.get_active_review_cycle(state, "script")
    assert cycle is not None
    assert cycle["status"] == "completed"


def test_get_active_review_cycle_none_for_unknown_phase() -> None:
    state = _empty_state()
    assert ostate.get_active_review_cycle(state, "qc") is None


# --- Revision requests -------------------------------------------------------


def test_add_and_get_pending_revision() -> None:
    state = _empty_state()
    ostate.add_revision_request(state, ["artifact:script:v2"], note="Fix tone")
    assert ostate.has_pending_revision(state) is True
    revisions = ostate.get_pending_revisions(state)
    assert len(revisions) == 1
    assert revisions[0]["note"] == "Fix tone"


def test_resolve_revision_clears_it() -> None:
    state = _empty_state()
    ostate.add_revision_request(state, ["artifact:script:v2"])
    ostate.resolve_revision(state, "artifact:script:v2")
    assert ostate.has_pending_revision(state) is False


def test_has_pending_revision_false_initially() -> None:
    state = _empty_state()
    assert ostate.has_pending_revision(state) is False


# --- Routing decisions -------------------------------------------------------


def test_record_and_get_routing_decisions() -> None:
    state = _empty_state()
    ostate.record_routing_decision(
        state,
        "screenwriter-agent",
        "script phase needs creator",
        input_refs=["artifact:scene-intent:S001:v1"],
        expected_output="script_scene",
    )
    decisions = ostate.get_routing_decisions(state)
    assert len(decisions) == 1
    assert decisions[0]["selected_agent"] == "screenwriter-agent"


def test_get_latest_routing_decision() -> None:
    state = _empty_state()
    ostate.record_routing_decision(state, "agent-a", "first")
    ostate.record_routing_decision(state, "agent-b", "second")
    latest = ostate.get_latest_routing_decision(state)
    assert latest is not None
    assert latest["selected_agent"] == "agent-b"


def test_get_latest_routing_decision_empty() -> None:
    state = _empty_state()
    assert ostate.get_latest_routing_decision(state) is None


# --- Convergence tracking ----------------------------------------------------


def test_convergence_stalls_after_max_rounds() -> None:
    state = _empty_state()
    ostate.init_convergence(state, "script")
    for _ in range(5):
        ostate.increment_convergence_round(state, "script")
    assert ostate.is_stalled(state, "script", max_rounds=5) is True


def test_convergence_not_stalled_below_max() -> None:
    state = _empty_state()
    ostate.init_convergence(state, "script")
    ostate.increment_convergence_round(state, "script")
    assert ostate.is_stalled(state, "script", max_rounds=5) is False


def test_mark_stalled() -> None:
    state = _empty_state()
    ostate.mark_stalled(state, "script", "validator score frozen at 70")
    assert ostate.is_stalled(state, "script") is True


# --- Failure decisions -------------------------------------------------------


def test_add_and_get_failure_decisions() -> None:
    state = _empty_state()
    ostate.add_failure_decision(
        state,
        {
            "decision_id": "fd1",
            "error_class": "provider_account",
            "severity": "blocking",
            "safe_to_retry": False,
        },
    )
    decisions = ostate.get_failure_decisions(state)
    assert len(decisions) == 1
    assert decisions[0]["severity"] == "blocking"


def test_has_blocking_failure() -> None:
    state = _empty_state()
    ostate.add_failure_decision(state, {"severity": "blocking"})
    assert ostate.has_blocking_failure(state) is True


def test_has_blocking_failure_false_for_non_blocking() -> None:
    state = _empty_state()
    ostate.add_failure_decision(state, {"severity": "non_blocking"})
    assert ostate.has_blocking_failure(state) is False


# --- Provider health snapshot ------------------------------------------------


def test_is_provider_blocked() -> None:
    state = _empty_state()
    ostate.update_provider_health(
        state, "seedance", {"status": "blocked_quota", "reason": "quota exhausted"}
    )
    assert ostate.is_provider_blocked(state, "seedance") is True


def test_is_provider_healthy() -> None:
    state = _empty_state()
    ostate.update_provider_health(state, "seedance", {"status": "healthy"})
    assert ostate.is_provider_blocked(state, "seedance") is False


def test_get_blocked_providers_filters_correctly() -> None:
    state = _empty_state()
    ostate.update_provider_health(state, "seedance", {"status": "blocked_quota"})
    ostate.update_provider_health(state, "veo", {"status": "healthy"})
    ostate.update_provider_health(state, "imagen", {"status": "blocked_auth"})
    blocked = ostate.get_blocked_providers(state)
    assert set(blocked) == {"seedance", "imagen"}


def test_get_healthy_providers() -> None:
    state = _empty_state()
    ostate.update_provider_health(state, "seedance", {"status": "blocked_quota"})
    ostate.update_provider_health(state, "veo", {"status": "healthy"})
    healthy = ostate.get_healthy_providers(state)
    assert healthy == ["veo"]


# --- Budget snapshot ---------------------------------------------------------


def test_budget_snapshot_defaults() -> None:
    state = _empty_state()
    snap = ostate.get_budget_snapshot(state)
    assert snap["cap_usd"] == 0.0
    assert snap["spent_usd"] == 0.0
    assert snap["threshold_exceeded"] is False


def test_update_budget_snapshot() -> None:
    state = _empty_state()
    ostate.update_budget_snapshot(state, cap_usd=50.0, spent_usd=30.0)
    snap = ostate.get_budget_snapshot(state)
    assert snap["remaining_usd"] == 20.0


def test_is_budget_blocked() -> None:
    state = _empty_state()
    ostate.update_budget_snapshot(state, cap_usd=50.0, spent_usd=50.0, threshold_exceeded=True)
    assert ostate.is_budget_blocked(state) is True


def test_ensure_orchestrator_state_idempotent() -> None:
    state: dict[str, Any] = {"project_id": "p1"}
    ostate.ensure_orchestrator_state(state)
    ostate.ensure_orchestrator_state(state)  # should not raise
    ostate.set_candidate_ref(state, "script", "ref")
    assert ostate.get_candidate_refs(state)["script"] == "ref"
