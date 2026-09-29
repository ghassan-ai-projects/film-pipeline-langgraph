"""Orchestrator state helpers — manage the orchestrator's decision domain.

Operates on the existing dict-based graph state to avoid a broad refactor.
Each function reads or writes a specific slice of orchestrator state:
candidate/approved refs, review cycles, revision requests, routing decisions,
failure decisions, convergence signals, provider health, and budget awareness.

The architecture blueprint (Section 2) defines the orchestrator as the
central decision-maker. This module gives it the state it needs to reason.

**Public surface.** ``__all__`` below is the declared contract: the channel
registry plus the read/write accessors for the eight state slices named above,
and the human-approval gate every node consults. Everything else — the
``_ORCH_NS``-derived key constants and the private helpers — is internal.
Consumers outside this module reach the state only through these accessors,
never by building a key themselves. The guard suite enforcing both rules is
``tests/unit/orchestration/test_orchestrator_state_surface.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast

from film_pipeline.governance.orchestrator_reads import ORCH_NS as _ORCH_NS
from film_pipeline.orchestration.state_schema import StudioGraphState

__all__ = [
    "ORCH_CHANNELS",
    "OrchChannelSpec",
    "add_failure_decision",
    "add_revision_request",
    "advance_review_round",
    "close_review_cycle",
    "ensure_orchestrator_state",
    "get_active_review_cycle",
    "get_all_revisions",
    "get_approved_refs",
    "get_blocked_providers",
    "get_candidate_refs",
    "get_convergence",
    "get_convergence_round",
    "get_execution_brief",
    "get_failure_decisions",
    "get_healthy_providers",
    "get_latest_failure_decision",
    "get_latest_routing_decision",
    "get_pending_revisions",
    "get_provider_health_snapshot",
    "get_routing_decisions",
    "has_blocking_failure",
    "has_pending_revision",
    "increment_convergence_round",
    "init_convergence",
    "init_refs",
    "is_provider_blocked",
    "is_stalled",
    "mark_stalled",
    "record_routing_decision",
    "require_human_approval",
    "resolve_artifact",
    "resolve_revision",
    "set_approved_ref",
    "set_candidate_ref",
    "set_execution_brief",
    "start_review_cycle",
    "update_provider_health",
]

# --- Stable state keys -------------------------------------------------------
# These keys live inside the graph state dict.  They are namespaced with a
# leading underscore to avoid accidental collisions with existing state fields.

# Candidate refs: the latest version of each artifact family, regardless of
# approval status.  Shape: dict[artifact_family → ref_string]
_CANDIDATE_REFS = f"{_ORCH_NS}__candidate_refs"

# Approved refs: the latest approved version of each artifact family.
# Shape: dict[artifact_family → ref_string]
_APPROVED_REFS = f"{_ORCH_NS}__approved_refs"

# Active review cycles: one per phase with an in-progress review.
# Shape: list[dict] with keys: phase, started_at, round_count, status, strategy
_ACTIVE_REVIEW_CYCLES = f"{_ORCH_NS}__active_review_cycles"

# Pending revision requests.
# Shape: list[RevisionRequest] (serialized as dict)
_PENDING_REVISIONS = f"{_ORCH_NS}__pending_revisions"

# Orchestrator routing decisions.
# Shape: list[RoutingDecision] (serialized as dict)
_ROUTING_DECISIONS = f"{_ORCH_NS}__routing_decisions"

# Convergence tracking per phase.
# Shape: dict[phase → dict{round_count, stalled, escalation_reason}]
_CONVERGENCE = f"{_ORCH_NS}__convergence"

# Failure decisions from the failure-handling agent.
# Shape: list[FailureDecision] (serialized as dict)
_FAILURE_DECISIONS = f"{_ORCH_NS}__failure_decisions"

# Provider health snapshot (cached, refreshed on provider interaction).
# Shape: dict[provider_id → ProviderHealthState as dict]
_PROVIDER_HEALTH_SNAPSHOT = f"{_ORCH_NS}__provider_health_snapshot"

# Execution brief: the orchestrator's structural contract for the film.
# Populated by StructureExtractorAgent after script phase. Used by Gate A/B/C
# validators to enforce shot-count, runtime, and field invariants.
_EXECUTION_BRIEF = f"{_ORCH_NS}__execution_brief"


def require_human_approval(state: Mapping[str, object]) -> bool:
    """Read the human-approval requirement from resolved graph config.

    Defaults to ``True`` when the key is missing or the config is
    unpopulated, keeping human gates enabled unless a profile opts out.

    Public because the node layer's gate decisions all consult it: three
    modules imported the private form, which made ownership nominal (O7).
    """
    cfg = state.get("resolved_config", {})
    if isinstance(cfg, dict):
        studio = cfg.get("studio", {})
        if isinstance(studio, dict):
            return bool(studio.get("require_human_approval", True))
    return True


# --- Channel registry --------------------------------------------------------


@dataclass(frozen=True)
class OrchChannelSpec:
    """Declarative contract for one state key crossing the node boundary.

    ``propagation`` selects the copy policy applied by
    ``graph.nodes._agent_handoff._propagate_side_effects``:

    - ``full``        — copied whenever present on the node's working copy.
    - ``full_truthy`` — copied only when present and truthy.
    - ``append_only`` — reducer channel; only entries appended after the
      node's input snapshot are contributed.
    - ``explicit``    — never auto-propagated; writers return the key in
      their own update dicts (or a dedicated promotion path owns it).

    Adding a state key here is mandatory: the channel-registry parity tests
    fail when an orchestrator constant or graph-schema key lacks a row.
    """

    key: str
    propagation: Literal["full", "full_truthy", "append_only", "explicit"]
    note: str = ""


ORCH_CHANNELS: tuple[OrchChannelSpec, ...] = (
    OrchChannelSpec(
        _CANDIDATE_REFS,
        "full_truthy",
        "published artifact refs; promoted by approve_phase_node",
    ),
    OrchChannelSpec(
        _APPROVED_REFS,
        "explicit",
        "approve_phase_node returns promoted refs in its own update dict",
    ),
    OrchChannelSpec(
        _ACTIVE_REVIEW_CYCLES,
        "explicit",
        "review-cycle writers return cycles in updates",
    ),
    OrchChannelSpec(
        _PENDING_REVISIONS,
        "explicit",
        "revision writers return pending revisions in updates",
    ),
    OrchChannelSpec(
        _ROUTING_DECISIONS,
        "explicit",
        "shadow namespace; deletion scheduled with D13/P1 wire-or-delete",
    ),
    OrchChannelSpec(
        _CONVERGENCE,
        "explicit",
        "review-loop nodes return convergence snapshots in updates",
    ),
    OrchChannelSpec(
        _FAILURE_DECISIONS,
        "explicit",
        "dormant writer; wiring decided in D13/P1 (failure-handling agent)",
    ),
    OrchChannelSpec(
        _PROVIDER_HEALTH_SNAPSHOT,
        "explicit",
        "dormant writer; wiring decided in D13/P1 (provider health)",
    ),
    OrchChannelSpec(
        _EXECUTION_BRIEF,
        "full",
        "structural brief from shot_bible extraction; DF-F2 fix — must reach "
        "live state so validators stop pinning artifact version 1",
    ),
    OrchChannelSpec(
        "_routing_decisions",
        "full",
        "handoff records recorded by _record_handoff during agent runs",
    ),
    OrchChannelSpec(
        "_repair_feedback",
        "full",
        "copied on present (even when cleared to '') so consumed feedback "
        "clearing survives the boundary",
    ),
    OrchChannelSpec(
        "_validation_reports",
        "full",
        "validator reports accumulated within the node run",
    ),
    OrchChannelSpec("issues", "append_only", "append-only issues reducer channel"),
    OrchChannelSpec(
        "validation_report_refs", "append_only", "append-only report-ref reducer channel"
    ),
)


# --- Candidate vs approved refs ----------------------------------------------


def init_refs(state: dict[str, Any]) -> None:
    """Ensure the candidate and approved ref domains exist in state."""
    if _CANDIDATE_REFS not in state:
        state[_CANDIDATE_REFS] = {}
    if _APPROVED_REFS not in state:
        state[_APPROVED_REFS] = {}


def get_candidate_refs(state: Mapping[str, object]) -> dict[str, str]:
    """Return the latest candidate ref for each artifact family."""
    return cast(dict[str, str], state.get(_CANDIDATE_REFS, {}))


def get_approved_refs(state: Mapping[str, object]) -> dict[str, str]:
    """Return the latest approved ref for each artifact family."""
    return cast(dict[str, str], state.get(_APPROVED_REFS, {}))


def set_candidate_ref(state: dict[str, Any], family: str, ref: str) -> None:
    """Record a new candidate ref for an artifact family."""
    state.setdefault(_CANDIDATE_REFS, {})[family] = ref


def set_approved_ref(state: dict[str, Any], family: str, ref: str) -> None:
    """Record an approved ref, superseding any previous approved ref."""
    state.setdefault(_APPROVED_REFS, {})[family] = ref


def resolve_artifact(
    state: Mapping[str, object], family: str, *, require_approved: bool = False
) -> str | None:
    """Resolve the best available ref for an artifact family.

    When ``require_approved`` is True, only returns an approved ref.
    When False, falls back to the latest candidate.
    """
    approved = get_approved_refs(state)
    if family in approved:
        return approved[family]
    if require_approved:
        return None
    candidates = get_candidate_refs(state)
    return candidates.get(family)


# --- Review cycles -----------------------------------------------------------


def get_active_review_cycle(state: Mapping[str, object], phase: str) -> dict[str, Any] | None:
    """Return the active review cycle for a phase, if any."""
    raw_cycles = state.get(_ACTIVE_REVIEW_CYCLES)
    cycles = raw_cycles if isinstance(raw_cycles, list) else []
    for c in cycles:
        if isinstance(c, dict) and c.get("phase") == phase:
            return c
    return None


def start_review_cycle(
    state: dict[str, Any],
    phase: str,
    *,
    strategy: str = "single",
) -> dict[str, Any]:
    """Begin a new review cycle for a phase and return it."""
    cycle: dict[str, Any] = {
        "phase": phase,
        "started_at": datetime.now().isoformat(),
        "round_count": 0,
        "status": "active",
        "strategy": strategy,
    }
    state.setdefault(_ACTIVE_REVIEW_CYCLES, []).append(cycle)
    return cycle


def advance_review_round(state: Mapping[str, object], phase: str) -> dict[str, Any] | None:
    """Increment the round counter for an active review cycle."""
    cycle = get_active_review_cycle(state, phase)
    if cycle is None:
        return None
    cycle["round_count"] = cycle.get("round_count", 0) + 1
    return cycle


def close_review_cycle(
    state: Mapping[str, object], phase: str, *, status: str = "completed"
) -> None:
    """Close the active review cycle for a phase."""
    cycle = get_active_review_cycle(state, phase)
    if cycle:
        cycle["status"] = status


# --- Revision requests -------------------------------------------------------


def add_revision_request(
    state: dict[str, Any],
    artifact_refs: list[str],
    *,
    note: str = "",
    from_version: int = 1,
) -> dict[str, Any]:
    """Create a durable revision request and return it."""
    revision: dict[str, Any] = {
        "artifact_refs": artifact_refs,
        "note": note,
        "from_version": from_version,
        "created_at": datetime.now().isoformat(),
        "resolved": False,
    }
    state.setdefault(_PENDING_REVISIONS, []).append(revision)
    return revision


def get_pending_revisions(state: Mapping[str, object]) -> list[dict[str, Any]]:
    """Return all unresolved revision requests."""
    raw_revisions = state.get(_PENDING_REVISIONS)
    revisions = raw_revisions if isinstance(raw_revisions, list) else []
    return [r for r in revisions if isinstance(r, dict) and not r.get("resolved", False)]


def get_all_revisions(state: Mapping[str, object]) -> list[dict[str, Any]]:
    """Return the whole revision slice, resolved entries included.

    The accessor exists for the node that must carry the slice across the
    boundary: a propagation write copies state, so it needs the complete list,
    not the unresolved subset that :func:`get_pending_revisions` returns.
    """
    revisions = state.get(_PENDING_REVISIONS, [])
    return list(revisions) if isinstance(revisions, list) else []


def has_pending_revision(state: Mapping[str, object]) -> bool:
    """Return True if any revision request is unresolved."""
    return len(get_pending_revisions(state)) > 0


def resolve_revision(state: Mapping[str, object], artifact_ref: str) -> None:
    """Mark a revision request as resolved for a specific artifact.

    ``Mapping`` rather than a plain dict so a graph-state TypedDict is accepted;
    the entries are mutated in place, which the read-only container type allows.
    """
    pending = state.get(_PENDING_REVISIONS)
    revisions: list[dict[str, Any]] = pending if isinstance(pending, list) else []
    for r in revisions:
        if isinstance(r, dict) and artifact_ref in r.get("artifact_refs", []):
            r["resolved"] = True
            r["resolved_at"] = datetime.now().isoformat()


# --- Routing decisions -------------------------------------------------------


def record_routing_decision(
    state: dict[str, Any],
    selected_agent: str,
    reason: str,
    *,
    input_refs: list[str] | None = None,
    expected_output: str = "",
    candidate_agents: list[str] | None = None,
) -> dict[str, Any]:
    """Persist an explainable routing decision."""
    decision: dict[str, Any] = {
        "routing_decision_id": f"route:{datetime.now().strftime('%Y%m%d%H%M%S')}:{selected_agent}",
        "selected_agent": selected_agent,
        "reason": reason,
        "input_refs": input_refs or [],
        "expected_output": expected_output,
        "candidate_agents": candidate_agents or [],
        "recorded_at": datetime.now().isoformat(),
    }
    state.setdefault(_ROUTING_DECISIONS, []).append(decision)
    return decision


def get_routing_decisions(state: Mapping[str, object]) -> list[dict[str, Any]]:
    """Return all routing decisions for this project."""
    return cast(list[dict[str, Any]], state.get(_ROUTING_DECISIONS, []))


def get_latest_routing_decision(state: Mapping[str, object]) -> dict[str, Any] | None:
    """Return the most recent routing decision."""
    decisions = get_routing_decisions(state)
    return decisions[-1] if decisions else None


# --- Convergence tracking ----------------------------------------------------


def get_convergence(state: Mapping[str, object]) -> dict[str, dict[str, Any]]:
    """Return the whole convergence slice, keyed by phase.

    The accessor exists so a node that needs to *carry* the slice across the
    boundary — rather than read one phase's round count — does not rebuild the
    ``_orchestrator__convergence`` key by hand. Returns a deep copy, so a
    caller can assign it into a node update without aliasing live state.
    """
    from copy import deepcopy

    raw = state.get(_CONVERGENCE, {})
    return deepcopy(raw) if isinstance(raw, dict) else {}


def get_convergence_round(state: Mapping[str, object], phase: str) -> int:
    """Return the recorded round count for a phase, defaulting to 1.

    Reads through this accessor rather than indexing the slice so the
    "missing means first round" rule has one author.
    """
    conv = state.get(_CONVERGENCE, {})
    if not isinstance(conv, dict):
        return 1
    phase_conv = conv.get(phase, {})
    if not isinstance(phase_conv, dict):
        return 1
    return int(phase_conv.get("round_count", 1) or 1)


def init_convergence(state: StudioGraphState, phase: str) -> None:
    """Initialize convergence tracking for a phase."""
    state.setdefault("_orchestrator__convergence", {})[phase] = {
        "round_count": 0,
        "stalled": False,
        "escalation_reason": "",
    }


def increment_convergence_round(state: StudioGraphState, phase: str) -> int:
    """Increment the convergence round counter. Returns the new count."""
    conv = state.setdefault("_orchestrator__convergence", {}).setdefault(
        phase, {"round_count": 0, "stalled": False, "escalation_reason": ""}
    )
    conv["round_count"] += 1
    return cast(int, conv["round_count"])


def is_stalled(state: Mapping[str, object], phase: str, *, max_rounds: int = 5) -> bool:
    """Return True if the phase has exceeded the max rounds without converging.

    Read-only. The key is the module constant ``_CONVERGENCE``, which a TypedDict
    cannot be indexed by, so this reads structurally through ``Mapping`` rather
    than naming ``StudioGraphState``.
    """
    raw = state.get(_CONVERGENCE, {})
    if not isinstance(raw, dict):
        return False
    conv = raw.get(phase)
    if not isinstance(conv, dict):
        return False
    return bool(conv.get("stalled", False)) or conv.get("round_count", 0) >= max_rounds


def mark_stalled(state: StudioGraphState, phase: str, reason: str) -> None:
    """Mark a phase as non-convergent with a reason."""
    conv = state.setdefault("_orchestrator__convergence", {}).setdefault(
        phase, {"round_count": 0, "stalled": False, "escalation_reason": ""}
    )
    conv["stalled"] = True
    conv["escalation_reason"] = reason


# --- Failure decisions -------------------------------------------------------


def add_failure_decision(state: dict[str, Any], decision: dict[str, Any]) -> None:
    """Persist a failure decision from the failure-handling agent."""
    state.setdefault(_FAILURE_DECISIONS, []).append(decision)


def get_failure_decisions(state: Mapping[str, object]) -> list[dict[str, Any]]:
    """Return all failure decisions for this project."""
    return cast(list[dict[str, Any]], state.get(_FAILURE_DECISIONS, []))


def get_latest_failure_decision(state: Mapping[str, object]) -> dict[str, Any] | None:
    """Return the most recent unresolved failure decision."""
    decisions = get_failure_decisions(state)
    return decisions[-1] if decisions else None


def has_blocking_failure(state: Mapping[str, object]) -> bool:
    """Return True if any failure decision has severity='blocking'."""
    return any(d.get("severity") == "blocking" for d in get_failure_decisions(state))


# --- Provider health snapshot ------------------------------------------------


def update_provider_health(state: dict[str, Any], provider_id: str, health: dict[str, Any]) -> None:
    """Cache a provider's health state in the orchestrator domain."""
    snapshot = state.setdefault(_PROVIDER_HEALTH_SNAPSHOT, {})
    health["cached_at"] = datetime.now().isoformat()
    snapshot[provider_id] = health


