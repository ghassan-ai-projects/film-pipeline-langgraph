"""Graph node definitions — one per phase."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def intake_node(state: dict[str, Any]) -> dict[str, Any]:
    """Intake: classify input, infer config, present for approval."""
    new_state = deepcopy(state)
    new_state["current_phase"] = "intake"
    if not new_state.get("approved"):
        new_state["human_approval_required"] = True
        new_state["human_approval_phase"] = "config"
    return new_state


def constitution_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "constitution"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "constitution"
    return new_state


def development_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "development"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "treatment"
    return new_state


def script_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "script"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "script"
    return new_state


def visual_dev_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "visual_dev"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "visual_bible"
    return new_state


def shot_bible_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "shot_bible"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "shot_bible"
    return new_state


def gen_planning_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "gen_planning"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "generation_spend"
    return new_state


def generation_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "generation"
    new_state["approved"] = False
    # Pauses before expensive work
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "generation_batch"
    return new_state


def qc_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "qc"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "qc"
    return new_state


def post_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "post"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "assembly"
    return new_state


def delivery_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "delivery"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "final_delivery"
    return new_state


def approve_phase_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["approved"] = True
    new_state["human_approval_required"] = False
    return new_state


def request_revision_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["approved"] = False
    new_state["human_approval_required"] = False
    issues = new_state.get("issues", [])
    new_state["issues"] = [
        *issues,
        {
            "issue_id": "rev",
            "severity": "warning",
            "code": "REVISION_REQUESTED",
            "message": "Human requested revision.",
        },
    ]
    return new_state
