"""Conditional edge routing for the supervisor graph.

Maps orchestrator action names (from ``compute_actions()``) to graph
node names. The action vocabulary is defined in the router; these edges
translate actions into concrete graph routing.
"""

from __future__ import annotations

from collections.abc import Mapping

from film_pipeline.filmspec import next_phase as next_phase
from film_pipeline.orchestration.orchestrator_state import is_stalled as is_stalled
from film_pipeline.orchestration.router import compute_actions as compute_actions
from film_pipeline.orchestration.state_schema import StudioGraphState


def _is_auto_mode(state: Mapping[str, object]) -> bool:
    """True when the resolved config disables human approval (headless runs)."""
    cfg = state.get("resolved_config", {})
    if isinstance(cfg, dict):
        studio = cfg.get("studio", {})
        if isinstance(studio, dict):
            return not bool(studio.get("require_human_approval", True))
    return False


# Actions that route through the consistency check to the human gate
_HUMAN_GATE_ACTIONS = (
    "wait_for_human",
    "present_review_package",
    "escalate_to_human",
    "continue_unrelated_work",
)

# Actions that route to automatic repair
_REPAIR_ACTIONS = ("handle_blockers",)


def after_phase(state: StudioGraphState) -> str:
    """Route after a phase node completes.

    Maps the orchestrator's next_action to a graph node name.
    Actions that should pause for a human gate map to ``consistency_check``,
    which always flows into ``await_approval``.

    ``compute_actions`` reaches ``ensure_orchestrator_state`` through the
    gate-facts port, which *seeds* the orchestrator keys with ``setdefault``
    under computed module-constant names. A TypedDict cannot be indexed by a
    computed key, so the call goes through a plain dict copy. Discarding that
    copy is safe: every seed is an empty container, and every reader of those
    keys uses ``.get(key, default)``, so the seeds are initialisation only.
    """
    result = compute_actions(dict(state))
    action = result.next_action

    if action in _HUMAN_GATE_ACTIONS:
        return "consistency_check"
    if action in _REPAIR_ACTIONS:
        return "repair"

    # Actions that route to a phase node — strip the prefix so the returned
    # value is the phase key used by the conditional-edge destination map.
    # Includes the defensive "advance_to_end", which maps to the terminal node.
    if action.startswith("advance_to_"):
        return action[len("advance_to_") :]

    # Final phase completion
    if action == "wrap":
        return "end"

    # Actions that stay in the current phase
    if action in ("repair", "revise"):
        return "await_approval"

    # Fallback: treat as human gate
    return "consistency_check"


def _record_stall(state: StudioGraphState, phase: str) -> None:
    """Flag the gate as requiring a human and record a deduplicated blocker."""
    state["human_approval_required"] = True
    state["_stalled_phase"] = phase
    issue_id = f"stalled:{phase}"
    issues = state.setdefault("issues", [])
    if not any(isinstance(issue, dict) and issue.get("issue_id") == issue_id for issue in issues):
        issues.append(
            {
                "issue_id": issue_id,
                "severity": "blocking",
                "code": "ORCHESTRATOR_STALLED",
                "message": (
                    f"Phase '{phase}' has stalled after repeated review or repair attempts. "
                    "Human intervention is required."
                ),
            }
        )


def after_approval(state: StudioGraphState) -> str:
    """Route after the human approval gate.

    If approved, advance to the next phase. If stalled, stay at the gate
    (prevents infinite repair loop). If issues exist, route to repair.
    Otherwise, stay at the approval gate.
    """
    if state.get("approved"):
        phase = str(state.get("current_phase", "intake"))
        return next_phase(phase) or "end"

    # Prevent infinite repair loop when stalled
    phase = str(state.get("current_phase", ""))
    if is_stalled(state, phase):
        _record_stall(state, phase)
        # Headless mode has no human to intervene — end the run with the blocker
        # recorded instead of looping the approval gate forever.
        if _is_auto_mode(state):
            state["completed"] = True
            return "end"
        return "await_approval"

    if state.get("issues"):
        return "repair"
    return "await_approval"
