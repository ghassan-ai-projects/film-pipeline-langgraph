"""Orchestrator state helpers — manage the orchestrator's decision domain.

Operates on the existing dict-based graph state to avoid a broad refactor.
Each function reads or writes a specific slice of orchestrator state:
candidate/approved refs, review cycles, revision requests, routing decisions,
failure decisions, convergence signals, provider health, and budget awareness.

The architecture blueprint (Section 2) defines the orchestrator as the
central decision-maker. This module gives it the state it needs to reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast

# --- Stable state keys -------------------------------------------------------
# These keys live inside the graph state dict.  They are namespaced with a
# leading underscore and an "orch:" prefix to avoid accidental collisions with
# existing state fields.

_ORCH_NS = "_orchestrator"

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

# Budget state snapshot for routing awareness.
# Shape: dict with keys: cap_usd, spent_usd, remaining_usd, blocking_threshold_exceeded
_BUDGET_SNAPSHOT = f"{_ORCH_NS}__budget_snapshot"

# Execution brief: the orchestrator's structural contract for the film.
# Populated by StructureExtractorAgent after script phase. Used by Gate A/B/C
# validators to enforce shot-count, runtime, and field invariants.
_EXECUTION_BRIEF = f"{_ORCH_NS}__execution_brief"


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
        _BUDGET_SNAPSHOT,
        "explicit",
        "dormant writer; wiring decided in D13/P1 (budget recording)",
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


def get_candidate_refs(state: dict[str, Any]) -> dict[str, str]:
    """Return the latest candidate ref for each artifact family."""
    return cast(dict[str, str], state.get(_CANDIDATE_REFS, {}))


def get_approved_refs(state: dict[str, Any]) -> dict[str, str]:
    """Return the latest approved ref for each artifact family."""
    return cast(dict[str, str], state.get(_APPROVED_REFS, {}))


def set_candidate_ref(state: dict[str, Any], family: str, ref: str) -> None:
    """Record a new candidate ref for an artifact family."""
    state.setdefault(_CANDIDATE_REFS, {})[family] = ref


def set_approved_ref(state: dict[str, Any], family: str, ref: str) -> None:
    """Record an approved ref, superseding any previous approved ref."""
    state.setdefault(_APPROVED_REFS, {})[family] = ref


def resolve_artifact(
    state: dict[str, Any], family: str, *, require_approved: bool = False
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


def get_active_review_cycle(state: dict[str, Any], phase: str) -> dict[str, Any] | None:
    """Return the active review cycle for a phase, if any."""
    cycles: list[dict[str, Any]] = state.get(_ACTIVE_REVIEW_CYCLES, [])
    for c in cycles:
        if c.get("phase") == phase:
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


def advance_review_round(state: dict[str, Any], phase: str) -> dict[str, Any] | None:
    """Increment the round counter for an active review cycle."""
    cycle = get_active_review_cycle(state, phase)
    if cycle is None:
        return None
    cycle["round_count"] = cycle.get("round_count", 0) + 1
    return cycle


def close_review_cycle(state: dict[str, Any], phase: str, *, status: str = "completed") -> None:
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


def get_pending_revisions(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all unresolved revision requests."""
    revisions: list[dict[str, Any]] = state.get(_PENDING_REVISIONS, [])
    return [r for r in revisions if not r.get("resolved", False)]


def has_pending_revision(state: dict[str, Any]) -> bool:
    """Return True if any revision request is unresolved."""
    return len(get_pending_revisions(state)) > 0


def resolve_revision(state: dict[str, Any], artifact_ref: str) -> None:
    """Mark a revision request as resolved for a specific artifact."""
    revisions: list[dict[str, Any]] = state.get(_PENDING_REVISIONS, [])
    for r in revisions:
        if artifact_ref in r.get("artifact_refs", []):
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


