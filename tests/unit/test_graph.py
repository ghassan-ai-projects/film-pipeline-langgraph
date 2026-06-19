"""Tests for LangGraph graph module."""

from __future__ import annotations

from film_pipeline.graph.edges import after_approval, after_phase
from film_pipeline.graph.graph import build_graph
from film_pipeline.graph.nodes import (
    approve_phase_node,
    intake_node,
    request_revision_node,
)
from film_pipeline.graph.router import APPROVAL_GATES, PHASE_ORDER, compute_actions


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

    def test_phases_count(self) -> None:
        assert len(PHASE_ORDER) == 11

    def test_gates_mapped(self) -> None:
        for p in PHASE_ORDER:
            assert p in APPROVAL_GATES


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
            == "await_approval"
        )

    def test_after_approval_next(self) -> None:
        assert after_approval({"current_phase": "intake", "approved": True}) == "constitution"


class TestGraph:
    def test_compiles(self) -> None:
        assert build_graph() is not None
