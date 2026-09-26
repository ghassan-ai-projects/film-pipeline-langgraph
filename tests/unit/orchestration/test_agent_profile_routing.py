"""Tests for agent-to-model-profile routing in _run_agent()."""

from __future__ import annotations

from film_pipeline.orchestration.nodes import _AGENT_PROFILE_MAP


class TestAgentProfileMap:
    def test_creative_agents_use_creative_profiles(self) -> None:
        """Creative agents must map to creative_writer or visual_reasoner."""
        assert _AGENT_PROFILE_MAP["film-constitution-agent"] == "creative_writer"
        assert _AGENT_PROFILE_MAP["treatment-agent"] == "creative_writer"
        assert _AGENT_PROFILE_MAP["screenwriter-agent"] == "creative_writer"
        assert _AGENT_PROFILE_MAP["shot-design-agent"] == "creative_writer"
        assert _AGENT_PROFILE_MAP["reference-strategy-planner"] == "visual_reasoner"
        assert _AGENT_PROFILE_MAP["visual-dev-agent"] == "visual_reasoner"

    def test_validator_agents_use_strict_profiles(self) -> None:
        """Validator agents must map to strict_validator."""
        assert _AGENT_PROFILE_MAP["clip-validator"] == "strict_validator"
        assert _AGENT_PROFILE_MAP["structure-extractor-agent"] == "strict_validator"

    def test_operational_agents_use_operations_triage(self) -> None:
        """Operational agents must map to operations_triage."""
        assert _AGENT_PROFILE_MAP["intake-classifier-agent"] == "operations_triage"
        assert _AGENT_PROFILE_MAP["provider-planning-agent"] == "operations_triage"
        assert _AGENT_PROFILE_MAP["failure-handling-agent"] == "operations_triage"

    def test_unknown_agent_falls_back(self) -> None:
        """Unmapped agents get operations_triage as default."""
        assert (
            _AGENT_PROFILE_MAP.get("nonexistent-agent", "operations_triage") == "operations_triage"
        )

    def test_all_mvp_agents_have_profile_entries(self) -> None:
        """Every MVP-registered agent must have an entry in _AGENT_PROFILE_MAP."""
        from film_pipeline.agents.roster import MVP_AGENTS

        for agent in MVP_AGENTS:
            assert agent.agent_id in _AGENT_PROFILE_MAP, f"Missing profile for {agent.agent_id}"
