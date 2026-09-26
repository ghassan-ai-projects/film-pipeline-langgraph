"""Tests for agent registry."""

from __future__ import annotations

import logging

import pytest

from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.roster import MVP_AGENTS
from film_pipeline.schemas.base import AgentFamily, AgentRole
from film_pipeline.schemas.handoff import AgentRegistration


class TestAgentRegistry:
    def test_register(self) -> None:
        registry = AgentRegistry()
        contract = AgentRegistration(
            agent_id="test-agent",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=["test"],
            input_artifacts=["input"],
            output_artifacts=["output"],
            allowed_kb_domains=["ops"],
        )
        registry.register(contract)
        assert len(registry) == 1
        assert "test-agent" in registry

    def test_register_duplicate_raises(self) -> None:
        registry = AgentRegistry()
        contract = AgentRegistration(
            agent_id="dup-agent",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=["test"],
            input_artifacts=["input"],
            output_artifacts=["output"],
            allowed_kb_domains=["ops"],
        )
        registry.register(contract)
        try:
            registry.register(contract)
            raise AssertionError("Expected ValueError")
        except ValueError:
            pass

    def test_register_unknown_model_profile_raises(self) -> None:
        registry = AgentRegistry()
        contract = AgentRegistration(
            agent_id="bad-model-agent",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=["test"],
            output_artifacts=["output"],
            allowed_kb_domains=["ops"],
            default_model_profile="missing-profile",
        )

        with pytest.raises(ValueError, match="unknown model profile"):
            registry.register(contract)

    def test_register_blank_capability_raises(self) -> None:
        registry = AgentRegistry()
        contract = AgentRegistration(
            agent_id="blank-capability-agent",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=[""],
            output_artifacts=["output"],
            allowed_kb_domains=["ops"],
        )

        with pytest.raises(ValueError, match="blank value"):
            registry.register(contract)

    def test_register_overlapping_kb_domains_raises(self) -> None:
        registry = AgentRegistry()
        contract = AgentRegistration(
            agent_id="overlap-agent",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=["test"],
            output_artifacts=["output"],
            allowed_kb_domains=["ops"],
            blocked_kb_domains=["ops"],
        )

        with pytest.raises(ValueError, match="both allows and blocks"):
            registry.register(contract)

    def test_register_unknown_kb_domain_warns_when_allowlist_configured(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        registry = AgentRegistry(known_kb_domains={"ops"})
        contract = AgentRegistration(
            agent_id="unknown-domain-agent",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=["test"],
            output_artifacts=["output"],
            allowed_kb_domains=["ops", "typo"],
        )

        with caplog.at_level(logging.WARNING, logger="film_pipeline.agents.registry"):
            registry.register(contract)

        assert "unknown KB domain" in caplog.text
        assert registry.lookup_by_id("unknown-domain-agent") == contract

    def test_register_unknown_output_artifact_raises_when_allowlist_configured(self) -> None:
        registry = AgentRegistry(known_output_artifacts={"script"})
        contract = AgentRegistration(
            agent_id="unknown-output-agent",
            family=AgentFamily.OPERATIONS,
            role=AgentRole.CREATOR,
            capabilities=["test"],
            output_artifacts=["review_report"],
            allowed_kb_domains=["ops"],
        )

        with pytest.raises(ValueError, match="unknown artifact"):
            registry.register(contract)

    def test_register_many(self) -> None:
        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)
        # Compared against the roster, not a literal: the point of the test is
        # that register_many takes every row, not that the roster is a size.
        assert len(registry) == len(MVP_AGENTS)

    def test_lookup_by_id(self) -> None:
        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)
        agent = registry.lookup_by_id("screenwriter-agent")
        assert agent is not None
        assert agent.role == AgentRole.CREATOR
        assert agent.family == AgentFamily.SCREENWRITING

    def test_lookup_by_id_missing(self) -> None:
        registry = AgentRegistry()
        assert registry.lookup_by_id("nonexistent") is None

    def test_lookup_by_capability(self) -> None:
        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)
        agents = registry.lookup_by_capability("dialogue")
        assert len(agents) == 1
        assert agents[0].agent_id == "screenwriter-agent"

    def test_lookup_by_capability_multiple(self) -> None:
        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)
        agents = registry.lookup_by_capability("error_classification")
        assert len(agents) == 1
        assert agents[0].agent_id == "failure-handling-agent"

    def test_lookup_by_family(self) -> None:
        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)
        agents = registry.lookup_by_family(AgentFamily.QC)
        assert len(agents) == 1  # clip-validator

    def test_lookup_by_role(self) -> None:
        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)
        agents = registry.lookup_by_role(AgentRole.ORCHESTRATOR)
        assert len(agents) == 1
        assert agents[0].agent_id == "orchestrator-agent"

    def test_lookup_by_role_validator(self) -> None:
        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)
        agents = registry.lookup_by_role(AgentRole.VALIDATOR)
        assert len(agents) == 1  # clip-validator

    def test_creator_and_validator_separate(self) -> None:
        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)
        for agent in registry.agents.values():
            if agent.role == AgentRole.VALIDATOR:
                assert agent.family == AgentFamily.QC

    def test_all_agents_have_capabilities(self) -> None:
        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)
        for agent in registry.agents.values():
            assert len(agent.capabilities) >= 1, f"{agent.agent_id} has no capabilities"

    def test_all_agents_have_output_artifacts(self) -> None:
        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)
        for agent in registry.agents.values():
            assert len(agent.output_artifacts) >= 1, f"{agent.agent_id} has no output artifacts"

    def test_all_agents_have_prompt_framework(self) -> None:
        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)
        for agent in registry.agents.values():
            assert agent.prompt_framework == "RCTCO"