def get_routing_decisions(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all routing decisions for this project."""
    return cast(list[dict[str, Any]], state.get(_ROUTING_DECISIONS, []))


def get_latest_routing_decision(state: dict[str, Any]) -> dict[str, Any] | None:
    """Return the most recent routing decision."""
    decisions = get_routing_decisions(state)
    return decisions[-1] if decisions else None


# --- Convergence tracking ----------------------------------------------------


def init_convergence(state: dict[str, Any], phase: str) -> None:
    """Initialize convergence tracking for a phase."""
    state.setdefault(_CONVERGENCE, {})[phase] = {
        "round_count": 0,
        "stalled": False,
        "escalation_reason": "",
    }


def increment_convergence_round(state: dict[str, Any], phase: str) -> int:
    """Increment the convergence round counter. Returns the new count."""
    conv = state.setdefault(_CONVERGENCE, {}).setdefault(
        phase, {"round_count": 0, "stalled": False, "escalation_reason": ""}
    )
    conv["round_count"] += 1
    return cast(int, conv["round_count"])


def is_stalled(state: dict[str, Any], phase: str, *, max_rounds: int = 5) -> bool:
    """Return True if the phase has exceeded the max rounds without converging."""
    conv = state.get(_CONVERGENCE, {}).get(phase)
    if conv is None:
        return False
    return bool(conv.get("stalled", False)) or conv.get("round_count", 0) >= max_rounds


def mark_stalled(state: dict[str, Any], phase: str, reason: str) -> None:
    """Mark a phase as non-convergent with a reason."""
    conv = state.setdefault(_CONVERGENCE, {}).setdefault(
        phase, {"round_count": 0, "stalled": False, "escalation_reason": ""}
    )
    conv["stalled"] = True
    conv["escalation_reason"] = reason


# --- Failure decisions -------------------------------------------------------


def add_failure_decision(state: dict[str, Any], decision: dict[str, Any]) -> None:
    """Persist a failure decision from the failure-handling agent."""
    state.setdefault(_FAILURE_DECISIONS, []).append(decision)


def get_failure_decisions(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all failure decisions for this project."""
    return cast(list[dict[str, Any]], state.get(_FAILURE_DECISIONS, []))


def get_latest_failure_decision(state: dict[str, Any]) -> dict[str, Any] | None:
    """Return the most recent unresolved failure decision."""
    decisions = get_failure_decisions(state)
    return decisions[-1] if decisions else None


def has_blocking_failure(state: dict[str, Any]) -> bool:
    """Return True if any failure decision has severity='blocking'."""
    return any(d.get("severity") == "blocking" for d in get_failure_decisions(state))


# --- Provider health snapshot ------------------------------------------------


def update_provider_health(state: dict[str, Any], provider_id: str, health: dict[str, Any]) -> None:
    """Cache a provider's health state in the orchestrator domain."""
    snapshot = state.setdefault(_PROVIDER_HEALTH_SNAPSHOT, {})
    health["cached_at"] = datetime.now().isoformat()
    snapshot[provider_id] = health


def get_provider_health_snapshot(state: dict[str, Any], provider_id: str) -> dict[str, Any] | None:
    """Return the cached health state for a provider."""
    return cast(dict[str, Any] | None, state.get(_PROVIDER_HEALTH_SNAPSHOT, {}).get(provider_id))


def is_provider_blocked(state: dict[str, Any], provider_id: str) -> bool:
    """Return True if the cached health status indicates the provider is blocked."""
    health = get_provider_health_snapshot(state, provider_id)
    if health is None:
        return False
    status = health.get("status", "")
    return cast(bool, status.startswith("blocked_") or status == "disabled_by_user")


def get_blocked_providers(state: dict[str, Any]) -> list[str]:
    """Return the list of provider IDs that are currently blocked."""
    snapshot = state.get(_PROVIDER_HEALTH_SNAPSHOT, {})
    return [
        pid
        for pid, health in snapshot.items()
        if health.get("status", "").startswith("blocked_")
        or health.get("status") == "disabled_by_user"
    ]


def get_healthy_providers(state: dict[str, Any]) -> list[str]:
    """Return the list of provider IDs that are healthy or degraded."""
    snapshot = state.get(_PROVIDER_HEALTH_SNAPSHOT, {})
    return [
        pid for pid, health in snapshot.items() if health.get("status") in ("healthy", "degraded")
    ]


# --- Budget snapshot ---------------------------------------------------------


def update_budget_snapshot(
    state: dict[str, Any],
    *,
    cap_usd: float = 0.0,
    spent_usd: float = 0.0,
    threshold_exceeded: bool = False,
) -> None:
    """Cache budget awareness for routing decisions."""
    state[_BUDGET_SNAPSHOT] = {
        "cap_usd": cap_usd,
        "spent_usd": spent_usd,
        "remaining_usd": max(0.0, cap_usd - spent_usd),
        "threshold_exceeded": threshold_exceeded,
        "cached_at": datetime.now().isoformat(),
    }


def get_budget_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """Return the cached budget snapshot."""
    return cast(
        dict[str, Any],
        state.get(
            _BUDGET_SNAPSHOT,
            {"cap_usd": 0.0, "spent_usd": 0.0, "remaining_usd": 0.0, "threshold_exceeded": False},
        ),
    )


def is_budget_blocked(state: dict[str, Any]) -> bool:
    """Return True if the budget threshold has been exceeded."""
    return cast(bool, get_budget_snapshot(state).get("threshold_exceeded", False))


# --- Execution brief ---------------------------------------------------------


def set_execution_brief(state: dict[str, Any], brief: Any) -> None:
    """Cache the ExecutionBrief in orchestrator state.

    The brief is stored as a dict for serialisation compatibility with the
    graph state. Callers can pass either an ``ExecutionBrief`` instance or a
    dict with the same shape.
    """
    if hasattr(brief, "model_dump"):
        state[_EXECUTION_BRIEF] = brief.model_dump(mode="json")
    elif isinstance(brief, dict):
        state[_EXECUTION_BRIEF] = dict(brief)
    else:
        state[_EXECUTION_BRIEF] = brief


def get_execution_brief(state: dict[str, Any]) -> Any | None:
    """Return the cached ExecutionBrief from orchestrator state.

    Returns the raw cached dict/object. Callers should validate the shape
    before use. Returns ``None`` if no brief has been set.
    """
    return state.get(_EXECUTION_BRIEF)


def has_execution_brief(state: dict[str, Any]) -> bool:
    """Return True if an ExecutionBrief exists in orchestrator state."""
    return _EXECUTION_BRIEF in state


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
    state.setdefault(
        _BUDGET_SNAPSHOT,
        {
            "cap_usd": 0.0,
            "spent_usd": 0.0,
            "remaining_usd": 0.0,
            "threshold_exceeded": False,
        },
    )
    state.setdefault(_CONVERGENCE, {})
