"""Graph execution: invoke, resume, validate, advance.

Owns every interaction between a runtime and the LangGraph state machine —
running the graph, resuming it at approval gates, running validators against live
state, and the manual phase-advance fallback.

## Why this lives in `orchestration`

It was `studio/_graph_exec.py`. To do its job it imported three *private*
`orchestration` names — `services._SERVICES_CTX`, `nodes._run_validators` and
`nodes.approval._PHASE_NODES` — which was 3 of the 5 remaining cross-package
private reach-ins in the tree
(`docs/modularity-improvements/02-graph-execution-has-two-executors.md`, finding A).
A module that needs three of another package's private names is not a consumer of
that package; it is part of it.

`studio` keeps the composition it owns: `graph_factory` still wires the services and
the checkpointer together, and `StudioRuntime` still exposes the graph-execution
methods as its public interface. What moved is the execution *policy*.

## What the runtime must provide

`GraphHost` below states the whole requirement structurally, so this module
imports neither the composition root nor `operations`. It must not import
`operations`: that package imports `orchestration.services`, so reaching for
`operations.ports.RuntimePort` here would close `operations <-> orchestration`.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping
from typing import Any, Protocol, cast

from langgraph.graph.state import CompiledStateGraph

from film_pipeline.filmspec import PHASE_SEQUENCE, next_phase
from film_pipeline.orchestration.nodes import _run_validators
from film_pipeline.orchestration.nodes._repair_loop import resolved_phase_node
from film_pipeline.orchestration.orchestrator_state import get_candidate_refs
from film_pipeline.orchestration.resume import (
    _approval_made_progress,
    _build_resume_payload,
    _has_stale_generation_request_blocker,
    _preserve_external_generation_requests,
    _strip_stale_generation_request_blockers,
)
from film_pipeline.orchestration.services import _SERVICES_CTX, SERVICES_KEY, GraphServices
from film_pipeline.orchestration.state_schema import (
    StudioGraphState,
    apply_node_update,
    undeclared_state_keys,
)
from film_pipeline.schemas.base import FilmPhase
from film_pipeline.schemas.runtime_state import GraphStateSnapshot
from film_pipeline.storage.project_storage import graph_state_location
from film_pipeline.storage.runtime_gateway import project_storage_for

_logger = logging.getLogger(__name__)


#: Builds a compiled graph for a runtime root.
GraphBuilder = Callable[..., Any]


class GraphHost(Protocol):
    """The runtime surface graph execution drives.

    Deliberately self-contained rather than extending `operations.ports.RuntimePort`:
    `operations` imports `orchestration.services`, so extending it here would close a
    package cycle, and the two protocols only overlap on `services` and the
    persist/audit pair. Stating the requirement in one place also means a runtime can
    be substituted in a test without the composition root.
    """

    #: The service bundle a graph run needs (artifact store, agent registry, ...).
    services: GraphServices | None

    graph: Any
    projects: dict[str, Any]
    project_roots: dict[str, Any]
    runtime_root: Any
    active_project_id: str

    def get_active(self) -> dict[str, Any] | None:
        """Return the active project's state."""
        ...

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Return one project's state by id."""
        ...

    def create_checkpoint(
        self,
        project_id: str,
        phase: str,
        reason: str,
        *,
        artifact_versions: dict[str, str] | None = None,
        graph_state_ref: str = "",
    ) -> Any:
        """Take a checkpoint of one project.

        Spelled out rather than `**kwargs: Any` so the protocol matches the
        concrete runtime's keyword-only signature; a looser declaration would be
        satisfied by a method this module cannot actually call.
        """
        ...

    def persist_project_state(self, project_id: str) -> None:
        """Write one project's state to disk."""
        ...

    def record_audit(self, actor: str, action: str, **details: Any) -> None:
        """Append one audit event."""
        ...


#: Builds the compiled graph for a runtime root. Registered by the composition
#: root so this module never names it.
#:
#: The alternative was a function-level `from film_pipeline.studio.graph_factory
#: import build_graph` here. That is what this module did before it moved, but the
#: move makes the edge a *cycle* — `studio.graph_factory` imports `orchestration`
#: to wire the nodes — and `test_package_acyclicity` reads `ast`, so a lazy import
#: is still an edge. Injecting the builder inverts the dependency: `studio` knows
#: about `orchestration`, and this module knows only that a builder exists.
_GRAPH_BUILDER: GraphBuilder | None = None


def register_graph_builder(builder: GraphBuilder) -> None:
    """Install the compiled-graph factory. Called once by the composition root."""
    global _GRAPH_BUILDER
    _GRAPH_BUILDER = builder


