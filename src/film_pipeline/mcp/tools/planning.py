"""Budget initialization and generation plan tools."""

from __future__ import annotations

from typing import cast

import film_pipeline.mcp.tools as tools_pkg

from .helpers import _error, _ok, _services


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
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
        from film_pipeline.schemas.artifact import ArtifactMetadata
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
        meta = ArtifactMetadata(
            artifact_id="budget_state",
            artifact_type=ArtifactType.BUDGET_STATE,
            project_id=project_id,
            phase=FilmPhase("gen_planning"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.initialize_budget",
            created_at=datetime.now(UTC),
        )
        ref = store.save(budget, meta)
        active["budget_state_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(budget_state_ref=ref, cap_usd=cap, remaining_usd=budget.remaining_usd)
    except Exception as exc:
        return _error(f"Budget initialization failed: {exc}")


async def generate_plan(args: dict[str, object]) -> dict[str, object]:
    """Generate a GenerationPlan from the shot matrix."""
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import FilmPhase

        matrix = store.load(project_id, FilmPhase("shot_bible"), "master_film_matrix", 1)
    except (FileNotFoundError, ValueError):
        return _error("MasterFilmMatrix not found. Run generate_shot_bible first.")

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

    try:
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType
        from film_pipeline.schemas.artifact import ArtifactMetadata

        meta = ArtifactMetadata(
            artifact_id="generation_plan",
            artifact_type=ArtifactType.GENERATION_PLAN,
            project_id=project_id,
            phase=FilmPhase("gen_planning"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_plan",
            created_at=datetime.now(UTC),
        )
        ref = store.save(plan, meta)
        active["generation_plan_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(
            generation_plan_ref=ref,
            shot_count=len(shots),
            total_estimated_cost=total_cost,
        )
    except Exception as exc:
        return _error(f"Plan generation failed: {exc}")
