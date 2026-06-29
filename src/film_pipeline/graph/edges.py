"""Conditional edge routing for the supervisor graph.

Maps orchestrator action names (from ``compute_actions()``) to graph
node names. The action vocabulary is defined in the router; these edges
translate actions into concrete graph routing.
"""

from __future__ import annotations

from typing import Any

from film_pipeline.graph.router import compute_actions


def _is_auto_mode(state: dict[str, Any]) -> bool:
    """True when the resolved config disables human approval (headless runs)."""
    cfg = state.get("resolved_config", {})
    if isinstance(cfg, dict):
        studio = cfg.get("studio", {})
        if isinstance(studio, dict):
            return not bool(studio.get("require_human_approval", True))
    return False


def after_phase(state: dict[str, Any]) -> str:
    """Route after a phase node completes.

    Maps the orchestrator's next_action to a graph node name.
    Actions that should pause for a human gate map to ``consistency_check``,
    which always flows into ``await_approval``.
    """
    result = compute_actions(state)
    action = result.next_action

    # Actions that route through the consistency check to the human gate
    if action in (
        "wait_for_human",
        "present_review_package",
        "escalate_to_human",
        "continue_unrelated_work",
    ):
        return "consistency_check"

    # Actions that route to automatic repair
    if action in ("handle_blockers",):
        return "repair"

    # Actions that route to a phase node — strip the prefix so the returned
    # value is the phase key used by the conditional-edge destination map.
    if action.startswith("advance_to_"):
        target = action[len("advance_to_") :]
        if target == "end":
            return "end"
        return target

    # Final phase completion
    if action == "wrap":
        return "end"

    # Actions that stay in the current phase
    if action in ("repair", "revise"):
        return "await_approval"

    # Fallback: treat as human gate
    return "consistency_check"


def after_approval(state: dict[str, Any]) -> str:
    """Route after the human approval gate.

    If approved, advance to the next phase. If stalled, stay at the gate
    (prevents infinite repair loop). If issues exist, route to repair.
    Otherwise, stay at the approval gate.
    """
    if state.get("approved"):
        phase = str(state.get("current_phase", "intake"))
        next_map: dict[str, str] = {
            "intake": "constitution",
            "constitution": "development",
            "development": "script",
            "script": "visual_dev",
            "visual_dev": "shot_bible",
            "shot_bible": "gen_planning",
            "gen_planning": "generation",
            "generation": "qc",
            "qc": "post",
            "post": "delivery",
            "delivery": "end",
        }
        return next_map.get(phase, "end")

    # Prevent infinite repair loop when stalled
    from film_pipeline.graph.orchestrator_state import is_stalled

    phase = str(state.get("current_phase", ""))
    if is_stalled(state, phase):
        state["human_approval_required"] = True
        state["_stalled_phase"] = phase
        issue_id = f"stalled:{phase}"
        issues = state.setdefault("issues", [])
        if not any(
            isinstance(issue, dict) and issue.get("issue_id") == issue_id for issue in issues
        ):
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
        # Headless mode has no human to intervene — end the run with the blocker
        # recorded instead of looping the approval gate forever.
        if _is_auto_mode(state):
            state["completed"] = True
            return "end"
        return "await_approval"

    if state.get("issues"):
        return "repair"
    return "await_approval"


def after_repair(_state: dict[str, Any]) -> str:
    return "await_approval"