def ensure_graph(rt: GraphHost) -> Any:
    """Lazy-load and cache the graph instance."""
    if rt.graph is None:
        if _GRAPH_BUILDER is None:
            raise RuntimeError(
                "No graph builder is registered. The composition root "
                "(film_pipeline.studio) must call "
                "orchestration.execution.register_graph_builder(build_graph) at "
                "import; a runtime used without it cannot execute the graph."
            )
        rt.graph = _GRAPH_BUILDER(runtime_root=rt.runtime_root)
    return rt.graph


def run_graph(rt: GraphHost, state: dict[str, Any]) -> dict[str, Any]:
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


def auto_checkpoint(rt: GraphHost, state: dict[str, Any]) -> None:
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
        rt.record_audit(
            "system",
            "auto_checkpoint_failed",
            project_id=project_id,
            phase=phase,
            error=str(exc)[:200],
        )


def save_graph_state(rt: GraphHost, state: dict[str, Any], project_id: str) -> None:
    """Persist one machine state snapshot for crash recovery (atomic).

    Values the typed snapshot cannot serialize degrade through ``str()`` —
    crash recovery must never fail on state content. The write itself belongs
    to the storage core; this function only shapes the snapshot.
    """
    storage = project_storage_for(rt)
    if storage is None or project_id not in rt.project_roots:
        return
    safe = {k: v for k, v in state.items() if not k.startswith("_services")}
    # A key the state schema does not declare means a writer added state
    # without a contract. Warn rather than raise: crash recovery must not fail
    # on state content, but the drift must be visible.

    undeclared = undeclared_state_keys(safe)
    if undeclared:
        _logger.warning("Graph state for %s carries undeclared keys: %s", project_id, undeclared)
    try:
        snapshot = GraphStateSnapshot(state=safe)
    except ValueError:
        snapshot = GraphStateSnapshot(state=json.loads(json.dumps(safe, default=str)))
    storage.write_graph_state(project_id, snapshot)