def get_provider_health_snapshot(
    state: Mapping[str, object], provider_id: str
) -> dict[str, Any] | None:
    """Return the cached health state for a provider."""
    raw_snapshot = state.get(_PROVIDER_HEALTH_SNAPSHOT)
    snapshot = raw_snapshot if isinstance(raw_snapshot, dict) else {}
    health = snapshot.get(provider_id)
    return health if isinstance(health, dict) else None


def is_provider_blocked(state: Mapping[str, object], provider_id: str) -> bool:
    """Return True if the cached health status indicates the provider is blocked."""
    health = get_provider_health_snapshot(state, provider_id)
    if health is None:
        return False
    status = health.get("status", "")
    return cast(bool, status.startswith("blocked_") or status == "disabled_by_user")


def get_blocked_providers(state: Mapping[str, object]) -> list[str]:
    """Return the list of provider IDs that are currently blocked."""
    raw_snapshot = state.get(_PROVIDER_HEALTH_SNAPSHOT)
    snapshot = raw_snapshot if isinstance(raw_snapshot, dict) else {}
    return [
        pid
        for pid, health in snapshot.items()
        if isinstance(health, dict)
        if health.get("status", "").startswith("blocked_")
        or health.get("status") == "disabled_by_user"
    ]


def get_healthy_providers(state: Mapping[str, object]) -> list[str]:
    """Return the list of provider IDs that are healthy or degraded."""
    raw_snapshot = state.get(_PROVIDER_HEALTH_SNAPSHOT)
    snapshot = raw_snapshot if isinstance(raw_snapshot, dict) else {}
    return [
        pid
        for pid, health in snapshot.items()
        if isinstance(health, dict) and health.get("status") in ("healthy", "degraded")
    ]


