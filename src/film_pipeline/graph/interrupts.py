"""Human approval interrupt points — 10 gates that pause the graph.

Each interrupt is a LangGraph interrupt() call that pauses execution until
the human (or mock human) acts through the MCP surface (approve_phase or
request_revision).
"""

from __future__ import annotations

from typing import Any

APPROVAL_GATE_LABELS: dict[str, str] = {
    "intake": "config",
    "constitution": "constitution",
    "development": "treatment",
    "script": "script",
    "visual_dev": "visual_bible",
    "shot_bible": "shot_bible",
    "gen_planning": "generation_spend",
    "generation": "generation_batch",
    "qc": "qc",
    "post": "assembly",
    "delivery": "final_delivery",
}


def interrupt_for_gate(
    state: dict[str, Any],
    phase: str,
    gate: str,
) -> dict[str, Any]:
    """Mark state for human interrupt at the given approval gate.

    Called by graph nodes when a phase completes and needs human review.
    Returns updated state with interrupt flags set.
    """
    state["human_approval_required"] = True
    state["human_approval_phase"] = gate
    state["current_phase"] = phase
    state["approved"] = False
    return state


def should_interrupt(state: dict[str, Any]) -> bool:
    """Check whether the graph is paused at a human approval gate."""
    val: object = state.get("human_approval_required", False)
    return val is True


def resolve_after_approval(state: dict[str, Any]) -> dict[str, Any]:
    """Clear interrupt flags after human approves."""
    state["human_approval_required"] = False
    state["human_approval_phase"] = ""
    state["approved"] = True
    return state
