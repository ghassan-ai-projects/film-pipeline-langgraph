"""Handoff records and cross-node side-channel propagation.

Owns the underscore-prefixed state keys (``_routing_decisions``,
``_repair_feedback``, ``_validation_reports``) that carry routing and repair
decisions between nodes without entering artifact storage, plus the
orchestrator's ``_orchestrator__candidate_refs`` map that
``approve_phase_node`` promotes on approval.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from film_pipeline.graph.router import AgentRouteResult


def _copy_decision_channels(source: dict[str, Any], dest: dict[str, Any]) -> None:
    """Copy whole decision-channel keys (routing, repair feedback, reports)."""
    for key in ("_routing_decisions", "_repair_feedback", "_validation_reports"):
        if key in source:
            dest[key] = source[key]


def _copy_published_candidate_refs(source: dict[str, Any], dest: dict[str, Any]) -> None:
    """Carry the candidate-ref map so approval can promote published artifacts.

    ``_save_artifact`` records each ref into the node's working copy via
    ``set_candidate_ref``. Without copying the map into the returned update,
    it never reaches real graph state and ``approve_phase_node`` promotes
    an empty snapshot.
    """
    from film_pipeline.graph.orchestrator_state import get_candidate_refs

    refs = get_candidate_refs(source)
    if refs:
        dest["_orchestrator__candidate_refs"] = refs


def _append_new_reducer_entries(
    source: dict[str, Any],
    dest: dict[str, Any],
    original: dict[str, Any] | None,
) -> None:
    """Propagate only entries appended after the node's input snapshot.

    ``issues`` and ``validation_report_refs`` are append-only reducer channels;
    slicing against ``original`` keeps the reducer from re-appending entries
    the node merely carried through.
    """
    for key in ("issues", "validation_report_refs"):
        if key not in source:
            continue
        entries = list(source.get(key, []) or [])
        if original is not None:
            prior = len(list(original.get(key, []) or []))
            entries = entries[prior:]
        if entries or original is None:
            dest[key] = entries


def _propagate_side_effects(
    source: dict[str, Any],
    dest: dict[str, Any],
    original: dict[str, Any] | None = None,
) -> None:
    """Copy known side-effect keys from ``source`` to ``dest``.

    ``_run_agent`` mutates ``source`` (the node's ``new_state``) via
    ``_record_handoff``, but nodes return only an ``updates`` dict.
    This helper ensures routing decisions and other side effects
    survive the node boundary.

    When ``original`` (the node's input state) is provided, append-only
    reducer channels contribute only newly appended entries.
    """
    _copy_decision_channels(source, dest)
    _copy_published_candidate_refs(source, dest)
    _append_new_reducer_entries(source, dest, original)


def _prepend_repair_feedback(task: str, state: dict[str, Any]) -> str:
    """Prefix ``task`` with repair feedback injected by repair_phase_node."""
    feedback = str(state.get("_repair_feedback", "") or "")
    if feedback:
        return f"{feedback}\n\n{task}"
    return task


def _capture_run_outcome(
    state: dict[str, Any],
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
    state: dict[str, Any],
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
