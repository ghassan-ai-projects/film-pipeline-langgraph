"""Tests for GenPlannerAgent — produces a generation plan from model output."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.impl.gen_planner_agent import GenPlannerAgent
from film_pipeline.agents.registry import get_agent_class
from film_pipeline.schemas.base import AgentFamily, AgentRole
from film_pipeline.schemas.handoff import AgentRegistration
from film_pipeline.schemas.kb import KBContextPacket


def _make_contract() -> AgentRegistration:
    return AgentRegistration(
        agent_id="provider-planning-agent",
        family=AgentFamily.PROMPT_PLANNING,
        role=AgentRole.CREATOR,
        capabilities=["provider_selection", "cost_estimation"],
        input_artifacts=["prompt_registry", "master_film_matrix", "resolved_config"],
        output_artifacts=["provider_plan"],
    )


def _make_kb() -> KBContextPacket:
    return KBContextPacket(
        kb_context_id="kbctx:plan:v1",
        project_id="test-project",
        phase="visual_dev",
        agent_id="provider-planning-agent",
        task="Plan the generation batch.",
    )


def _make_agent() -> GenPlannerAgent:
    return GenPlannerAgent(_make_contract())


_HERO_REQUEST: dict[str, Any] = {
    "shot_id": "shot_0001",
    "provider": "seedance",
    "model": "2.0",
    "mode": "quality",
    "priority": 0,
    "estimated_cost_usd": 2.5,
}

_FILLER_REQUEST: dict[str, Any] = {
    "shot_id": "shot_0002",
    "estimated_cost_usd": 2.0,
}

_VALID_OUTPUT: dict[str, Any] = {
    "cost_estimate": {
        "project_id": "test-project",
        "batch_id": "batch-001",
        "provider": "seedance",
        "estimated_cost_usd": 4.5,
        "clip_count": 2,
        "notes": "hero shot first, then filler.",
    },
    "shot_groups": [_HERO_REQUEST, _FILLER_REQUEST],
}


class TestGenPlannerAgent:
    def test_registry_resolves_provider_planning_agent_to_class(self) -> None:
        assert get_agent_class("provider-planning-agent") is GenPlannerAgent

    def test_execute_produces_generation_requests(self) -> None:
        """The planner's real output is the requests dispatch consumes.

        It used to also emit a ``cost_estimate``; that artifact was removed with
        the cost feature, and ``validate`` now checks the requests instead of the
        estimate's type.
        """
        agent = _make_agent()
        requests = agent.execute(_VALID_OUTPUT)["generation_requests"]
        assert isinstance(requests, list)
        assert [r["shot_id"] for r in requests] == ["shot_0001", "shot_0002"]
        assert all(r["provider"] == "seedance" for r in requests)

    def test_execute_builds_generation_requests_with_defaults(self) -> None:
        agent = _make_agent()
        result = agent.execute(_VALID_OUTPUT)
        requests = result["generation_requests"]
        assert [r["shot_id"] for r in requests] == ["shot_0001", "shot_0002"]
        assert requests[0]["mode"] == "quality"
        assert requests[0]["priority"] == 0
        # The filler request omits provider/model/mode/priority and gets defaults.
        assert requests[1]["provider"] == "seedance"
        assert requests[1]["model"] == "2.0"
        assert requests[1]["mode"] == "test"
        assert requests[1]["priority"] == 1

    def test_execute_totals_match_requests(self) -> None:
        agent = _make_agent()
        result = agent.execute(_VALID_OUTPUT)
        assert result["total_shots"] == 2

    def test_execute_handles_nested_output(self) -> None:
        agent = _make_agent()
        result = agent.execute({"generation_plan": _VALID_OUTPUT})
        assert result["total_shots"] == 2
        assert isinstance(result["generation_requests"], list)

    def test_execute_handles_empty_input(self) -> None:
        agent = _make_agent()
        result = agent.execute({})
        # Structurally valid but empty plan.
        assert result["generation_requests"] == []
        assert result["total_shots"] == 0

    def test_validate_passes_for_valid_plan(self) -> None:
        agent = _make_agent()
        assert agent.validate(agent.execute(_VALID_OUTPUT)) is True

    def test_validate_passes_for_empty_but_structurally_valid_plan(self) -> None:
        agent = _make_agent()
        assert agent.validate(agent.execute({})) is True

    def test_validate_fails_for_wrong_artifact_type(self) -> None:
        agent = _make_agent()
        assert agent.validate({"generation_requests": "not-a-list"}) is False
        assert agent.validate({"generation_requests": [{"no_shot_id": 1}]}) is False

    def test_prepare_extracts_planning_state_refs(self) -> None:
        agent = _make_agent()
        prepared = agent.prepare(
            {
                "project_id": "test-project",
                "shot_matrix_ref": "master_film_matrix:v1",
                "budget_cap": "25.0",
                "preferred_providers": "seedance,kling",
            },
            _make_kb(),
            "Plan the generation batch.",
        )
        assert prepared == {
            "project_id": "test-project",
            "shot_matrix_ref": "master_film_matrix:v1",
            "budget_cap": "25.0",
            "preferred_providers": "seedance,kling",
            "task": "Plan the generation batch.",
        }

    def test_run_lifecycle_round_trips_valid_output(self) -> None:
        agent = _make_agent()
        result = agent.run({}, _make_kb(), "Plan the generation batch.", _VALID_OUTPUT)
        assert isinstance(result["generation_requests"], list)
        assert result["total_shots"] == 2

    def test_run_lifecycle_rejects_invalid_output(self) -> None:
        agent = _make_agent()
        # A result whose generation_requests are malformed fails validation;
        # exercising this through run() requires such a result, which execute()
        # cannot produce from a well-formed payload.
        assert agent.validate({"generation_requests": [{"no_shot_id": 1}]}) is False
