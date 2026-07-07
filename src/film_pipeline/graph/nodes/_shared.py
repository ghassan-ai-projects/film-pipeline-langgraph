"""Shared node-level state helpers: services access, gates, diff utilities."""

from __future__ import annotations

import contextvars
import re
from typing import Any

from film_pipeline.graph.services import SERVICES_KEY, GraphServices

_SERVICES_CTX: contextvars.ContextVar[GraphServices | None] = contextvars.ContextVar(
    "_film_pipeline_services", default=None
)


def _get_services(state: dict[str, Any]) -> GraphServices | None:
    """Return ``GraphServices`` from state, falling back to context variable.

    When running through a LangGraph ``StateGraph`` channel system,
    extra state keys not declared in the TypedDict may be dropped.
    The context variable provides a reliable fallback.
    """
    svc = state.get(SERVICES_KEY)
    if svc is not None:
        return svc  # type: ignore[no-any-return]
    return _SERVICES_CTX.get()


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


def _extract_target_scene_count(state: dict[str, Any]) -> int | None:
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


def _critical_context_issues(state: dict[str, Any], phase: str) -> list[dict[str, Any]]:
    """Blocking issues for critical upstream context that failed to load."""
    required = _CRITICAL_CONTEXT.get(phase, [])
    if not required:
        return []
    failures = set(state.get("_context_load_failures", []) or [])
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


def _coerce_user_runtime(state: dict[str, Any]) -> int:
    """Return the user-supplied target runtime (seconds), or 0 if not provided.

    Seeded into state before the graph runs by the create/submit entry points.
    When > 0 it is authoritative and overrides any model-estimated runtime.
    """
    raw = state.get("target_runtime_seconds")
    if raw is None or isinstance(raw, bool):
        return 0
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return value if value > 0 else 0


def _require_human_approval(state: dict[str, Any]) -> bool:
    """Read ``require_human_approval`` from resolved config.

    Defaults to ``True`` (gates ON) when the key is missing or the config
    is unpopulated — safe-by-default for production. Set to ``False`` in
    a profile (e.g. ``auto-approve.yaml``) for headless/automated runs.
    """
    cfg = state.get("resolved_config", {})
    if isinstance(cfg, dict):
        studio = cfg.get("studio", {})
        if isinstance(studio, dict):
            return bool(studio.get("require_human_approval", True))
    return True


def _phase_gate_updates(state: dict[str, Any], *, phase: str, gate: str) -> dict[str, Any]:
    """State updates that park a completed phase at its human approval gate.

    With ``require_human_approval=False`` (auto-approve profiles) the gate is
    pre-approved so the graph advances without pausing.
    """
    auto = not _require_human_approval(state)
    return {
        "current_phase": phase,
        "approved": auto,
        "human_approval_required": not auto,
        "human_approval_phase": gate,
    }


def _apply_external_state(
    state: dict[str, Any],
    external_state: dict[str, Any],
) -> dict[str, Any]:
    """Replay external MCP mutations into graph state before processing a resume.

    MCP tools update the active project state outside the graph (e.g. planning
    a generation batch). The resumed checkpoint predates those mutations, so
    we carry them in ``Command(resume={"_external_state": ...})`` and merge
    them here. Returns a partial update dict for LangGraph to merge.
    """
    updates: dict[str, Any] = {}
    incoming_requests = external_state.get("generation_requests")
    if incoming_requests:
        existing = state.get("generation_requests", []) or []
        existing_ids = {
            str(r.get("generation_request_id", r.get("generation_id", "")))
            for r in existing
            if isinstance(r, dict)
        }
        new_requests = [
            r
            for r in incoming_requests
            if isinstance(r, dict)
            and str(r.get("generation_request_id", r.get("generation_id", ""))) not in existing_ids
        ]
        if new_requests:
            updates["generation_requests"] = new_requests
    remove_codes = external_state.get("remove_issue_codes")
    if isinstance(remove_codes, list) and remove_codes:
        updates["issues"] = [{"__remove_codes__": [str(code) for code in remove_codes]}]
    return updates


def _is_new_ref(ref: str, original_state: dict[str, Any]) -> bool:
    """Return True if *ref* was not present in the original state's artifact_refs."""
    orig_refs = set(original_state.get("artifact_refs", []) or [])
    return ref not in orig_refs


def _is_new_issue(issue: dict[str, Any], original_state: dict[str, Any]) -> bool:
    """Return True if *issue* has a novel issue_id not in the original state."""
    iid = issue.get("issue_id")
    if not iid:
        return False
    orig_ids = {
        i.get("issue_id") for i in (original_state.get("issues", []) or []) if i.get("issue_id")
    }
    return iid not in orig_ids
