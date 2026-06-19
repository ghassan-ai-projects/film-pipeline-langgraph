"""Agent registry, RCTCO prompt runner, and agent handoff manager.

Each agent implements the :class:`BaseAgent` contract and is registered with
its capabilities, KB domains, and validator chain.
"""

from __future__ import annotations
