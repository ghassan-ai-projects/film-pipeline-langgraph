"""Typed graph state with reducers for append-only channels.

Implements the typed state contract defined in Phase 2 of the implementation
plan. Scalar fields use the default reducer (last write wins). Fields annotated
with ``Annotated[T, add]`` accumulate across nodes.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict

from film_pipeline.graph.services import GraphServices


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
    artifact_refs: Annotated[list[str], add]
    issues: Annotated[list[dict[str, object]], add]
    validation_report_refs: Annotated[list[str], add]
    generation_requests: Annotated[list[dict[str, object]], add]

    # ── Snapshot channels ─────────────────────────────────────────────────
    budget_snapshot: dict[str, object]
    provider_health_snapshot: dict[str, object]
    resolved_config: dict[str, object]

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
    _qc_reports: list[dict[str, Any]]
    _qc_raw_reports: list[dict[str, Any]]