def _approval_stalled(
    state: Mapping[str, object], active: Mapping[str, object], current_phase: str
) -> bool:
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
    rt: GraphHost,
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
            rt.record_audit(
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
            rt.record_audit(
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
            rt.record_audit(
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


def _approve_phase_artifacts(rt: GraphHost, project_id: str, phase: str) -> None:
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


def approve_phase(rt: GraphHost) -> dict[str, Any]:
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
    rt.persist_project_state(active["project_id"])
    save_graph_state(rt, dict(state), active["project_id"])
    _approve_phase_artifacts(rt, active["project_id"], current_phase)

    checkpoint = rt.create_checkpoint(
        project_id=active["project_id"],
        phase=str(state.get("current_phase", "")),
        reason=f"Approved at {current_phase}",
    )

    rt.record_audit(
        "human",
        "approve_phase",
        project_id=active["project_id"],
        phase=current_phase,
        next_phase=str(state.get("current_phase", "")),
        checkpoint_id=checkpoint.checkpoint_id,
    )
    return state


def run_validation(rt: GraphHost, project_id: str | None = None) -> dict[str, Any]:
    """Run validators against the active project's current-phase artifacts.

    Executes the same validator dispatch the QC node uses, but against the
    live project state and *without* advancing the phase. Validator-produced
    findings replace any prior validator findings (issues tagged with a
    ``validator_id``) while non-validator blockers are preserved, then the
    refreshed issues and validation reports are merged back and persisted.
    """

    active = rt.get_project(project_id) if project_id else rt.get_active()
    if active is None:
        raise ValueError("No active project.")
    project_id_value = str(active["project_id"])

    preserved_issues = [
        issue
        for issue in cast(list[dict[str, Any]], active.get("issues", []))
        if not (isinstance(issue, dict) and issue.get("validator_id"))
    ]
    # `_run_validators` takes the graph-state contract, but this path holds a
    # persisted *project-state* mapping. A TypedDict cannot be built from a
    # computed key (`[literal-required]`) and a plain dict is not assignable to
    # one, so the projection names literally every key the validator chain reads
    # or writes. That set is closed, and was enumerated from the chain's own
    # writes: reading one key less would hand a validator a missing value, and
    # writing one key less would silently drop a mutation on the way back.
    # The `_orchestrator__` key grammar has one author, so the candidate refs are
    # read through the accessor rather than by rebuilding the key here (the
    # orchestrator-surface guard enforces exactly that).

    seeded_candidates = get_candidate_refs(active)
    # Project-state values are `object` here, so each collection is narrowed by
    # `isinstance` rather than asserted with a `cast`: a cast would claim a shape
    # this path has no evidence for, and an unexpected shape should degrade to an
    # empty collection rather than travel on as a lie.
    raw_artifact_refs = active.get("artifact_refs")
    artifact_refs = (
        [str(ref) for ref in raw_artifact_refs] if isinstance(raw_artifact_refs, list) else []
    )
    raw_routing = active.get("_routing_decisions")
    routing_decisions = (
        [entry for entry in raw_routing if isinstance(entry, dict)]
        if isinstance(raw_routing, list)
        else []
    )
    raw_pending = active.get("_pending_row_updates")
    pending_row_updates = list(raw_pending) if isinstance(raw_pending, list) else []
    working: StudioGraphState = {
        # read by the chain
        "project_id": project_id_value,
        "current_phase": str(active.get("current_phase", "")),
        "artifact_refs": artifact_refs,
        # read and written by the chain
        "issues": list(preserved_issues),
        "_validation_reports": [],
        "consensus_report_ref": str(active.get("consensus_report_ref", "")),
        "qc_patch_ref": str(active.get("qc_patch_ref", "")),
        "shot_matrix_ref": str(active.get("shot_matrix_ref", "")),
        # written only on paths `_save_artifact`/`_run_agent` reach
        "_orchestrator__candidate_refs": dict(seeded_candidates),
        "_last_kb_context_ref": str(active.get("_last_kb_context_ref", "")),
        "_routing_decisions": routing_decisions,
        "_repair_feedback": str(active.get("_repair_feedback", "")),
        "_pending_row_updates": pending_row_updates,
    }
    # `_services` is a declared graph-state key, so the literal spelling is
    # used here: a TypedDict cannot be indexed by the imported constant.
    working["_services"] = rt.services
    _run_validators(working)
    working.pop("_services", None)

    active["issues"] = list(working.get("issues", []))
    active["_validation_reports"] = list(working.get("_validation_reports", []))
    # Every key the chain can write is carried back, not only the two this
    # function reports: dropping the rest would lose validator side effects.
    for side_effect_key in (
        "_orchestrator__candidate_refs",
        "_last_kb_context_ref",
        "_routing_decisions",
        "_repair_feedback",
        "qc_patch_ref",
    ):
        side_effect_value = working.get(side_effect_key)
        if side_effect_value:
            active[side_effect_key] = side_effect_value
    consensus_ref = working.get("consensus_report_ref")
    if consensus_ref:
        active["consensus_report_ref"] = consensus_ref
    rt.projects[project_id_value] = active
    rt.persist_project_state(project_id_value)
    rt.record_audit(
        "human",
        "run_validation",
        project_id=project_id_value,
        phase=str(active.get("current_phase", "")),
    )
    return active


def request_revision(rt: GraphHost, note: str = "") -> dict[str, Any]:
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
            rt.record_audit(
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
    rt.persist_project_state(active["project_id"])
    save_graph_state(rt, dict(state), active["project_id"])

    rt.record_audit(
        "human",
        "request_revision",
        project_id=active["project_id"],
        note=note,
    )
    return state


def advance_to_next_phase(rt: GraphHost, state: dict[str, Any]) -> dict[str, Any]:
    current_phase = str(state.get("current_phase", ""))
    if current_phase not in PHASE_SEQUENCE:
        rt.projects[state["project_id"]] = state
        rt.persist_project_state(state["project_id"])
        return state

    successor = next_phase(current_phase)
    if successor is None:
        final_state = dict(state)
        final_state["completed"] = True
        final_state["human_approval_phase"] = ""
        rt.projects[state["project_id"]] = final_state
        rt.persist_project_state(state["project_id"])
        return final_state

    advanced_state = run_phase_node(rt, state, successor)
    rt.projects[state["project_id"]] = advanced_state
    rt.persist_project_state(state["project_id"])
    return advanced_state


def run_phase_node(rt: GraphHost, state: dict[str, Any], phase: str) -> dict[str, Any]:

    node = resolved_phase_node(phase)
    # Inject graph services so nodes can invoke agents and persist artifacts
    state = dict(state)
    state[SERVICES_KEY] = rt.services
    node_result = _call_phase_node(node, state)
    # Direct node calls bypass channel accumulation, so replay the graph's own
    # merge rule from the state schema's `Annotated` declarations. This used to
    # be a hand-written reducer table here, which disagreed with the schema on
    # four channels and could not see a channel added later.
    merged = apply_node_update(state, node_result)
    # Strip runtime-only keys that must not leak into persisted state
    merged.pop(SERVICES_KEY, None)
    return merged


def _call_phase_node(node: Any, state: dict[str, Any]) -> dict[str, Any]:
    """Invoke one phase node, whether it is a plain function or a subgraph.

    Nine phases are plain node functions, which are called directly. `qc` is a
    compiled LangGraph subgraph (the parallel validator fan-out), which is
    invoked rather than called — and it needs the config to carry a
    ``thread_id`` for its checkpointer, so it is given a synthetic one. Without
    this branch the QC phase raises ``'CompiledStateGraph' object is not
    callable`` the moment the manual path reaches it.
    """
    if isinstance(node, CompiledStateGraph):
        result = node.invoke(state, {"configurable": {"thread_id": "manual-phase-node"}})
        return dict(result)
    result = node(state)
    return dict(result)
