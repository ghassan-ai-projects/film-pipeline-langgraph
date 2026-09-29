"""Handoff records and cross-node side-channel propagation.

Owns the underscore-prefixed state keys (``_routing_decisions``,
``_repair_feedback``, ``_validation_reports``) that carry routing and repair
decisions between nodes without entering artifact storage, plus the
orchestrator's ``_orchestrator__candidate_refs`` map that
``approve_phase_node`` promotes on approval.

Which keys cross the node boundary — and how each is copied — is owned by
``graph.orchestrator_state.ORCH_CHANNELS``. This module contributes no key
names of its own; adding a channel means adding a registry row, which the
channel-registry parity tests enforce.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from film_pipeline.orchestration.orchestrator_state import ORCH_CHANNELS
from film_pipeline.orchestration.state_schema import StudioGraphState

if TYPE_CHECKING:
    from film_pipeline.orchestration.router import AgentRouteResult


def _propagate_append_only_entries(
    source: Mapping[str, object],
    dest: dict[str, Any],
    original: Mapping[str, object] | None,
    key: str,
) -> None:
    """Propagate only entries appended after the node's input snapshot.

    ``issues`` and ``validation_report_refs`` are append-only reducer channels;
    slicing against ``original`` keeps the reducer from re-appending entries
    the node merely carried through.

    ``source``/``original`` are read-only graph state. ``dest`` is the caller's
    partial-update accumulator, written under a *computed* channel key, so it
    has to stay ``dict[str, Any]``: a TypedDict cannot be indexed by a computed
    key (``TypedDict key must be a string literal [literal-required]``).
    """
    if key not in source:
        return
    raw = source.get(key)
    entries = list(raw) if isinstance(raw, list) else []
    if original is not None:
        prior_raw = original.get(key)
        prior = len(prior_raw) if isinstance(prior_raw, list) else 0
        entries = entries[prior:]
    if entries or original is None:
        dest[key] = entries


def _propagate_side_effects(
    source: Mapping[str, object],
    dest: dict[str, Any],
    original: Mapping[str, object] | None = None,
) -> None:
    """Copy registered side-effect keys from ``source`` to ``dest``.

    ``_run_agent`` mutates ``source`` (the node's ``new_state``) via
    ``_record_handoff``, but nodes return only an ``updates`` dict.
    This helper ensures side effects survive the node boundary exactly as
    declared by ``ORCH_CHANNELS`` — one policy per key, no local key list.

    When ``original`` (the node's input state) is provided, append-only
    reducer channels contribute only newly appended entries.

    ``dest`` is the caller's partial-update accumulator, written under computed
    channel keys, so it stays ``dict[str, Any]`` rather than a TypedDict.
    """

    for spec in ORCH_CHANNELS:
        if spec.propagation == "explicit":
            continue
        if spec.propagation == "append_only":
            _propagate_append_only_entries(source, dest, original, spec.key)
            continue
        if spec.key not in source:
            continue
        value = source[spec.key]
        if spec.propagation == "full_truthy" and not value:
            continue
        dest[spec.key] = value


def _prepend_repair_feedback(task: str, state: Mapping[str, object]) -> str:
    """Prefix ``task`` with repair feedback injected by repair_phase_node."""
    feedback = str(state.get("_repair_feedback", "") or "")
    if feedback:
        return f"{feedback}\n\n{task}"
    return task


def _capture_run_outcome(
    state: StudioGraphState,
    result: dict[str, Any],
    had_feedback: bool,
) -> dict[str, Any]:
    """Propagate handoff mutations into the result and clear consumed repair feedback."""
    routing_decisions = state.get("_routing_decisions")
    if routing_decisions:
        result["_routing_decisions"] = list(routing_decisions)
    if had_feedback:
        state["_repair_feedback"] = ""
        result["_repair_feedback"] = ""
    return result


def _is_duplicate_handoff(routes: list[dict[str, Any]], phase: str, task: str) -> bool:
    """Return True when a handoff record with the same phase+task already exists."""
    handoff_key = f"{phase}:{task}"
    for existing in routes:
        existing_key = f"{existing.get('phase', '')}:{existing.get('task', '')}"
        if existing_key == handoff_key:
            return True
    return False


def _record_handoff(
    state: StudioGraphState,
    agent_id: str,
    phase: str,
    task: str,
    route_result: AgentRouteResult,
    agent_output: dict[str, Any],
    *,
    template_id: str = "",
    model_profile: str = "",
) -> None:
    """Store a handoff record so routing is explainable and queryable.

    Idempotent: duplicates (same phase + task) on replay are skipped.
    Records prompt template version and resolved model profile for audit.
    """
    routes: list[dict[str, Any]] = state.setdefault("_routing_decisions", [])

    # Guard against duplicates on LangGraph checkpoint replay
    if _is_duplicate_handoff(routes, phase, task):
        return

    handoff = {
        "agent_id": agent_id,
        "phase": phase,
        "task": task,
        "routing_reason": route_result.routing_reason,
        "fallback": route_result.fallback,
        "input_refs": list(state.get("artifact_refs", [])),
        "output_keys": list(agent_output.keys()),
        "project_id": state.get("project_id", ""),
        "template_id": template_id,
        "model_profile": model_profile,
    }
    routes.append(handoff)
