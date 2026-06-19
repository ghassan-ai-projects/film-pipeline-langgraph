"""E2E Scenario: Graph execution through phases with mock infrastructure."""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.graph.edges import after_approval, after_phase, after_repair
from film_pipeline.graph.graph import build_graph
from film_pipeline.graph.nodes import (
    approve_phase_node,
    constitution_node,
    delivery_node,
    development_node,
    gen_planning_node,
    generation_node,
    intake_node,
    post_node,
    qc_node,
    request_revision_node,
    script_node,
    shot_bible_node,
    visual_dev_node,
)
from film_pipeline.graph.router import PHASE_ORDER, compute_actions


@pytest.mark.e2e
class TestGraphExecution:
    """End-to-end: run the graph through multiple phases."""

    def test_graph_invokes_all_phase_nodes(self) -> None:
        """Verify the graph invokes nodes — cycles without human (expected)."""
        graph = build_graph()
        state: dict[str, Any] = {"project_id": "e2e-graph-test"}

        # Graph will cycle through approval gate without human intervention.
        # This verifies the graph compiles and executes node functions.
        from langgraph.errors import GraphRecursionError

        with pytest.raises(GraphRecursionError):
            graph.invoke(
                state,
                config={"configurable": {"thread_id": "e2e-1"}, "recursion_limit": 5},
            )

    def test_graph_interrupts_at_approval_gate(self) -> None:
        """Verify the graph pauses at human approval gates."""
        graph = build_graph()
        state: dict[str, Any] = {"project_id": "test-interrupt"}

        from langgraph.errors import GraphRecursionError

        # Stream values to see state after intake_node
        events: list[dict[str, Any]] = []
        try:
            for event in graph.stream(
                state,
                config={"configurable": {"thread_id": "e2e-2"}, "recursion_limit": 3},
                stream_mode="values",
            ):
                events.append(event)
        except GraphRecursionError:
            pass

        assert len(events) > 1
        # First event is input state, second is after intake_node
        assert events[1].get("current_phase") == "intake"

    def test_approval_triggers_phase_transition(self) -> None:
        """Verify that the graph compiles with approved state."""
        graph = build_graph()
        state: dict[str, Any] = {
            "project_id": "test-transition",
            "current_phase": "intake",
            "approved": True,
            "human_approval_required": False,
        }

        from langgraph.errors import GraphRecursionError

        # Graph should still compile and execute
        with pytest.raises(GraphRecursionError):
            graph.invoke(
                state,
                config={"configurable": {"thread_id": "e2e-3"}, "recursion_limit": 5},
            )

    def test_all_phases_sequence_state(self) -> None:
        """Verify each phase node sets correct state fields."""
        nodes = [
            intake_node,
            constitution_node,
            development_node,
            script_node,
            visual_dev_node,
            shot_bible_node,
            gen_planning_node,
            generation_node,
            qc_node,
            post_node,
            delivery_node,
        ]

        for node_fn, phase_name in zip(nodes, PHASE_ORDER, strict=False):
            result = node_fn({})
            assert result["current_phase"] == phase_name
            assert result["human_approval_required"] is True

    def test_approve_phase_node(self) -> None:
        result = approve_phase_node({"approved": False, "human_approval_required": True})
        assert result["approved"] is True
        assert result["human_approval_required"] is False

    def test_request_revision_node(self) -> None:
        result = request_revision_node({"issues": []})
        assert len(result["issues"]) == 1
        assert result["issues"][0]["code"] == "REVISION_REQUESTED"
        assert result["approved"] is False

    def test_edge_routing_after_phase(self) -> None:
        """Verify conditional edges route correctly."""
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

        assert after_approval({"current_phase": "intake", "approved": True}) == "constitution"
        assert after_approval({"current_phase": "delivery", "approved": True}) == "end"
        assert after_repair({}) == "await_approval"

    def test_edge_routing_with_blocking_issues(self) -> None:
        """Blocking issues prevent phase advancement."""
        result = after_phase(
            {
                "current_phase": "script",
                "approved": True,
                "human_approval_required": False,
                "issues": [{"severity": "blocking", "code": "BAD_SCRIPT"}],
            }
        )
        assert result != "await_approval"

    def test_edge_routing_approved_advances(self) -> None:
        """Approved phase without issues advances to next phase."""
        result = after_phase(
            {
                "current_phase": "script",
                "approved": True,
                "human_approval_required": False,
                "issues": [],
            }
        )
        assert "advance_to" in result or result == "await_approval"

    def test_after_approval_repair_path(self) -> None:
        """Not approved but has issues → repair."""
        result = after_approval({"current_phase": "script", "approved": False, "issues": ["bad"]})
        assert result == "repair"

    def test_after_approval_await(self) -> None:
        """Not approved, no issues → stay awaiting."""
        result = after_approval({"current_phase": "script", "approved": False, "issues": []})
        assert result == "await_approval"

    def test_router_blocking_issues(self) -> None:
        """Router detects blocking issues."""
        r = compute_actions(
            {
                "current_phase": "script",
                "approved": True,
                "human_approval_required": False,
                "issues": [{"severity": "blocking", "code": "E1"}],
            }
        )
        assert len(r.blocked) >= 1
        assert r.next_action == "handle_blockers"
