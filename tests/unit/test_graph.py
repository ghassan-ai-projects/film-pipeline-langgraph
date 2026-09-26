"""Tests for LangGraph graph module."""

from __future__ import annotations

from film_pipeline.orchestration import orchestrator_state as ostate
from film_pipeline.orchestration.edges import after_approval, after_phase
from film_pipeline.orchestration.nodes import (
    approve_phase_node,
    intake_node,
    request_revision_node,
)
from film_pipeline.orchestration.router import APPROVAL_GATES, PHASE_ORDER, compute_actions
from film_pipeline.studio.graph_factory import build_graph


class TestRouter:
    def test_intake_needs_approval(self) -> None:
        r = compute_actions({"current_phase": "intake", "approved": False, "issues": []})
        assert "approve_phase" in r.eligible

    def test_approved_advances(self) -> None:
        r = compute_actions(
            {
                "current_phase": "intake",
                "approved": True,
                "human_approval_required": False,
                "issues": [],
            }
        )
        assert "advance_to_constitution" in r.eligible

    def test_blocking_stops(self) -> None:
        r = compute_actions(
            {
                "current_phase": "script",
                "approved": True,
                "human_approval_required": False,
                "issues": [{"severity": "blocking"}],
            }
        )
        assert len(r.blocked) == 1

    def test_human_gate_priority(self) -> None:
        r = compute_actions(
            {
                "current_phase": "script",
                "approved": False,
                "human_approval_required": True,
                "issues": [],
            }
        )
        assert r.next_action == "wait_for_human"

    def test_human_gate_blocks_approval_when_stalled_with_blockers(self) -> None:
        r = compute_actions(
            {
                "current_phase": "shot_bible",
                "approved": False,
                "human_approval_required": True,
                "_stalled_phase": "shot_bible",
                "issues": [{"severity": "blocking"}],
            }
        )
        assert r.next_action == "wait_for_human"
        assert "approve_phase" not in r.eligible
        assert "escalate_to_human" in r.eligible
        assert r.blocked[0]["action"] == "approve_phase"

    def test_phases_count(self) -> None:
        assert len(PHASE_ORDER) == 11

    def test_gates_mapped(self) -> None:
        for p in PHASE_ORDER:
            assert p in APPROVAL_GATES

    # --- Orchestrator-aware router tests ---------------------------------

    def test_provider_blocked_offers_continue_unrelated(self) -> None:
        """When a provider is blocked in generation phase, offer continue_unrelated_work."""
        state: dict[str, object] = {
            "current_phase": "generation",
            "approved": True,
            "human_approval_required": False,
            "issues": [],
        }
        ostate.ensure_orchestrator_state(state)
        ostate.update_provider_health(state, "seedance", {"status": "blocked_quota"})
        r = compute_actions(state)
        assert r.next_action == "continue_unrelated_work"
        assert "continue_unrelated_work" in r.eligible

    def test_provider_healthy_in_non_gen_phase_advances(self) -> None:
        """When provider is blocked but we're in a non-gen phase, still advance."""
        state: dict[str, object] = {
            "current_phase": "script",
            "approved": True,
            "human_approval_required": False,
            "issues": [],
        }
        ostate.ensure_orchestrator_state(state)
        ostate.update_provider_health(state, "seedance", {"status": "blocked_quota"})
        r = compute_actions(state)
        assert r.next_action == "advance_to_visual_dev"

    def test_blocking_failure_routes_to_failure_handler(self) -> None:
        """Blocking failure decision should route to failure handler."""
        state: dict[str, object] = {
            "current_phase": "generation",
            "approved": True,
            "human_approval_required": False,
            "issues": [],
        }
        ostate.ensure_orchestrator_state(state)
        ostate.add_failure_decision(
            state,
            {
                "decision_id": "fd1",
                "severity": "blocking",
                "safe_to_retry": False,
                "safe_to_continue_other_work": False,
                "human_message": "quota exhausted",
            },
        )
        r = compute_actions(state)
        assert r.next_action == "escalate_to_failure_handler"

    def test_blocking_failure_with_safe_continuation(self) -> None:
        """Blocking failure in non-gen phase with safe_to_continue_other_work."""
        state: dict[str, object] = {
            "current_phase": "script",
            "approved": True,
            "human_approval_required": False,
            "issues": [],
        }
        ostate.ensure_orchestrator_state(state)
        ostate.add_failure_decision(
            state,
            {
                "decision_id": "fd1",
                "severity": "blocking",
                "safe_to_retry": False,
                "safe_to_continue_other_work": True,
                "human_message": "generation blocked but planning can continue",
            },
        )
        r = compute_actions(state)
        assert r.next_action == "continue_unrelated_work"

    def test_pending_revision_forces_revise(self) -> None:
        """Pending revision must be resolved before approval."""
        state: dict[str, object] = {
            "current_phase": "script",
            "approved": False,
            "human_approval_required": False,
            "issues": [],
        }
        ostate.ensure_orchestrator_state(state)
        ostate.add_revision_request(state, ["artifact:script:v1"])
        r = compute_actions(state)
        assert r.next_action == "revise"
        assert "approve_phase" not in r.eligible

    def test_blocking_issues_offer_escalate_to_human(self) -> None:
        """Blocking issues should offer escalate_to_human as option."""
        state: dict[str, object] = {
            "current_phase": "script",
            "approved": True,
            "human_approval_required": False,
            "issues": [{"severity": "blocking", "code": "IDENTITY_DRIFT"}],
        }
        r = compute_actions(state)
        assert "escalate_to_human" in r.eligible

    def test_happy_path_unchanged(self) -> None:
        """Straight-line phase progression still works when no blockers exist."""
        state: dict[str, object] = {
            "current_phase": "intake",
            "approved": True,
            "human_approval_required": False,
            "issues": [],
        }
        r = compute_actions(state)
        assert r.next_action == "advance_to_constitution"


class TestNodes:
    def test_intake_node(self) -> None:
        o = intake_node({})
        assert o["current_phase"] == "intake"

    def test_approve_node(self) -> None:
        o = approve_phase_node({"approved": False})
        assert o["approved"] is True

    def test_revision_node(self) -> None:
        o = request_revision_node({"issues": []})
        assert len(o["issues"]) == 1


class TestEdges:
    def test_after_phase_to_gate(self) -> None:
        assert (
            after_phase(
                {
                    "current_phase": "script",
                    "approved": False,
                    "human_approval_required": True,
                    "issues": [],
                }
            )
            == "consistency_check"
        )

    def test_after_approval_next(self) -> None:
        assert after_approval({"current_phase": "intake", "approved": True}) == "constitution"


class TestGraph:
    def test_compiles(self) -> None:
        assert build_graph() is not None


class TestSubgraphs:
    def test_qc_subgraph_importable(self) -> None:
        from film_pipeline.orchestration.subgraphs import qc

        assert qc.build_qc_subgraph() is not None
