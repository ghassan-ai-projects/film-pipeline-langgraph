"""Dynamic action router — computes eligible and blocked actions per state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PHASE_ORDER = [
    "intake",
    "constitution",
    "development",
    "script",
    "visual_dev",
    "shot_bible",
    "gen_planning",
    "generation",
    "qc",
    "post",
    "delivery",
]

APPROVAL_GATES = {
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


@dataclass
class RouterResult:
    eligible: list[str] = field(default_factory=list)
    blocked: list[dict[str, str]] = field(default_factory=list)
    next_action: str = ""
    human_gate: str = ""


def compute_actions(state: dict[str, Any]) -> RouterResult:
    phase = state.get("current_phase", "intake")
    approved = state.get("approved", False)
    human_required = state.get("human_approval_required", False)
    issues: list[dict[str, Any]] = state.get("issues", [])

    result = RouterResult()

    if human_required:
        result.eligible = ["approve_phase", "request_revision"]
        result.next_action = "wait_for_human"
        result.human_gate = APPROVAL_GATES.get(phase, phase)
        return result

    blocking = [i for i in issues if i.get("severity") == "blocking"]
    if blocking:
        result.blocked = [
            {"action": "advance_phase", "reason": f"blocking issue: {b.get('code', '')}"}
            for b in blocking
        ]
        result.eligible = ["repair", "request_human_review"]
        result.next_action = "handle_blockers"
        return result

    if not approved and phase in APPROVAL_GATES:
        result.eligible = ["present_review_package", "approve_phase"]
        result.next_action = "present_review_package"
        result.human_gate = APPROVAL_GATES[phase]
        return result

    idx = PHASE_ORDER.index(phase) if phase in PHASE_ORDER else -1
    if idx >= 0 and idx + 1 < len(PHASE_ORDER):
        next_phase = PHASE_ORDER[idx + 1]
        result.eligible = [f"advance_to_{next_phase}"]
        result.next_action = f"advance_to_{next_phase}"
    else:
        result.eligible = ["wrap"]
        result.next_action = "wrap"

    return result