# --- Execution brief ---------------------------------------------------------


def set_execution_brief(state: StudioGraphState, brief: Any) -> None:
    """Cache the ExecutionBrief in orchestrator state.

    The brief is stored as a dict for serialisation compatibility with the
    graph state. Callers can pass either an ``ExecutionBrief`` instance or a
    dict with the same shape.

    Takes the graph-state contract rather than a plain dict: the key is declared
    in ``StudioGraphState``, and it is written below by its literal spelling.
    ``_EXECUTION_BRIEF`` is the same string, but a TypedDict cannot be indexed by
    a constant (``[literal-required]``), so the literal is used here and the
    constant remains the one definition the *readers* resolve through.
    """
    if hasattr(brief, "model_dump"):
        state["_orchestrator__execution_brief"] = brief.model_dump(mode="json")
    elif isinstance(brief, dict):
        state["_orchestrator__execution_brief"] = dict(brief)
    else:
        state["_orchestrator__execution_brief"] = brief


def get_execution_brief(state: Mapping[str, object]) -> Any | None:
    """Return the cached ExecutionBrief from orchestrator state.

    Returns the raw cached dict/object. Callers should validate the shape
    before use. Returns ``None`` if no brief has been set.
    """
    return state.get(_EXECUTION_BRIEF)


# --- Initialization ----------------------------------------------------------


def ensure_orchestrator_state(state: dict[str, Any]) -> None:
    """Ensure all orchestrator state domains exist in the state dict.

    Call once per project creation to avoid key errors in downstream code.
    """
    init_refs(state)
    state.setdefault(_ACTIVE_REVIEW_CYCLES, [])
    state.setdefault(_PENDING_REVISIONS, [])
    state.setdefault(_ROUTING_DECISIONS, [])
    state.setdefault(_FAILURE_DECISIONS, [])
    state.setdefault(_PROVIDER_HEALTH_SNAPSHOT, {})
    state.setdefault(_CONVERGENCE, {})
