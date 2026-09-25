"""Compatibility aliases for :mod:`film_pipeline.orchestration._gate_facts`."""

from __future__ import annotations

from film_pipeline.orchestration._gate_facts import GATE_FACTS as GATE_FACTS
from film_pipeline.orchestration._gate_facts import OrchestratorGateFacts as OrchestratorGateFacts

# Private helpers still reached through this path during migration.

__all__ = [
    "GATE_FACTS",
    "OrchestratorGateFacts",
]
