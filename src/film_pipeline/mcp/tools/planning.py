"""Budget initialization and generation plan tools."""

from __future__ import annotations

from typing import Any, cast

import film_pipeline.mcp.tools as tools_pkg

from .helpers import _error, _latest_artifact_version, _ok, _services


async def initialize_budget(args: dict[str, object]) -> dict[str, object]:
    """Create the initial BudgetState for a project."""
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    cap = float(cast(float, args.get("cap_usd", 100.0)))
    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import ArtifactType
        from film_pipeline.schemas.budget import BudgetState

        budget = BudgetState(
            project_id=project_id,
            cap_usd=cap,
            spent_usd=0.0,
            per_phase_caps_usd={
                "visual_dev": cap * 0.3,
                "generation": cap * 0.6,
                "post": cap * 0.1,
            },
            max_auto_approved_cost_usd=1.0,
            human_approval_above_usd=5.0,
        )
        ref = _save_gen_planning_candidate(
            store,
            project_id,
            "budget_state",
            ArtifactType.BUDGET_STATE,
            "mcp.initialize_budget",
            budget,
        )
        _register_active_artifact_ref(rt, active, project_id, "budget_state_ref", ref)

        return _ok(budget_state_ref=ref, cap_usd=cap, remaining_usd=budget.remaining_usd)
    except Exception as exc:
        return _error(f"Budget initialization failed: {exc}")


def _save_gen_planning_candidate(
    store: Any,
    project_id: str,
    artifact_id: str,
    artifact_type: Any,
    created_by: str,
    content: Any,
) -> Any:
    """Persist an artifact as the next CANDIDATE version in gen_planning."""
    from datetime import UTC, datetime

    from film_pipeline.schemas._base import ArtifactStatus, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata

    next_version = (
        _latest_artifact_version(store, project_id, FilmPhase("gen_planning"), artifact_id) + 1
    )
    meta = ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        project_id=project_id,
        phase=FilmPhase("gen_planning"),
        version=next_version,
        status=ArtifactStatus.CANDIDATE,
        parents=[],
        created_by=created_by,
        created_at=datetime.now(UTC),
    )
    return store.save(content, meta)


def _register_active_artifact_ref(
    rt: Any, active: dict[str, Any], project_id: str, state_key: str, ref: object
) -> None:
    """Record an artifact reference on the active project and persist state."""
    active[state_key] = ref
    active.setdefault("artifact_refs", []).append(ref)
    rt.projects[project_id] = active
    rt._persist_project_state(project_id)


def _load_master_matrix(store: Any, project_id: str) -> Any:
    """Load the MasterFilmMatrix artifact, or None when it does not exist."""
    try:
        from film_pipeline.schemas._base import FilmPhase

        return store.load(project_id, FilmPhase("shot_bible"), "master_film_matrix", 1)
    except (FileNotFoundError, ValueError):
        return None


def _build_generation_plan(project_id: str, matrix: Any) -> tuple[Any, float]:
    """Derive the GenerationPlan and its estimated cost from the shot matrix."""
    from film_pipeline.schemas.generation import GenerationPlan, ShotPlan

    shots = [
        ShotPlan(
            shot_id=row.shot_id,
            priority=3,
            risk=str(getattr(row, "risk_level", "medium")),
            tier="fast",
            estimated_duration=float(getattr(row, "duration_seconds", 5)),
            generation_order=i,
        )
        for i, row in enumerate(matrix.rows)
    ]

    total_cost = sum(s.estimated_duration * 0.02 for s in shots)
    plan = GenerationPlan(
        project_id=project_id,
        shots=shots,
        total_estimated_cost=total_cost,
        provider_utilization={"gemini-imagen-4": len(shots)},
    )
    return plan, total_cost


def _persist_plan(rt: Any, active: dict[str, Any], project_id: str, plan: Any) -> Any:
    """Save the generation plan artifact and link it into the project state."""
    from film_pipeline.schemas._base import ArtifactType

    store = _services(rt).artifact_store
    ref = _save_gen_planning_candidate(
        store,
        project_id,
        "generation_plan",
        ArtifactType.GENERATION_PLAN,
        "mcp.generate_plan",
        plan,
    )
    _register_active_artifact_ref(rt, active, project_id, "generation_plan_ref", ref)
    return ref


async def generate_plan(args: dict[str, object]) -> dict[str, object]:
    """Generate a GenerationPlan from the shot matrix."""
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    matrix = _load_master_matrix(store, project_id)
    if matrix is None:
        return _error("MasterFilmMatrix not found. Run generate_shot_bible first.")

    plan, total_cost = _build_generation_plan(project_id, matrix)

    try:
        ref = _persist_plan(rt, active, project_id, plan)
        return _ok(
            generation_plan_ref=ref,
            shot_count=len(plan.shots),
            total_estimated_cost=total_cost,
        )
    except Exception as exc:
        return _error(f"Plan generation failed: {exc}")
