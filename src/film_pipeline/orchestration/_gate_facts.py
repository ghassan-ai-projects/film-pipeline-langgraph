"""Bind orchestrator state to the gate law's fact port.

`governance.action_routing` decides which actions are eligible; it needs
orchestrator facts but sits below `orchestration` and must not import it. This
adapter supplies them from the concrete state module.
"""

from __future__ import annotations

from typing import Any

from film_pipeline.orchestration import orchestrator_state as ostate


class OrchestratorGateFacts:
    """The concrete :class:`~film_pipeline.governance.gate_facts.GateFacts`."""

    def ensure_state(self, state: dict[str, Any]) -> None:
        ostate.ensure_orchestrator_state(state)

    def has_blocking_failure(self, state: dict[str, Any]) -> bool:
        return ostate.has_blocking_failure(state)

    def latest_failure_decision(self, state: dict[str, Any]) -> dict[str, Any] | None:
        return ostate.get_latest_failure_decision(state)

    def blocked_providers(self, state: dict[str, Any]) -> list[str]:
        return ostate.get_blocked_providers(state)

    def has_pending_revision(self, state: dict[str, Any]) -> bool:
        return ostate.has_pending_revision(state)

    def approved_refs(self, state: dict[str, Any]) -> dict[str, str]:
        return ostate.get_approved_refs(state)


GATE_FACTS = OrchestratorGateFacts()

__all__ = ["GATE_FACTS", "OrchestratorGateFacts"]
