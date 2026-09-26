"""Agent registry, RCTCO prompt runner, and agent roster.

Each agent implements the :class:`BaseAgent` contract and is registered with
its capabilities, KB domains, and validator chain.

Handoff records are owned by the graph: ``orchestration.nodes._agent_handoff``
records routing decisions on the state channels, and ``schemas.handoff`` defines
the ``AgentHandoff`` record. There is no in-process handoff manager — the former
``agents.handoff.HandoffManager`` had no production caller.
"""

from __future__ import annotations

from film_pipeline.agents.base import BaseAgent
from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.roster import MVP_AGENTS
from film_pipeline.agents.runner import PromptRunner, RCTCOPrompt

__all__ = [
    "MVP_AGENTS",
    "AgentRegistry",
    "BaseAgent",
    "PromptRunner",
    "RCTCOPrompt",
]
