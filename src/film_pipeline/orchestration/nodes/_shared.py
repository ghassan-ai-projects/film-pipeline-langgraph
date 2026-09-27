"""Shared node-level state helpers for gates and state diffs."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from film_pipeline.orchestration.orchestrator_state import require_human_approval
from film_pipeline.orchestration.state_schema import StudioGraphState

_NUMBER_WORDS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}


def _extract_target_scene_count(state: Mapping[str, object]) -> int | None:
    """Return an explicit user scene-count if one was provided or mentioned.

    Priority:
    1. A value already set in state (e.g. from the ``submit_idea`` tool).
    2. A number in the idea text such as ``12 scenes`` or ``twelve scenes``.
    """
    explicit = state.get("target_scene_count")
    if isinstance(explicit, int) and explicit > 0:
        return explicit

    idea = str(state.get("idea", ""))
    if not idea:
        return None

    # Digits first: "12 scenes", "12-scene", "12 scenes,"
    digit_match = re.search(r"(\d+)\s*[-]?\s*(?:scene|scenes)\b", idea, re.IGNORECASE)
    if digit_match:
        count = int(digit_match.group(1))
        if count > 0:
            return count

    # Number words: "twelve scenes"
    lowered = idea.lower()
    for word, value in _NUMBER_WORDS.items():
        pattern = rf"\b{word}\b\s*[-]?\s*(?:scene|scenes)\b"
        if re.search(pattern, lowered):
            return value

    return None


_CRITICAL_CONTEXT: dict[str, list[str]] = {
    "development": ["constitution_ref"],
    "script": ["constitution_ref", "treatment_ref", "scene_list_ref"],
}


def _critical_context_issues(state: Mapping[str, object], phase: str) -> list[dict[str, Any]]:
    """Blocking issues for critical upstream context that failed to load."""
    required = _CRITICAL_CONTEXT.get(phase, [])
    if not required:
        return []
    raw_failures = state.get("_context_load_failures")
    failures = set(raw_failures) if isinstance(raw_failures, list) else set()
    issues: list[dict[str, Any]] = []
    for key in required:
        ref = str(state.get(key, "") or "").strip()
        if ref and key in failures:
            issues.append(
                {
                    "issue_id": f"ctx_unavailable_{key}",
                    "severity": "blocking",
                    "code": "critical_context_unavailable",
                    "message": (
                        f"Required upstream artifact '{key}' ({ref}) could not be "
                        f"loaded for the {phase} phase. The agent would write "
                        "context-blind; resolve the upstream artifact before continuing."
                    ),
                }
            )
    return issues


def _coerce_user_runtime(state: Mapping[str, object]) -> int:
    """Return the user-supplied target runtime (seconds), or 0 if not provided.

    Seeded into state before the graph runs by the create/submit entry points.
    When > 0 it is authoritative and overrides any model-estimated runtime.
    """
    raw = state.get("target_runtime_seconds")
    if raw is None or isinstance(raw, bool):
        return 0
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return 0
    return value if value > 0 else 0


def _phase_gate_updates(state: Mapping[str, object], *, phase: str, gate: str) -> StudioGraphState:
    """State updates that park a completed phase at its human approval gate.

    With ``require_human_approval=False`` (auto-approve profiles) the gate is
    pre-approved so the graph advances without pausing.

    Returns a partial update: every key below is declared on
    :class:`StudioGraphState`.
    """
    auto = not require_human_approval(state)
    return {
        "current_phase": phase,
        "approved": auto,
        "human_approval_required": not auto,
        "human_approval_phase": gate,
    }


def _generation_request_key(request: dict[str, Any]) -> str:
    """Deduplication key identifying a generation request across MCP and graph state."""
    return str(request.get("generation_request_id", request.get("generation_id", "")))


def _apply_external_state(
    state: Mapping[str, object],
    external_state: dict[str, Any],
) -> StudioGraphState:
    """Replay external MCP mutations into graph state before processing a resume.

    MCP tools update the active project state outside the graph (e.g. planning
    a generation batch). The resumed checkpoint predates those mutations, so
    we carry them in ``Command(resume={"_external_state": ...})`` and merge
    them here. Returns a partial update dict for LangGraph to merge.
    """
    updates: StudioGraphState = {}
    incoming_requests = external_state.get("generation_requests")
    if incoming_requests:
        raw_existing = state.get("generation_requests")
        existing = raw_existing if isinstance(raw_existing, list) else []
        existing_ids = {_generation_request_key(r) for r in existing if isinstance(r, dict)}
        new_requests = [
            r
            for r in incoming_requests
            if isinstance(r, dict) and _generation_request_key(r) not in existing_ids
        ]
        if new_requests:
            updates["generation_requests"] = new_requests
    remove_codes = external_state.get("remove_issue_codes")
    if isinstance(remove_codes, list) and remove_codes:
        updates["issues"] = [{"__remove_codes__": [str(code) for code in remove_codes]}]
    return updates


def _is_new_ref(ref: str, original_state: Mapping[str, object]) -> bool:
    """Return True if *ref* was not present in the original state's artifact_refs."""
    existing = original_state.get("artifact_refs")
    orig_refs = set(existing) if isinstance(existing, list) else set()
    return ref not in orig_refs


def _is_new_issue(issue: dict[str, Any], original_state: Mapping[str, object]) -> bool:
    """Return True if *issue* has a novel issue_id not in the original state."""
    iid = issue.get("issue_id")
    if not iid:
        return False
    existing = original_state.get("issues")
    orig_ids = {
        i.get("issue_id")
        for i in (existing if isinstance(existing, list) else [])
        if isinstance(i, dict) and i.get("issue_id")
    }
    return iid not in orig_ids


def _collect_updates(
    gate_updates: Mapping[str, object],
    new_state: Mapping[str, object],
    original: Mapping[str, object],
    ref_keys: tuple[str, ...],
) -> dict[str, Any]:
    """Compute the partial update from a before/after diff of the node state.

    One definition, shared by the phase nodes that diff their working copy
    against the state they were handed. It was byte-identical in both `qc` and
    `visual`, which meant the node-boundary update rule — which refs and issues
    cross the boundary, and which keys are carried — had two authors and no
    test pinning them to each other.

    All three state parameters are read-only, so they take ``Mapping``: that
    accepts the graph-state TypedDict its callers hold. The return stays
    ``dict[str, Any]`` because ``ref_keys`` is a runtime tuple, and a TypedDict
    cannot be written through a computed key (``[literal-required]``).
    """
    updates: dict[str, Any] = dict(gate_updates)
    refs = new_state.get("artifact_refs")
    candidates = refs if isinstance(refs, list) else []
    new_refs = [str(r) for r in candidates if _is_new_ref(str(r), original)]
    if new_refs:
        updates["artifact_refs"] = new_refs
    raw_issues = new_state.get("issues")
    listed = raw_issues if isinstance(raw_issues, list) else []
    new_issues = [i for i in listed if isinstance(i, dict) and _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    for key in ref_keys:
        val = new_state.get(key)
        if val:
            updates[key] = val
    return updates
