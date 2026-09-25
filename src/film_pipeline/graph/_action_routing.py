"""Compatibility aliases for the gate law, now owned by ``governance``.

`compute_actions` now takes the orchestrator facts explicitly; this shim binds
the concrete adapter so existing single-argument callers keep working.
"""

from __future__ import annotations

from typing import Any

from film_pipeline.governance.action_routing import RouterResult as RouterResult
from film_pipeline.governance.action_routing import compute_actions as _compute_actions
from film_pipeline.graph._gate_facts import GATE_FACTS


def compute_actions(state: dict[str, Any]) -> RouterResult:
    """Compute eligible actions using the concrete orchestrator facts."""
    return _compute_actions(state, GATE_FACTS)


__all__ = ["RouterResult", "compute_actions"]
