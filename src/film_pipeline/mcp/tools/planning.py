"""Budget initialization and generation plan tools."""

from __future__ import annotations

import math
from typing import Any, cast

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.budget import cap_for
from film_pipeline.config.profile_resolver import provider_specs_from_raw

from .helpers import (
    _error,
    _latest_artifact_version,
    _no_active_project,
    _ok,
    _services,
)

#: Fallback cap when neither the caller nor the project supplies one. Kept
#: explicit and named so it is visible as the last-resort default it is.
_DEFAULT_CAP_USD: float = 100.0


async def initialize_budget(args: dict[str, object]) -> dict[str, object]:
    """Create the initial BudgetState for a project."""
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _no_active_project()
    project_id = str(active["project_id"])
    raw_cap = args.get("cap_usd")
    if raw_cap is None:
        # Read the project's configured cap rather than carrying a rival literal.
        # `cap_for` returns unlimited when nothing is configured; that is a real
        # gap (profiles declare `project_cap_usd`, but no creation path writes it
        # onto the project), so this preserves the previous *effective* behavior
        # of "no cap supplied means no limit" instead of silently inventing 100.
        cap = cap_for(active)
        if not math.isfinite(cap):
            cap = _DEFAULT_CAP_USD
    else:
        try:
            cap = float(cast(float, raw_cap))
        except (TypeError, ValueError):
            return _error("cap_usd must be a number.")
    if not math.isfinite(cap) or cap < 0:
        return _error("cap_usd must be a finite, non-negative number.")
    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas.base import ArtifactType
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
) -> str:
    """Persist an artifact as the next CANDIDATE version in gen_planning."""
    from datetime import UTC, datetime

    from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef
    from film_pipeline.schemas.base import ArtifactStatus, FilmPhase

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
    ref: ArtifactRef = store.save(content, meta)
    return ref.to_string()


def _register_active_artifact_ref(
    rt: Any, active: dict[str, Any], project_id: str, state_key: str, ref: object
) -> None:
    """Record an artifact reference on the active project and persist state."""
    active[state_key] = ref
    active.setdefault("artifact_refs", []).append(ref)
    rt.projects[project_id] = active
    rt._persist_project_state(project_id)


def _load_master_matrix(store: Any, project_id: str) -> Any:
    """Load and validate the latest MasterFilmMatrix artifact, if it exists."""
    try:
        from film_pipeline.schemas.base import FilmPhase
        from film_pipeline.schemas.matrix import MasterFilmMatrix

        version = max(1, store.latest_version(project_id, "shot_bible", "master_film_matrix"))
        raw = store.load(project_id, FilmPhase("shot_bible"), "master_film_matrix", version)
        if isinstance(raw, MasterFilmMatrix):
            return raw
        return MasterFilmMatrix.model_validate(raw)
    except FileNotFoundError:
        return None
    except ValueError as exc:
        raise ValueError(f"Persisted MasterFilmMatrix is invalid: {exc}") from exc


def _fallback_video_route(rt: Any, state: dict[str, Any]) -> tuple[str, str]:
    """Resolve the fallback plan's video provider and model from live state."""
    resolved_config = state.get("resolved_config", {})
    providers = resolved_config.get("providers", {}) if isinstance(resolved_config, dict) else {}
    if isinstance(providers, dict):
        configured = provider_specs_from_raw(providers)
        default_id = str(providers.get("default", "")).strip()
        video_specs = [spec for spec in configured if spec.get("provider_type") == "video"]
        selected = next(
            (spec for spec in video_specs if str(spec.get("provider_id")) == default_id),
            video_specs[0] if video_specs else None,
        )
        if selected is not None:
            provider_id = str(selected["provider_id"])
            models = selected.get("models", [])
            if isinstance(models, list) and models:
                return provider_id, str(models[0])
            runtime_provider, runtime_model = rt.default_video_provider()
            if provider_id == runtime_provider:
                return provider_id, runtime_model
            adapter = rt.get_provider(provider_id)
            entry_models = getattr(getattr(adapter, "entry", None), "models", [])
            if isinstance(entry_models, list) and entry_models:
                return provider_id, str(entry_models[0])
            return provider_id, ""
    return cast(tuple[str, str], rt.default_video_provider())


def _build_generation_plan(
    project_id: str,
    matrix: Any,
    *,
    runtime: Any,
    state: dict[str, Any],
) -> tuple[Any, float]:
    """Derive the GenerationPlan and its estimated cost from the shot matrix."""
    from film_pipeline.providers.pricing import (
        PROVIDER_PRICING,
        estimate_cost_for_duration,
        tier_for,
    )
    from film_pipeline.schemas.generation import GenerationPlan, ShotPlan

    provider_id, model_id = _fallback_video_route(runtime, state)
    if provider_id not in PROVIDER_PRICING:
        raise ValueError(f"Cannot estimate generation cost for unknown provider '{provider_id}'.")
    if not model_id:
        raise ValueError(f"Cannot create generation plan for '{provider_id}' without a model.")
    shots = [
        ShotPlan(
            shot_id=row.shot_id,
            priority=3,
            risk=str(getattr(row, "risk_level", "medium")),
            tier=tier_for(provider_id, model_id),
            provider_id=provider_id,
            model_id=model_id,
            estimated_cost=round(
                estimate_cost_for_duration(
                    provider_id,
                    model_id,
                    float(getattr(row, "duration_seconds", 5)),
                ),
                4,
            ),
            estimated_duration=float(getattr(row, "duration_seconds", 5)),
            generation_order=i,
        )
        for i, row in enumerate(matrix.rows)
    ]

    total_cost = round(sum(s.estimated_cost for s in shots), 2)
    plan = GenerationPlan(
        project_id=project_id,
        shots=shots,
        total_estimated_cost=total_cost,
        provider_utilization={provider_id: len(shots)},
    )
    return plan, total_cost


def _persist_plan(rt: Any, active: dict[str, Any], project_id: str, plan: Any) -> Any:
    """Save the generation plan artifact and link it into the project state."""
    from film_pipeline.schemas.base import ArtifactType

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
        return _no_active_project()
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    try:
        matrix = _load_master_matrix(store, project_id)
    except ValueError as exc:
        return _error(str(exc))
    if matrix is None:
        return _error("MasterFilmMatrix not found. Run generate_shot_bible first.")

    try:
        plan, total_cost = _build_generation_plan(
            project_id,
            matrix,
            runtime=rt,
            state=active,
        )
    except ValueError as exc:
        return _error(str(exc))

    try:
        ref = _persist_plan(rt, active, project_id, plan)
        return _ok(
            generation_plan_ref=ref,
            shot_count=len(plan.shots),
            total_estimated_cost=total_cost,
        )
    except Exception as exc:
        return _error(f"Plan generation failed: {exc}")
