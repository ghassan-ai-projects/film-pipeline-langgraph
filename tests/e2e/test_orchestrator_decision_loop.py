"""E2E tests for the orchestrator decision loop — multi-round review,
revision durability, provider-blocked routing, and
approved-baseline handoff between phases."""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.orchestration import orchestrator_state as ostate
from film_pipeline.orchestration.router import compute_actions


def _base_state(phase: str = "script", approved: bool = False) -> dict[str, Any]:
    state: dict[str, Any] = {
        "current_phase": phase,
        "approved": approved,
        "human_approval_required": False,
        "issues": [],
        "project_id": "e2e-test",
    }
    ostate.ensure_orchestrator_state(state)
    return state


@pytest.mark.e2e
class TestOrchestratorDecisionLoop:
    """End-to-end: verify orchestrator routing across multiple scenarios."""

    # --- Happy path: baseline still works ------------------------------------

    def test_phase_progression_happy_path(self) -> None:
        """Straight-line phase progression unchanged."""
        state = _base_state("intake", approved=True)
        r = compute_actions(state)
        assert r.next_action == "advance_to_constitution"

    # --- Revision → repair → approve cycle ----------------------------------

    def test_revision_prevents_approval(self) -> None:
        """A pending revision blocks phase advancement."""
        state = _base_state("script", approved=False)
        ostate.add_revision_request(state, ["artifact:script:v1"], note="Fix tone")
        r = compute_actions(state)
        assert r.next_action == "revise"
        assert "approve_phase" not in r.eligible

    def test_revision_resolved_allows_approval(self) -> None:
        """Resolving a revision unblocks the approval path."""
        state = _base_state("script", approved=False)
        ostate.add_revision_request(state, ["artifact:script:v1"])
        ostate.resolve_revision(state, "artifact:script:v1")
        r = compute_actions(state)
        assert r.next_action == "present_review_package"
        assert "approve_phase" in r.eligible

    def test_multi_round_revision_increments_counter(self) -> None:
        """Multiple revision rounds advance the convergence counter."""
        state = _base_state("script", approved=False)
        ostate.init_convergence(state, "script")
        ostate.increment_convergence_round(state, "script")
        ostate.increment_convergence_round(state, "script")
        assert ostate.is_stalled(state, "script", max_rounds=2) is True

    # --- Candidate vs approved ref handoff ----------------------------------

    def test_candidate_promoted_to_approved_on_approval(self) -> None:
        """Approving a phase promotes candidate refs to approved."""
        state = _base_state("script", approved=False)
        ostate.set_candidate_ref(state, "script", "artifact:script:v3")
        ostate.set_candidate_ref(state, "scene_list", "artifact:scene_list:v2")

        # Simulate approval
        from film_pipeline.orchestration.nodes import approve_phase_node

        approved_state = approve_phase_node(state)
        approved_refs = ostate.get_approved_refs(approved_state)
        assert approved_refs.get("script") == "artifact:script:v3"
        assert approved_refs.get("scene_list") == "artifact:scene_list:v2"

    def test_downstream_resolves_approved_over_candidate(self) -> None:
        """Resolve artifact prefers approved ref over candidate."""
        state = _base_state("visual_dev", approved=True)
        ostate.set_candidate_ref(state, "script", "artifact:script:v3")
        ostate.set_approved_ref(state, "script", "artifact:script:v2")
        ref = ostate.resolve_artifact(state, "script")
        assert ref == "artifact:script:v2"

    # --- Provider health blocking -------------------------------------------

    def test_provider_blocked_blocks_generation_advance(self) -> None:
        """When approved in gen_planning and provider is blocked, cannot advance."""
        state = _base_state("gen_planning", approved=True)
        ostate.update_provider_health(state, "seedance", {"status": "blocked_quota"})
        r = compute_actions(state)
        assert r.next_action == "continue_unrelated_work"
        assert any(b.get("action", "").startswith("advance_to_generation") for b in r.blocked)

    def test_provider_blocked_allows_non_gen_work(self) -> None:
        """Provider blocked but non-generation phases advance normally."""
        state = _base_state("script", approved=True)
        ostate.update_provider_health(state, "seedance", {"status": "blocked_quota"})
        r = compute_actions(state)
        assert r.next_action == "advance_to_visual_dev"

    # --- Budget awareness ---------------------------------------------------

    def test_blocking_failure_routes_to_handler(self) -> None:
        """Blocking failure with no safe continuation routes to failure handler."""
        state = _base_state("generation", approved=True)
        ostate.add_failure_decision(
            state,
            {
                "decision_id": "fd1",
                "severity": "blocking",
                "safe_to_retry": False,
                "safe_to_continue_other_work": False,
                "human_message": "credit exhausted",
            },
        )
        r = compute_actions(state)
        assert r.next_action == "escalate_to_failure_handler"

    def test_failure_decisions_persisted(self) -> None:
        """Failure decisions survive state round-trip."""
        state = _base_state("generation")
        ostate.add_failure_decision(
            state,
            {"decision_id": "fd1", "severity": "blocking"},
        )
        assert len(ostate.get_failure_decisions(state)) == 1
        assert ostate.has_blocking_failure(state) is True

    # --- Convergence and escalation -----------------------------------------

    def test_stalled_phase_detected(self) -> None:
        """Five rounds without convergence marks phase as stalled."""
        state = _base_state("script")
        ostate.init_convergence(state, "script")
        for _ in range(5):
            ostate.increment_convergence_round(state, "script")
        assert ostate.is_stalled(state, "script", max_rounds=5) is True
