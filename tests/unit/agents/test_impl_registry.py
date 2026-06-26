"""Tests for concrete agent implementation registry."""

from __future__ import annotations

from film_pipeline.agents.impl.intake_agent import IntakeAgent
from film_pipeline.agents.impl.orchestrator_agent import OrchestratorAgent
from film_pipeline.agents.impl.registry import AGENT_CLASS_BY_ID, get_agent_class
from film_pipeline.agents.impl.screenwriter_agent import ScreenwriterAgent


def test_get_agent_class_resolves_core_agents() -> None:
    assert get_agent_class("intake-classifier-agent") is IntakeAgent
    assert get_agent_class("screenwriter-agent") is ScreenwriterAgent
    assert get_agent_class("orchestrator-agent") is OrchestratorAgent


def test_get_agent_class_unknown_returns_none() -> None:
    assert get_agent_class("not-a-real-agent") is None


def test_agent_class_registry_has_unique_keys() -> None:
    assert len(AGENT_CLASS_BY_ID) == len(set(AGENT_CLASS_BY_ID))
