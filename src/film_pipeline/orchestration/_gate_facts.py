"""Bind orchestrator state to the gate law's fact port.

`governance.action_routing` decides which actions are eligible; it needs
orchestrator facts but sits below `orchestration` and must not import it. This
adapter supplies them from the concrete state module.
"""

from __future__ import annotations

from typing import Any

from film_pipeline.orchestration.orchestrator_state import (
    ensure_orchestrator_state,
    get_approved_refs,
    get_blocked_providers,
    get_latest_failure_decision,
    has_blocking_failure,
    has_pending_revision,
)


class OrchestratorGateFacts:
    """The concrete :class:`~film_pipeline.governance.gate_facts.GateFacts`."""

    def ensure_state(self, state: dict[str, Any]) -> None:
        ensure_orchestrator_state(state)

    def has_blocking_failure(self, state: dict[str, Any]) -> bool:
        return has_blocking_failure(state)

    def latest_failure_decision(self, state: dict[str, Any]) -> dict[str, Any] | None:
        return get_latest_failure_decision(state)

    def blocked_providers(self, state: dict[str, Any]) -> list[str]:
        return get_blocked_providers(state)

    def has_pending_revision(self, state: dict[str, Any]) -> bool:
        return has_pending_revision(state)

    def approved_refs(self, state: dict[str, Any]) -> dict[str, str]:
        return get_approved_refs(state)


GATE_FACTS = OrchestratorGateFacts()

__all__ = ["GATE_FACTS", "OrchestratorGateFacts"]
