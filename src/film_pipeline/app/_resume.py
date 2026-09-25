"""Graph-resume helpers: approval progress checks and external-state carry-over.

MCP tools mutate the active project state after a graph checkpoint was
created; these helpers replay those mutations when the graph resumes so a
checkpoint never sees stale state.
"""

from __future__ import annotations

from typing import Any

from film_pipeline.graph.phase_sequence import PHASE_SEQUENCE

_STALE_REQUEST_CODES = frozenset({"empty_generation_requests", "no_generation_requests"})


def _approval_made_progress(state: dict[str, Any], previous_phase: str) -> bool:
    """Return whether a graph approval resume changed phase or intentionally blocked."""
    if state.get("completed"):
        return True
    if state.get("_approval_blocked_by_issues"):
        return True
    issues = state.get("issues", [])
    if isinstance(issues, list) and any(
        isinstance(issue, dict) and issue.get("severity") == "blocking" for issue in issues
    ):
        return True
    current_phase = str(state.get("current_phase", ""))
    if current_phase == previous_phase:
        return False
    if current_phase in PHASE_SEQUENCE and previous_phase in PHASE_SEQUENCE:
        return PHASE_SEQUENCE.index(current_phase) > PHASE_SEQUENCE.index(previous_phase)
    return bool(current_phase)


def _has_stale_generation_request_blocker(
    resumed_state: dict[str, Any],
    active_state: dict[str, Any],
) -> bool:
    """Detect graph checkpoints that predate externally planned generation requests."""
    if str(active_state.get("current_phase", "")) != "generation":
        return False
    if not active_state.get("generation_requests"):
        return False
    if resumed_state.get("generation_requests"):
        return False
    issues = resumed_state.get("issues", [])
    if not isinstance(issues, list):
        return False
    return any(
        isinstance(issue, dict) and issue.get("code") in _STALE_REQUEST_CODES for issue in issues
    )


def _preserve_external_generation_requests(
    resumed_state: dict[str, Any],
    active_state: dict[str, Any],
) -> None:
    """Carry generation requests created by MCP tools across graph checkpoint resumes."""
    if resumed_state.get("generation_requests"):
        return
    generation_requests = active_state.get("generation_requests")
    if generation_requests:
        resumed_state["generation_requests"] = generation_requests


def _strip_stale_generation_request_blockers(state: dict[str, Any]) -> None:
    """Remove generated request-missing blockers after requests are restored."""
    if not state.get("generation_requests"):
        return
    issues = state.get("issues", [])
    if not isinstance(issues, list):
        return
    state["issues"] = [
        issue
        for issue in issues
        if not (isinstance(issue, dict) and issue.get("code") in _STALE_REQUEST_CODES)
    ]


def _build_resume_payload(
    action: str,
    active: dict[str, Any],
    note: str = "",
) -> dict[str, Any]:
    """Build a Command resume payload, carrying external MCP state into the graph.

    MCP tools such as ``plan_generation_batch`` update the active project state
    after the graph checkpoint was created. Without replaying those mutations,
    a resumed checkpoint sees stale state (e.g. empty generation requests) and
    loops on repair. The ``_external_state`` key is applied by ``await_approval_node``
    before the approval/revision action is processed.
    """
    payload: dict[str, Any] = {"action": action}
    if note:
        payload["note"] = note
    external_state: dict[str, Any] = {}
    generation_requests = active.get("generation_requests")
    if generation_requests:
        external_state["generation_requests"] = generation_requests
        # The requests exist now, so any "no requests" blockers recorded in
        # the graph checkpoint are stale — instruct the issues reducer to
        # drop them before the approval guard runs.
        external_state["remove_issue_codes"] = sorted(_STALE_REQUEST_CODES)
    if external_state:
        payload["_external_state"] = external_state
    return payload
