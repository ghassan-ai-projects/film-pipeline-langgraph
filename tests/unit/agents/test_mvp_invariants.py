"""Invariant tests for the wired MVP agent roster.

Every agent declared in ``MVP_AGENTS`` must be executable end-to-end:
- a concrete implementation class
- a dedicated prompt template
- a resolvable model profile
- a mock response for mock-mode execution
"""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.agents.impl.registry import get_agent_class
from film_pipeline.agents.model_routing import ModelRouter
from film_pipeline.agents.mvp import MVP_AGENTS
from film_pipeline.agents.prompt_templates.registry import get_registry
from film_pipeline.app.mock_responses import default_mock_responses


class TestMVPAgentInvariants:
    """Each MVP agent is wired with class, template, profile, and mock data."""

    @pytest.fixture
    def mock_responses(self) -> dict[str, dict[str, Any]]:
        return default_mock_responses()

    @pytest.fixture
    def model_router(self) -> ModelRouter:
        return ModelRouter()

    @pytest.fixture
    def prompt_registry(self) -> Any:
        return get_registry()

    @pytest.mark.parametrize("agent", MVP_AGENTS, ids=lambda a: a.agent_id)
    def test_agent_has_implementation_class(self, agent: Any) -> None:
        assert get_agent_class(agent.agent_id) is not None, (
            f"{agent.agent_id} has no implementation class"
        )

    @pytest.mark.parametrize("agent", MVP_AGENTS, ids=lambda a: a.agent_id)
    def test_agent_has_dedicated_prompt_template(self, agent: Any, prompt_registry: Any) -> None:
        assert prompt_registry.get(agent.agent_id) is not None, (
            f"{agent.agent_id} has no dedicated prompt template"
        )

    @pytest.mark.parametrize("agent", MVP_AGENTS, ids=lambda a: a.agent_id)
    def test_agent_model_profile_is_resolvable(self, agent: Any, model_router: ModelRouter) -> None:
        profile = agent.default_model_profile
        # The orchestrator alias is accepted by AgentRegistry but must map to a
        # real profile at runtime; the wired agents now use concrete profiles.
        assert profile in model_router.list_profiles(), (
            f"{agent.agent_id} references unknown model profile '{profile}'"
        )
        # Prove the router can actually resolve it.
        assert model_router.resolve_or_raise(profile)

    @pytest.mark.parametrize("agent", MVP_AGENTS, ids=lambda a: a.agent_id)
    def test_agent_has_mock_response(
        self, agent: Any, mock_responses: dict[str, dict[str, Any]]
    ) -> None:
        assert agent.agent_id in mock_responses, (
            f"{agent.agent_id} has no mock response for mock-mode execution"
        )
        assert isinstance(mock_responses[agent.agent_id], dict)
        assert mock_responses[agent.agent_id], f"{agent.agent_id} mock response is empty"
