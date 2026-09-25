"""Structural reads of orchestrator-cached values.

`governance` sits below `orchestration` and must not import it. The few
orchestrator values the governance layer needs are declared here as namespace
lookups, so the dependency stays one-way: `orchestration` owns the state shape
and `governance` reads it by key.

This is deliberately minimal. It exists so the human-gate validators can read
the cached ExecutionBrief without an upward import edge, not as a general
orchestrator-state facade.
"""

from __future__ import annotations

from typing import Any

#: Orchestrator namespace prefix, mirrored from `orchestrator_state`.
_ORCH_NS = "_orchestrator"


def get_execution_brief(state: dict[str, Any]) -> dict[str, Any] | None:
    """Return the cached ExecutionBrief payload, or ``None`` when unset."""
    value = state.get(f"{_ORCH_NS}__execution_brief")
    if value is None:
        return None
    return value if isinstance(value, dict) else None


def get_approved_refs(state: dict[str, Any]) -> dict[str, str]:
    """Return the approved artifact ref for each artifact id."""
    value = state.get(f"{_ORCH_NS}__approved_refs", {})
    return dict(value) if isinstance(value, dict) else {}
