"""Conditional edge routing for the supervisor graph."""

from __future__ import annotations

from typing import Any

from film_pipeline.graph.router import compute_actions


def after_phase(state: dict[str, Any]) -> str:
    result = compute_actions(state)
    if result.next_action == "wait_for_human":
        return "await_approval"
    if result.human_gate and not state.get("approved"):
        return "await_approval"
    return result.next_action


def after_approval(state: dict[str, Any]) -> str:
    if state.get("approved"):
        phase = state.get("current_phase", "intake")
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
    if state.get("issues"):
        return "repair"
    return "await_approval"


def after_repair(_state: dict[str, Any]) -> str:
    return "await_approval"
