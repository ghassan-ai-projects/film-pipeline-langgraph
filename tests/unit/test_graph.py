"""Tests for LangGraph graph module."""

from __future__ import annotations

from film_pipeline.graph.edges import after_approval, after_phase
from film_pipeline.graph.graph import build_graph
from film_pipeline.graph.interrupts import (
    APPROVAL_GATE_LABELS,
    interrupt_for_gate,
    resolve_after_approval,
    should_interrupt,
)
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


class TestInterrupts:
    def test_interrupt_for_gate(self) -> None:
        state: dict[str, object] = {}
        result = interrupt_for_gate(state, "script", "script")
        assert result["human_approval_required"] is True
        assert result["human_approval_phase"] == "script"
        assert result["current_phase"] == "script"

    def test_should_interrupt_true(self) -> None:
        assert should_interrupt({"human_approval_required": True}) is True

    def test_should_interrupt_false(self) -> None:
        assert should_interrupt({"human_approval_required": False}) is False
        assert should_interrupt({}) is False

    def test_resolve_after_approval(self) -> None:
        state: dict[str, object] = {
            "human_approval_required": True,
            "human_approval_phase": "script",
            "approved": False,
        }
        result = resolve_after_approval(state)
        assert result["human_approval_required"] is False
        assert result["human_approval_phase"] == ""
        assert result["approved"] is True

    def test_all_phases_have_gate_label(self) -> None:
        for phase in PHASE_ORDER:
            assert phase in APPROVAL_GATE_LABELS


class TestSubgraphs:
    def test_subgraphs_importable(self) -> None:
        from film_pipeline.graph.subgraphs import (
            constitution,
            delivery,
            development,
            gen_planning,
            generation,
            intake,
            post,
            qc,
            screenwriting,
            shot_bible,
            visual_dev,
        )

        assert constitution is not None
        assert delivery is not None
        assert development is not None
        assert gen_planning is not None
        assert generation is not None
        assert intake is not None
        assert post is not None
        assert qc is not None
        assert screenwriting is not None
        assert shot_bible is not None
        assert visual_dev is not None
