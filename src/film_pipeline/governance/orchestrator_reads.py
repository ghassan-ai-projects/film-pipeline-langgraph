"""Structural reads of orchestrator-cached values.

`governance` sits below `orchestration` and must not import it. The few
orchestrator values the governance layer needs are declared here as namespace
lookups, so the dependency stays one-way: `orchestration` owns the state shape
and `governance` reads it by key.

This is deliberately minimal. It exists so the human-gate validators can read
the cached ExecutionBrief without an upward import edge, not as a general
orchestrator-state facade.

**`ORCH_NS` has exactly one definition, and it is here.** The namespace prefix
used to be written out twice — once here and once in `orchestration`, which now
imports it back. Two copies of one literal is the "one policy, N sites" shape:
had they drifted, `get_execution_brief` would have silently returned `None` and
the brief gate would have seen no brief. `orchestration -> governance` is already
an edge, so the import adds no cycle.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

ORCH_NS = "_orchestrator"


def get_execution_brief(state: Mapping[str, object]) -> dict[str, Any] | None:
    """Return the cached ExecutionBrief payload, or ``None`` when unset."""
    value = state.get(f"{ORCH_NS}__execution_brief")
    if value is None:
        return None
    return value if isinstance(value, dict) else None


def get_approved_refs(state: Mapping[str, object]) -> dict[str, str]:
    """Return the approved artifact ref for each artifact id."""
    value = state.get(f"{ORCH_NS}__approved_refs", {})
    return dict(value) if isinstance(value, dict) else {}


__all__ = ["ORCH_NS", "get_approved_refs", "get_execution_brief"]
