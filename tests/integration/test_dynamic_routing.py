"""Integration test: dynamic routing — capability-based agent selection.

Proves that the routing system selects different agents for create, review,
and repair tasks, and that routing decisions are persisted as handoff records
queryable through the MCP tool.
"""

from __future__ import annotations

from pathlib import Path

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.graph.router import AgentRouteResult, route_agent


class TestRouteAgent:
    """Prove route_agent() selects different agents for create/review/repair."""

    def test_create_path_returns_default_agent(self) -> None:
        rt = StudioRuntime()
        rt.create_project("route-test", "Route Test")
        rt.set_active("route-test")

        state = rt.get_active() or {}
        result = route_agent(state, "script", task_type="create")

        assert isinstance(result, AgentRouteResult)
        assert result.agent_id == "screenwriter-agent"
        assert "create path" in result.routing_reason
        assert result.fallback is False

    def test_repair_path_selects_operator(self) -> None:
        rt = StudioRuntime()
        rt.create_project("route-test", "Route Test")
        rt.set_active("route-test")

        state = rt.get_active() or {}
        assert rt.services is not None
        result = route_agent(
            state,
            "script",
            task_type="repair",
            registry=rt.services.agent_registry,
        )

        assert isinstance(result, AgentRouteResult)
        # Repair selects failure-handling-agent (OPERATOR role, the repair agent)
        assert result.agent_id == "failure-handling-agent"
        assert "repair" in result.routing_reason.lower()
        assert result.fallback is False

    def test_review_path_selects_reviewer(self) -> None:
        rt = StudioRuntime()
        rt.create_project("route-test", "Route Test")
        rt.set_active("route-test")

        state = rt.get_active() or {}
        assert rt.services is not None
        result = route_agent(
            state,
            "script",
            task_type="review",
            registry=rt.services.agent_registry,
        )

        assert isinstance(result, AgentRouteResult)
        # Review selects clip-validator (VALIDATOR role, the QC agent)
        assert result.agent_id == "clip-validator"
        assert "review" in result.routing_reason.lower()
        assert result.fallback is False

    def test_different_phases_default_to_different_agents(self) -> None:
        """Each phase routes to its own default agent."""
        cases = [
            ("intake", "intake-classifier-agent"),
            ("constitution", "film-constitution-agent"),
            ("script", "screenwriter-agent"),
            ("shot_bible", "shot-design-agent"),
            ("qc", "clip-validator"),
        ]
        for phase, expected_agent in cases:
            result = route_agent({}, phase, task_type="create")
            assert result.agent_id == expected_agent, (
                f"Phase '{phase}' should route to '{expected_agent}', got '{result.agent_id}'"
            )

    def test_repair_without_registry_falls_back_to_default(self) -> None:
        """Without a registry, repair/review return default create agent."""
        result = route_agent({}, "script", task_type="repair")
        assert result.agent_id == "screenwriter-agent"
        assert result.fallback is False

    def test_preferred_capability_maps_task_type_without_registry(self) -> None:
        """preferred_capability infers task_type even when registry is None."""
        result = route_agent({}, "script", preferred_capability="review")
        assert result.agent_id == "screenwriter-agent"


class TestRoutingDecisions:
    """Prove routing decisions are persisted in state."""

    def test_routing_persisted_after_agent_run(self, tmp_path: Path) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("route-test", "Route Test")
        rt.set_active("route-test")

        # Run intake — should record a routing decision
        state = rt._run_phase_node(rt.get_active() or {}, "intake")

        decisions = state.get("_routing_decisions", [])
        assert len(decisions) >= 1, f"Expected routing decisions, got {list(state.keys())}"
        first = decisions[0]
        assert first["agent_id"] == "intake-classifier-agent"
        assert "create path" in first["routing_reason"]
        assert first["phase"] == "intake"
        assert "output_keys" in first
        assert "input_refs" in first

    def test_multiple_phases_accumulate_decisions(self, tmp_path: Path) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("route-test", "Route Test")
        rt.set_active("route-test")

        state = rt._run_phase_node(rt.get_active() or {}, "intake")
        state = rt._run_phase_node(state, "constitution")
        state = rt._run_phase_node(state, "development")

        decisions = state.get("_routing_decisions", [])
        assert len(decisions) >= 3
        agent_ids = [d["agent_id"] for d in decisions]
        assert "intake-classifier-agent" in agent_ids
        assert "film-constitution-agent" in agent_ids
        assert "treatment-agent" in agent_ids


class TestExplainRoutingMCP:
    """Prove routing decisions are queryable from project state."""

    def test_no_decisions_in_fresh_project(self, tmp_path: Path) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("empty-test", "Empty")
        rt.set_active("empty-test")

        active = rt.get_active()
        assert active is not None
        assert active.get("_routing_decisions", []) == []

    def test_decisions_populated_after_agent_run(self, tmp_path: Path) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("explain-test", "Explain Test")
        rt.set_active("explain-test")

        state = rt._run_phase_node(rt.get_active() or {}, "intake")
        rt.projects["explain-test"] = state

        decisions = state.get("_routing_decisions", [])
        assert len(decisions) >= 1
        assert decisions[0]["agent_id"] == "intake-classifier-agent"
        summary = decisions[0].get("routing_reason", "")
        assert "create path" in summary
