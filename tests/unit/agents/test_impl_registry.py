"""Tests for the agent implementation binding in ``agents.registry``."""

from __future__ import annotations

from film_pipeline.agents.impl.intake_agent import IntakeAgent
from film_pipeline.agents.impl.orchestrator_agent import OrchestratorAgent
from film_pipeline.agents.impl.screenwriter_agent import ScreenwriterAgent
from film_pipeline.agents.registry import AGENT_CLASS_BY_ID, get_agent_class
from film_pipeline.agents.roster import MVP_AGENTS


def test_get_agent_class_resolves_core_agents() -> None:
    assert get_agent_class("intake-classifier-agent") is IntakeAgent
    assert get_agent_class("screenwriter-agent") is ScreenwriterAgent
    assert get_agent_class("orchestrator-agent") is OrchestratorAgent


def test_get_agent_class_unknown_returns_none() -> None:
    assert get_agent_class("not-a-real-agent") is None


def test_class_bindings_cover_the_roster_exactly() -> None:
    """The binding table and the roster name the same set of agent ids.

    This replaces the old ``len(AGENT_CLASS_BY_ID) == len(set(...))``
    assertion, which was vacuous — a dict cannot have duplicate keys, so it
    could never fail. The real invariant is parity with the roster: a key the
    roster does not register is an unreachable alias (the deleted
    ``visual-dev-agent``), and a roster row with no key is a dead agent.
    """
    assert set(AGENT_CLASS_BY_ID) == {agent.agent_id for agent in MVP_AGENTS}
