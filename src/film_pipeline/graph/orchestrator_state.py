"""Compatibility aliases for :mod:`film_pipeline.orchestration.orchestrator_state`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.orchestration.orchestrator_state import (
    _ACTIVE_REVIEW_CYCLES as _ACTIVE_REVIEW_CYCLES,
)
from film_pipeline.orchestration.orchestrator_state import _APPROVED_REFS as _APPROVED_REFS
from film_pipeline.orchestration.orchestrator_state import _BUDGET_SNAPSHOT as _BUDGET_SNAPSHOT
from film_pipeline.orchestration.orchestrator_state import _CANDIDATE_REFS as _CANDIDATE_REFS
from film_pipeline.orchestration.orchestrator_state import _CONVERGENCE as _CONVERGENCE
from film_pipeline.orchestration.orchestrator_state import _EXECUTION_BRIEF as _EXECUTION_BRIEF
from film_pipeline.orchestration.orchestrator_state import _FAILURE_DECISIONS as _FAILURE_DECISIONS
from film_pipeline.orchestration.orchestrator_state import _ORCH_NS as _ORCH_NS
from film_pipeline.orchestration.orchestrator_state import _PENDING_REVISIONS as _PENDING_REVISIONS
from film_pipeline.orchestration.orchestrator_state import (
    _PROVIDER_HEALTH_SNAPSHOT as _PROVIDER_HEALTH_SNAPSHOT,
)
from film_pipeline.orchestration.orchestrator_state import _ROUTING_DECISIONS as _ROUTING_DECISIONS
from film_pipeline.orchestration.orchestrator_state import ORCH_CHANNELS as ORCH_CHANNELS
from film_pipeline.orchestration.orchestrator_state import OrchChannelSpec as OrchChannelSpec
from film_pipeline.orchestration.orchestrator_state import (
    _require_human_approval as _require_human_approval,
)
from film_pipeline.orchestration.orchestrator_state import (
    add_failure_decision as add_failure_decision,
)
from film_pipeline.orchestration.orchestrator_state import (
    add_revision_request as add_revision_request,
)
from film_pipeline.orchestration.orchestrator_state import (
    advance_review_round as advance_review_round,
)
from film_pipeline.orchestration.orchestrator_state import close_review_cycle as close_review_cycle
from film_pipeline.orchestration.orchestrator_state import (
    ensure_orchestrator_state as ensure_orchestrator_state,
)
from film_pipeline.orchestration.orchestrator_state import (
    get_active_review_cycle as get_active_review_cycle,
)
from film_pipeline.orchestration.orchestrator_state import get_approved_refs as get_approved_refs
from film_pipeline.orchestration.orchestrator_state import (
    get_blocked_providers as get_blocked_providers,
)
from film_pipeline.orchestration.orchestrator_state import (
    get_budget_snapshot as get_budget_snapshot,
)
from film_pipeline.orchestration.orchestrator_state import get_candidate_refs as get_candidate_refs
from film_pipeline.orchestration.orchestrator_state import (
    get_execution_brief as get_execution_brief,
)
from film_pipeline.orchestration.orchestrator_state import (
    get_failure_decisions as get_failure_decisions,
)
from film_pipeline.orchestration.orchestrator_state import (
    get_healthy_providers as get_healthy_providers,
)
from film_pipeline.orchestration.orchestrator_state import (
    get_latest_failure_decision as get_latest_failure_decision,
)
from film_pipeline.orchestration.orchestrator_state import (
    get_latest_routing_decision as get_latest_routing_decision,
)
from film_pipeline.orchestration.orchestrator_state import (
    get_pending_revisions as get_pending_revisions,
)
from film_pipeline.orchestration.orchestrator_state import (
    get_provider_health_snapshot as get_provider_health_snapshot,
)
from film_pipeline.orchestration.orchestrator_state import (
    get_routing_decisions as get_routing_decisions,
)
from film_pipeline.orchestration.orchestrator_state import (
    has_blocking_failure as has_blocking_failure,
)
from film_pipeline.orchestration.orchestrator_state import (
    has_execution_brief as has_execution_brief,
)
from film_pipeline.orchestration.orchestrator_state import (
    has_pending_revision as has_pending_revision,
)
from film_pipeline.orchestration.orchestrator_state import (
    increment_convergence_round as increment_convergence_round,
)
from film_pipeline.orchestration.orchestrator_state import init_convergence as init_convergence
from film_pipeline.orchestration.orchestrator_state import init_refs as init_refs
from film_pipeline.orchestration.orchestrator_state import is_budget_blocked as is_budget_blocked
from film_pipeline.orchestration.orchestrator_state import (
    is_provider_blocked as is_provider_blocked,
)
from film_pipeline.orchestration.orchestrator_state import is_stalled as is_stalled
from film_pipeline.orchestration.orchestrator_state import mark_stalled as mark_stalled
from film_pipeline.orchestration.orchestrator_state import (
    record_routing_decision as record_routing_decision,
)
from film_pipeline.orchestration.orchestrator_state import resolve_artifact as resolve_artifact
from film_pipeline.orchestration.orchestrator_state import resolve_revision as resolve_revision
from film_pipeline.orchestration.orchestrator_state import set_approved_ref as set_approved_ref
from film_pipeline.orchestration.orchestrator_state import set_candidate_ref as set_candidate_ref
from film_pipeline.orchestration.orchestrator_state import (
    set_execution_brief as set_execution_brief,
)
from film_pipeline.orchestration.orchestrator_state import start_review_cycle as start_review_cycle
from film_pipeline.orchestration.orchestrator_state import (
    update_budget_snapshot as update_budget_snapshot,
)
from film_pipeline.orchestration.orchestrator_state import (
    update_provider_health as update_provider_health,
)

__all__ = [
    "ORCH_CHANNELS",
    "OrchChannelSpec",
    "add_failure_decision",
    "add_revision_request",
    "advance_review_round",
    "close_review_cycle",
    "ensure_orchestrator_state",
    "get_active_review_cycle",
    "get_approved_refs",
    "get_blocked_providers",
    "get_budget_snapshot",
    "get_candidate_refs",
    "get_execution_brief",
    "get_failure_decisions",
    "get_healthy_providers",
    "get_latest_failure_decision",
    "get_latest_routing_decision",
    "get_pending_revisions",
    "get_provider_health_snapshot",
    "get_routing_decisions",
    "has_blocking_failure",
    "has_execution_brief",
    "has_pending_revision",
    "increment_convergence_round",
    "init_convergence",
    "init_refs",
    "is_budget_blocked",
    "is_provider_blocked",
    "is_stalled",
    "mark_stalled",
    "record_routing_decision",
    "resolve_artifact",
    "resolve_revision",
    "set_approved_ref",
    "set_candidate_ref",
    "set_execution_brief",
    "start_review_cycle",
    "update_budget_snapshot",
    "update_provider_health",
]
