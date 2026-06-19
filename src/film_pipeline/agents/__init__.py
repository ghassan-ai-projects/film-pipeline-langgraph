"""Agent registry, RCTCO prompt runner, and agent handoff manager.

Each agent implements the :class:`BaseAgent` contract and is registered with
its capabilities, KB domains, and validator chain.
"""

from __future__ import annotations

from film_pipeline.agents.base import BaseAgent
from film_pipeline.agents.handoff import HandoffManager
from film_pipeline.agents.mvp import MVP_AGENTS
from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.runner import PromptRunner, RCTCOPrompt

__all__ = [
    "MVP_AGENTS",
    "AgentRegistry",
    "BaseAgent",
    "HandoffManager",
    "PromptRunner",
    "RCTCOPrompt",
]
