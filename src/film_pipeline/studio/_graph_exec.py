"""Graph execution for the studio runtime: invoke, resume, validate, advance.

Owns every interaction between ``StudioRuntime`` and the LangGraph state
machine — running the graph, resuming it at approval gates, running validators
against live state, and the manual phase-advance fallback.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from film_pipeline.filmspec import PHASE_SEQUENCE, next_phase
from film_pipeline.orchestration.services import _SERVICES_CTX
from film_pipeline.schemas.base import FilmPhase
from film_pipeline.schemas.runtime_state import GraphStateSnapshot
from film_pipeline.storage.project_storage import graph_state_location
from film_pipeline.studio import _persistence
from film_pipeline.studio._resume import (
    _approval_made_progress,
    _build_resume_payload,
    _has_stale_generation_request_blocker,
    _preserve_external_generation_requests,
    _strip_stale_generation_request_blockers,
)

if TYPE_CHECKING:
    from film_pipeline.studio.runtime import StudioRuntime

_logger = logging.getLogger(__name__)


def ensure_graph(rt: StudioRuntime) -> Any:
    """Lazy-load and cache the graph instance."""
    if rt.graph is None:
        from film_pipeline.studio.graph_factory import build_graph

        rt.graph = build_graph(runtime_root=rt.runtime_root)
    return rt.graph


def run_graph(rt: StudioRuntime, state: dict[str, Any]) -> dict[str, Any]:
    """Run the graph with the given state.

    Supplies ``GraphServices`` through runtime context before invocation
    so checkpoints never need to serialize service objects.

    With LangGraph ``interrupt()`` + checkpointer, the graph pauses at
    human gates and resumes via ``graph.invoke(Command(...), config)``.
    No recursion-limit workaround needed.

    Persists graph state to disk for crash recovery (Phase 7+ P0).
    """
    graph = ensure_graph(rt)

    state = dict(state)

    # Set context-var fallback so nodes can find services without storing
    # runtime dependencies in checkpointed graph state.
    token = _SERVICES_CTX.set(rt.services)
    try:
        config: dict[str, Any] = {
            "configurable": {
                "thread_id": state.get("project_id", "default"),
                "services": rt.services,
            },
            "recursion_limit": 50,  # 10 phases x ~3 steps each + repair headroom
        }
        result: dict[str, Any] = cast(dict[str, Any], graph.invoke(state, config))
    finally:
        _SERVICES_CTX.reset(token)
    pid = str(result.get("project_id", ""))
    if pid:
        auto_checkpoint(rt, result)
    return result


def auto_checkpoint(rt: StudioRuntime, state: dict[str, Any]) -> None:
    """Persist the state snapshot and create a checkpoint after a graph step."""
    project_id = str(state.get("project_id", ""))
    if not project_id or project_id not in rt.projects:
        return
    phase = str(state.get("current_phase", "") or "intake")
    if not phase:
        return

    # The graph state snapshot lives at state/graph-state.json: one atomic
    # write per mutating operation; checkpoints only reference it. The old
    # per-step graph_state artifact is gone. A failed snapshot must not
    # crash a run that already completed.
    try:
        save_graph_state(rt, dict(state), project_id)
    except Exception as exc:
        _logger.warning("Auto-checkpoint could not persist graph state for %s: %s", project_id, exc)
    graph_state_ref = graph_state_location()

    from film_pipeline.orchestration.orchestrator_state import get_candidate_refs

    candidate_refs = get_candidate_refs(state)
    artifact_versions = dict(candidate_refs)

    try:
        rt.create_checkpoint(
            project_id=project_id,
            phase=phase,
            reason="auto: graph step completed",
            artifact_versions=artifact_versions,
            graph_state_ref=graph_state_ref,
        )
    except Exception as exc:
        # A failed auto-checkpoint must not crash the run, but it must be
        # visible: log with traceback and record an audit event.
        _logger.warning("Auto-checkpoint failed for %s at %s", project_id, phase, exc_info=True)
        rt._record_audit(
            "system",
            "auto_checkpoint_failed",
            project_id=project_id,
            phase=phase,
            error=str(exc)[:200],
        )


def save_graph_state(rt: StudioRuntime, state: dict[str, Any], project_id: str) -> None:
    """Persist one machine state snapshot for crash recovery (atomic).

    Values the typed snapshot cannot serialize degrade through ``str()`` —
    crash recovery must never fail on state content. The write itself belongs
    to the storage core; this function only shapes the snapshot.
    """
    storage = _persistence.storage_for(rt)
    if storage is None or project_id not in rt.project_roots:
        return
    safe = {k: v for k, v in state.items() if not k.startswith("_services")}
    try:
        snapshot = GraphStateSnapshot(state=safe)
    except ValueError:
        snapshot = GraphStateSnapshot(state=json.loads(json.dumps(safe, default=str)))
    storage.write_graph_state(project_id, snapshot)


def _approval_stalled(state: dict[str, Any], active: dict[str, Any], current_phase: str) -> bool:
    """True when approval made no progress or a stale generation blocker remains."""
    return not _approval_made_progress(
        state, current_phase
    ) or _has_stale_generation_request_blocker(state, active)


def _has_pending_human_interrupt(snapshot: Any) -> bool:
    """Return whether a checkpoint can accept ``Command(resume=...)``.

    A persisted failed ``__start__`` task is a checkpoint, but it is not a
    resumable human gate. Calling ``Command(resume=...)`` there writes no state
    channel and raises LangGraph's ``InvalidUpdateError``.
    """
    tasks = getattr(snapshot, "tasks", ())
    if any(getattr(task, "interrupts", ()) for task in tasks or ()):
        return True
    next_nodes = tuple(getattr(snapshot, "next", ()) or ())
    if next_nodes:
        return "await_approval" in next_nodes
    return False


def _resume_after_approval(
    rt: StudioRuntime,
    active: dict[str, Any],
    current_phase: str,
) -> Any:
    """Resume the graph at the approval gate; fall back to manual advance.

    The fallback fires *only* when no checkpoint exists for the project's
    thread (legitimate for projects advanced before any graph checkpoint),
    detected via an empty ``get_state`` snapshot — never on generic failures.
    A failing resume is logged, audited as ``resume_failed``, and re-raised:
    errors must not silently bypass the human gate.
    """
    from langgraph.types import Command

    graph = ensure_graph(rt)
    config: dict[str, Any] = {
        "configurable": {"thread_id": active["project_id"], "services": rt.services},
    }

    # Set the services context variable so graph nodes can find
    # GraphServices without checkpointing runtime objects.
    token = _SERVICES_CTX.set(rt.services)
    try:
        try:
            snapshot = graph.get_state(config)
        except Exception as exc:
            _logger.exception(
                "Graph state probe failed for %s at phase %s",
                active.get("project_id", ""),
                current_phase,
            )
            rt._record_audit(
                "system",
                "resume_failed",
                project_id=str(active.get("project_id", "")),
                phase=current_phase,
                error=type(exc).__name__,
            )
            raise
        if not snapshot.values and not snapshot.next:
            return advance_to_next_phase(rt, dict(active))
        try:
            state = graph.invoke(
                Command(resume=_build_resume_payload("approve", active)),
                config,
            )
        except Exception as exc:
            _logger.exception(
                "Graph resume failed for %s at phase %s",
                active.get("project_id", ""),
                current_phase,
            )
            rt._record_audit(
                "system",
                "resume_failed",
                project_id=str(active.get("project_id", "")),
                phase=current_phase,
                error=type(exc).__name__,
            )
            raise
        _preserve_external_generation_requests(state, active)
        _strip_stale_generation_request_blockers(state)
        if _approval_stalled(state, active, current_phase):
            rt._record_audit(
                "system",
                "resume_stalled_manual_advance",
                project_id=str(active.get("project_id", "")),
                phase=current_phase,
                next_phase=str(state.get("current_phase", "")),
            )
            return advance_to_next_phase(rt, dict(active))
        return state
    finally:
        _SERVICES_CTX.reset(token)


def _approve_phase_artifacts(rt: StudioRuntime, project_id: str, phase: str) -> None:
    """Transition the approved phase's current artifacts to APPROVED.

    The human gate is the one place the artifact status machine fires in
    production: approved artifacts gain an approval ref and their human
    views land in ``deliverables/``. Best-effort — a store transition
    failure must not undo the phase approval itself.
    """
    if rt.services is None:
        return
    store = rt.services.artifact_store
    for meta in store.list_artifacts(project_id, FilmPhase(phase)):
        try:
            store.approve(
                project_id,
                phase,
                meta.artifact_id,
                meta.version,
                approval_ref=f"approval:{phase}:{meta.artifact_id}:v{meta.version}",
            )
        except (ValueError, FileNotFoundError, OSError) as exc:
            _logger.warning(
                "Could not mark %s v%d approved: %s", meta.artifact_id, meta.version, exc
            )


def approve_phase(rt: StudioRuntime) -> dict[str, Any]:
    """Approve the current phase and advance.

    Resumes the graph at the approval gate (see ``_resume_after_approval``)
    via ``Command(resume={"action": "approve", ...})``, then persists state,
    checkpoints, and records the audit trail.
    """
    active = rt.get_active()
    if not active:
        raise ValueError("No active project.")
    current_phase = str(active.get("current_phase", ""))
    if not current_phase:
        raise ValueError("No active phase to approve.")

    state = cast(dict[str, Any], _resume_after_approval(rt, active, current_phase))

    rt.projects[active["project_id"]] = state
    rt._persist_project_state(active["project_id"])
    save_graph_state(rt, dict(state), active["project_id"])
    _approve_phase_artifacts(rt, active["project_id"], current_phase)

    checkpoint = rt.create_checkpoint(
        project_id=active["project_id"],
        phase=str(state.get("current_phase", "")),
        reason=f"Approved at {current_phase}",
    )

    rt._record_audit(
        "human",
        "approve_phase",
        project_id=active["project_id"],
        phase=current_phase,
        next_phase=str(state.get("current_phase", "")),
        checkpoint_id=checkpoint.checkpoint_id,
    )
    return state


def run_validation(rt: StudioRuntime, project_id: str | None = None) -> dict[str, Any]:
    """Run validators against the active project's current-phase artifacts.

    Executes the same validator dispatch the QC node uses, but against the
    live project state and *without* advancing the phase. Validator-produced
    findings replace any prior validator findings (issues tagged with a
    ``validator_id``) while non-validator blockers are preserved, then the
    refreshed issues and validation reports are merged back and persisted.
    """
    from film_pipeline.orchestration.nodes import _run_validators
    from film_pipeline.orchestration.services import SERVICES_KEY

    active = rt.get_project(project_id) if project_id else rt.get_active()
    if active is None:
        raise ValueError("No active project.")
    project_id_value = str(active["project_id"])

    preserved_issues = [
        issue
        for issue in cast(list[dict[str, Any]], active.get("issues", []))
        if not (isinstance(issue, dict) and issue.get("validator_id"))
    ]
    working = dict(active)
    working[SERVICES_KEY] = rt.services
    working["issues"] = list(preserved_issues)
    working["_validation_reports"] = []
    working.pop("_pending_row_updates", None)
    _run_validators(working)
    working.pop(SERVICES_KEY, None)

    active["issues"] = list(working.get("issues", []))
    active["_validation_reports"] = list(working.get("_validation_reports", []))
    consensus_ref = working.get("consensus_report_ref")
    if consensus_ref:
        active["consensus_report_ref"] = consensus_ref
    rt.projects[project_id_value] = active
    rt._persist_project_state(project_id_value)
    rt._record_audit(
        "human",
        "run_validation",
        project_id=project_id_value,
        phase=str(active.get("current_phase", "")),
    )
    return active


def request_revision(rt: StudioRuntime, note: str = "") -> dict[str, Any]:
    """Request revision of the current phase.

    Resumes a live approval interrupt with ``Command(resume=...)``. If the
    persisted checkpoint is missing or is a failed ``__start__`` task, submits
    the active state as a normal graph input and explicitly routes it to repair.
    """
    from langgraph.types import Command

    active = rt.get_active()
    if not active:
        raise ValueError("No active project.")

    graph = ensure_graph(rt)
    config: dict[str, Any] = {
        "configurable": {"thread_id": active["project_id"], "services": rt.services},
        "recursion_limit": 50,
    }

    token = _SERVICES_CTX.set(rt.services)
    try:
        try:
            snapshot = graph.get_state(config)
            if _has_pending_human_interrupt(snapshot):
                state = graph.invoke(
                    Command(resume=_build_resume_payload("revise", active, note=note)),
                    config,
                )
            else:
                # Re-submit the persisted runtime state as a real graph input.
                # This repairs missing/poisoned checkpoints before routing to
                # repair_phase_node; Command(resume=...) is invalid at __start__.
                recovery_state = dict(active)
                recovery_state["_revision_note"] = note
                recovery_state["_resume_to_repair"] = True
                state = graph.invoke(recovery_state, config)
        except Exception as exc:
            _logger.exception(
                "Graph revision resume failed for %s at phase %s",
                active.get("project_id", ""),
                active.get("current_phase", ""),
            )
            rt._record_audit(
                "system",
                "resume_failed",
                project_id=str(active.get("project_id", "")),
                phase=str(active.get("current_phase", "")),
                error=type(exc).__name__,
            )
            raise
    finally:
        _SERVICES_CTX.reset(token)
    state = cast(dict[str, Any], state)

    rt.projects[active["project_id"]] = state
    rt._persist_project_state(active["project_id"])
    save_graph_state(rt, dict(state), active["project_id"])

    rt._record_audit(
        "human",
        "request_revision",
        project_id=active["project_id"],
        note=note,
    )
    return state


def advance_to_next_phase(rt: StudioRuntime, state: dict[str, Any]) -> dict[str, Any]:
    current_phase = str(state.get("current_phase", ""))
    if current_phase not in PHASE_SEQUENCE:
        rt.projects[state["project_id"]] = state
        rt._persist_project_state(state["project_id"])
        return state

    successor = next_phase(current_phase)
    if successor is None:
        final_state = dict(state)
        final_state["completed"] = True
        final_state["human_approval_phase"] = ""
        rt.projects[state["project_id"]] = final_state
        rt._persist_project_state(state["project_id"])
        return final_state

    advanced_state = run_phase_node(rt, state, successor)
    rt.projects[state["project_id"]] = advanced_state
    rt._persist_project_state(state["project_id"])
    return advanced_state


def run_phase_node(rt: StudioRuntime, state: dict[str, Any], phase: str) -> dict[str, Any]:
    from film_pipeline.orchestration.nodes.approval import _PHASE_NODES
    from film_pipeline.orchestration.services import SERVICES_KEY

    node = _PHASE_NODES[phase]
    # Inject graph services so nodes can invoke agents and persist artifacts
    state = dict(state)
    state[SERVICES_KEY] = rt.services
    node_result = node(state)
    # Merge node result back into state using the same reducer semantics
    # the graph applies (direct node calls bypass channel accumulation).
    from film_pipeline.orchestration.state_schema import (
        merge_generation_requests,
        merge_issues,
        merge_unique,
    )

    merged = dict(state)
    merged.update(node_result)
    reducers: dict[str, Callable[[list[Any] | None, list[Any] | None], list[Any]]] = {
        "artifact_refs": merge_unique,
        "issues": merge_issues,
        "validation_report_refs": merge_unique,
        "generation_requests": merge_generation_requests,
    }
    for key, reducer in reducers.items():
        new = node_result.get(key, [])
        if new:
            merged[key] = reducer(list(state.get(key, [])), list(new))
    for key in ("_routing_decisions", "_validation_reports"):
        prev = state.get(key, [])
        new = node_result.get(key, [])
        if new:
            merged[key] = list(prev) + [item for item in new if item not in prev]
    # Strip runtime-only keys that must not leak into persisted state
    merged.pop(SERVICES_KEY, None)
    return merged
