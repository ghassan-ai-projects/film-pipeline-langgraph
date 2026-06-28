"""Typed graph state with reducers for append-only channels.

Implements the typed state contract defined in Phase 2 of the implementation
plan. Scalar fields use the default reducer (last write wins). Fields annotated
with ``Annotated[T, add]`` accumulate across nodes.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict


class StudioGraphState(TypedDict, total=False):
    """Canonical graph state for the film pipeline.

    All keys are optional (``total=False``) so nodes return only the keys they
    modify. LangGraph merges partial updates into the accumulated state.
    """

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

    # ── Append-only channels ──────────────────────────────────────────────
    artifact_refs: Annotated[list[str], add]
    issues: Annotated[list[dict[str, object]], add]
    validation_report_refs: Annotated[list[str], add]
    generation_requests: Annotated[list[dict[str, object]], add]

    # ── Snapshot channels ─────────────────────────────────────────────────
    budget_snapshot: dict[str, object]
    provider_health_snapshot: dict[str, object]
    resolved_config: dict[str, object]
