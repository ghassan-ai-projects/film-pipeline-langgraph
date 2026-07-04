"""Typed graph state with reducers for append-only channels.

Implements the typed state contract defined in Phase 2 of the implementation
plan. Scalar fields use the default reducer (last write wins). Fields annotated
with ``Annotated[T, add]`` accumulate across nodes.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict

from film_pipeline.graph.services import GraphServices


def merge_unique(left: list[str] | None, right: list[str] | None) -> list[str]:
    """Append-only reducer for string refs that skips duplicates.

    Nodes occasionally return refs that are already recorded (e.g. when a
    full state dict is re-submitted to a thread that has checkpointed
    channels); duplicated refs are never meaningful, so they are dropped.
    """
    merged = list(left or [])
    seen = set(merged)
    for item in right or []:
        if item not in seen:
            merged.append(item)
            seen.add(item)
    return merged


def merge_generation_requests(
    left: list[dict[str, object]] | None,
    right: list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    """Upsert reducer for generation requests, keyed by request id.

    New requests append; a request whose id is already present replaces the
    stored entry (nodes enrich requests in place, e.g. resolving prompts),
    so re-emitting a request never duplicates it.
    """

    def _request_id(request: dict[str, object]) -> str:
        for key in ("generation_request_id", "generation_id", "shot_id"):
            value = str(request.get(key, "") or "")
            if value:
                return value
        return ""

    merged = list(left or [])
    index_by_id = {
        _request_id(request): position
        for position, request in enumerate(merged)
        if isinstance(request, dict) and _request_id(request)
    }
    for request in right or []:
        request_id = _request_id(request)
        if request_id and request_id in index_by_id:
            merged[index_by_id[request_id]] = request
            continue
        merged.append(request)
        if request_id:
            index_by_id[request_id] = len(merged) - 1
    return merged


def merge_issues(
    left: list[dict[str, object]] | None,
    right: list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    """Reducer for the ``issues`` channel: append, dedupe, and allow removal.

    A plain ``operator.add`` reducer makes issues immortal — once a blocking
    issue enters checkpointed graph state it can never be resolved, which
    wedges approval gates forever. This reducer:

    - appends new issues, skipping exact duplicates already present, and
    - honors a ``{"__remove_codes__": [...]}`` sentinel entry that removes
      previously recorded issues by their ``code`` (used when an external
      actor — e.g. the operator planning a generation batch — has resolved
      the underlying condition).
    """
    merged = list(left or [])
    removal_codes: set[str] = set()
    for item in right or []:
        if isinstance(item, dict) and "__remove_codes__" in item:
            codes = item.get("__remove_codes__")
            if isinstance(codes, list):
                removal_codes.update(str(code) for code in codes)
            continue
        if item not in merged:
            merged.append(item)
    if removal_codes:
        merged = [
            issue
            for issue in merged
            if not (isinstance(issue, dict) and str(issue.get("code", "")) in removal_codes)
        ]
    return merged


class StudioGraphState(TypedDict, total=False):
    """Canonical graph state for the film pipeline.

    All keys are optional (``total=False``) so nodes return only the keys they
    modify. LangGraph merges partial updates into the accumulated state.
    """

    # ── Runtime services ──────────────────────────────────────────────────
    # Injected by the runtime for the current graph invocation only. The
    # runtime strips this key before persisting project/checkpoint state.
    _services: GraphServices | None

    # ── Core identifiers ──────────────────────────────────────────────────
    project_id: str
    current_phase: str
    approved: bool
    completed: bool
    title: str
    slug: str
    server_mode: str
    # Operator-facing project settings; without schema entries the graph
    # silently drops them from state on every invoke.
    runtime_mode: str
    workflow_mode: str
    project_kind: str
    generation_policy: str

    # ── Human gate control ────────────────────────────────────────────────
    human_approval_phase: str
    human_approval_required: bool

    # ── Ref pointers (scalar — latest write wins) ────────────────────────
    idea: str
    film_type: str
    target_runtime_seconds: int
    # ── Story Scope Contract (derived at intake, enforced in prep) ────────
    pacing_style: str
    target_scene_count: int
    min_scene_count: int
    target_shot_count: int
    scope_contract_ref: str
    # ── User-intent constraints (extracted at intake, propagated to prompts) ─
    constraints_hints: dict[str, Any]
    constraints: dict[str, Any] | None
    constraints_ref: str
    profile_ref: str
    constitution_ref: str
    treatment_ref: str
    scene_list_ref: str
    script_ref: str
    story_bible_ref: str
    shot_matrix_ref: str
    visual_refs: str
    execution_brief_ref: str
    cost_estimate_ref: str
    consensus_report_ref: str
    assembly_manifest_ref: str
    prompt_registry_ref: str
    provider_plan_ref: str
    generation_schedule_ref: str
    delivery_manifest_ref: str

    # ── Patch / feedback refs ─────────────────────────────────────────────
    gen_planning_patch_ref: str
    generation_patch_ref: str
    qc_patch_ref: str
    repair_feedback_ref: str

    # ── Append-only channels ──────────────────────────────────────────────
    artifact_refs: Annotated[list[str], merge_unique]
    issues: Annotated[list[dict[str, object]], merge_issues]
    validation_report_refs: Annotated[list[str], merge_unique]
    generation_requests: Annotated[list[dict[str, object]], merge_generation_requests]

    # ── Snapshot channels ─────────────────────────────────────────────────
    budget_snapshot: dict[str, object]
    provider_health_snapshot: dict[str, object]
    resolved_config: dict[str, object]
    profile_stack: dict[str, str]
    resolved_config_sources: dict[str, object]
    config_conflicts: list[dict[str, object]]

    # ── Operator annotations (persisted with project state) ──────────────
    _operator_comments: list[dict[str, Any]]

    # ── Orchestrator-managed state ────────────────────────────────────────
    _orchestrator__candidate_refs: dict[str, str]
    _orchestrator__approved_refs: dict[str, str]
    _orchestrator__active_review_cycles: list[dict[str, Any]]
    _orchestrator__pending_revisions: list[dict[str, Any]]
    _orchestrator__routing_decisions: list[dict[str, Any]]
    _orchestrator__convergence: dict[str, dict[str, Any]]
    _orchestrator__failure_decisions: list[dict[str, Any]]
    _orchestrator__provider_health_snapshot: dict[str, dict[str, Any]]
    _orchestrator__budget_snapshot: dict[str, Any]
    _orchestrator__execution_brief: dict[str, Any]

    # ── Internal routing / repair flags ───────────────────────────────────
    _routing_decisions: list[dict[str, Any]]
    _stalled_phase: str
    _repair_feedback: str
    _revision_note: str
    _approval_blocked_by_issues: bool
    _context_load_failures: list[str]
    consistency_warnings: list[str]
    _validation_reports: list[dict[str, Any]]
    # Written concurrently by the QC fan-out workers — must be reducers.
    _qc_reports: Annotated[list[dict[str, Any]], add]
    _qc_raw_reports: Annotated[list[dict[str, Any]], add]
