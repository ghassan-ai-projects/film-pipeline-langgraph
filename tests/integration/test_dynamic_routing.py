"""Integration tests for state-driven routing via compute_actions()/after_phase()."""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.orchestration.edges import after_approval, after_phase
from film_pipeline.orchestration.router import APPROVAL_GATES, PHASE_ORDER, compute_actions


@pytest.mark.integration
class TestComputeActions:
    """Router selects the right action given runtime state."""

    def test_human_approval_required_waits(self) -> None:
        state = _base_state(phase="constitution")
        state["human_approval_required"] = True
        result = compute_actions(state)
        assert result.next_action == "wait_for_human"
        assert result.human_gate == APPROVAL_GATES["constitution"]
        assert "approve_phase" in result.eligible

    def test_blocking_failure_with_safe_continue(self) -> None:
        state = _base_state(phase="gen_planning")
        state["_orchestrator__failure_decisions"].append(
            {
                "severity": "blocking",
                "human_message": "provider down",
                "safe_to_continue_other_work": True,
            }
        )
        result = compute_actions(state)
        assert result.next_action == "continue_unrelated_work"
        assert "advance_to_generation" in {b["action"] for b in result.blocked}

    def test_blocking_failure_without_safe_continue_escalates(self) -> None:
        state = _base_state(phase="generation")
        state["_orchestrator__failure_decisions"].append(
            {
                "severity": "blocking",
                "human_message": "fatal",
                "safe_to_continue_other_work": False,
            }
        )
        result = compute_actions(state)
        assert result.next_action == "escalate_to_failure_handler"

    def test_provider_blocked_generation_phase_reroutes(self) -> None:
        state = _base_state(phase="generation")
        state["_orchestrator__provider_health_snapshot"] = {
            "mock-video-provider": {"status": "blocked_quota"},
        }
        result = compute_actions(state)
        assert result.next_action == "continue_unrelated_work"
        assert "advance_to_generation" in {b["action"] for b in result.blocked}

    def test_provider_blocked_before_generation_blocks_advance(self) -> None:
        state = _base_state(phase="gen_planning", approved=True)
        state["_orchestrator__provider_health_snapshot"] = {
            "mock-video-provider": {"status": "blocked_quota"},
        }
        result = compute_actions(state)
        assert result.next_action == "continue_unrelated_work"
        assert "advance_to_generation" in {b["action"] for b in result.blocked}

    def test_budget_blocked_escalates(self) -> None:
        state = _base_state(phase="generation", approved=True)
        state["_orchestrator__budget_snapshot"]["threshold_exceeded"] = True
        result = compute_actions(state)
        assert result.next_action == "escalate_to_human"
        assert "advance_phase" in {b["action"] for b in result.blocked}

    def test_blocking_issues_route_to_repair(self) -> None:
        state = _base_state(phase="shot_bible")
        state["issues"].append(
            {"severity": "blocking", "code": "shot_count_mismatch", "message": "too few shots"}
        )
        result = compute_actions(state)
        assert result.next_action == "handle_blockers"
        assert "repair" in result.eligible

    def test_pending_revision_routes_to_revise(self) -> None:
        state = _base_state(phase="script")
        state["_orchestrator__pending_revisions"].append(
            {"artifact_refs": ["artifact:script:v1"], "resolved": False}
        )
        result = compute_actions(state)
        assert result.next_action == "revise"
        assert "revise" in result.eligible

    def test_unapproved_phase_presents_review_package(self) -> None:
        state = _base_state(phase="visual_dev", approved=False)
        result = compute_actions(state)
        assert result.next_action == "present_review_package"
        assert result.human_gate == APPROVAL_GATES["visual_dev"]

    def test_approved_phase_advances(self) -> None:
        state = _base_state(phase="constitution", approved=True)
        result = compute_actions(state)
        assert result.next_action == "advance_to_development"

    def test_approved_final_phase_wraps(self) -> None:
        state = _base_state(phase="delivery", approved=True)
        result = compute_actions(state)
        assert result.next_action == "wrap"


def _base_state(*, phase: str = "intake", approved: bool = False) -> dict[str, Any]:
    return {
        "current_phase": phase,
        "approved": approved,
        "human_approval_required": False,
        "issues": [],
        "_orchestrator__candidate_refs": {},
        "_orchestrator__approved_refs": {},
        "_orchestrator__active_review_cycles": [],
        "_orchestrator__pending_revisions": [],
        "_orchestrator__routing_decisions": [],
        "_orchestrator__convergence": {},
        "_orchestrator__failure_decisions": [],
        "_orchestrator__provider_health_snapshot": {},
        "_orchestrator__budget_snapshot": {
            "cap_usd": 0.0,
            "spent_usd": 0.0,
            "remaining_usd": 0.0,
            "threshold_exceeded": False,
        },
        "_orchestrator__execution_brief": {},
    }


@pytest.mark.integration
class TestAfterPhaseEdges:
    """after_phase() maps RouterResult actions to graph node names."""

    def test_wait_for_human_goes_to_consistency_check(self) -> None:
        state = _base_state(phase="constitution")
        state["human_approval_required"] = True
        assert after_phase(state) == "consistency_check"

    def test_handle_blockers_goes_to_repair(self) -> None:
        state = _base_state(phase="shot_bible")
        state["issues"].append(
            {"severity": "blocking", "code": "shot_count_mismatch", "message": "x"}
        )
        assert after_phase(state) == "repair"

    def test_advance_goes_to_phase_node(self) -> None:
        state = _base_state(phase="generation", approved=True)
        assert after_phase(state) == "qc"

    def test_advance_to_end_goes_to_end(self) -> None:
        state = _base_state(phase="delivery", approved=True)
        assert after_phase(state) == "end"

    def test_repair_action_goes_to_await_approval(self) -> None:
        state = _base_state(phase="script")
        state["_orchestrator__pending_revisions"].append(
            {"artifact_refs": ["artifact:script:v1"], "resolved": False}
        )
        assert after_phase(state) == "await_approval"

    def test_unknown_action_defaults_to_consistency_check(self) -> None:
        state = _base_state(phase="constitution", approved=False)
        # present_review_package is not in the explicit action map, so the
        # fallback path should still route through the human gate.
        assert after_phase(state) == "consistency_check"


@pytest.mark.integration
class TestAfterApprovalEdges:
    """after_approval() maps post-approval state to the next node."""

    def test_approved_intake_advances_to_constitution(self) -> None:
        assert after_approval({"current_phase": "intake", "approved": True}) == "constitution"

    def test_unapproved_with_issues_routes_to_repair(self) -> None:
        assert (
            after_approval(
                {"current_phase": "intake", "approved": False, "issues": [{"severity": "blocking"}]}
            )
            == "repair"
        )

    def test_stalled_stays_at_gate(self) -> None:
        assert (
            after_approval(
                {
                    "current_phase": "shot_bible",
                    "approved": False,
                    "issues": [{"severity": "blocking"}],
                    "_orchestrator__convergence": {
                        "shot_bible": {"round_count": 5, "stalled": True, "escalation_reason": "x"},
                    },
                }
            )
            == "await_approval"
        )

    def test_final_phase_ends(self) -> None:
        assert after_approval({"current_phase": "delivery", "approved": True}) == "end"


@pytest.mark.integration
class TestPhaseOrderContract:
    """Phase order is stable and gates exist for every phase."""

    def test_approval_gate_for_every_phase(self) -> None:
        for phase in PHASE_ORDER:
            assert phase in APPROVAL_GATES, f"Missing approval gate for {phase}"
