"""Budget initialization and generation plan tools."""

from __future__ import annotations

from typing import Any, cast

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.config.profile_resolver import provider_specs_from_raw

from .helpers import (
    _error,
    _latest_artifact_version,
    _ok,
    _register_active_artifact_ref,
    _services,
    require_project_state,
)

#: Fallback cap when neither the caller nor the project supplies one. Kept
#: explicit and named so it is visible as the last-resort default it is.
_DEFAULT_CAP_USD: float = 100.0


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


def _known_provider(runtime: Any, provider_id: str) -> bool:
    """True when ``provider_id`` names a provider this runtime can reach.

    This guard was a membership test against the provider *pricing* catalogue,
    which made a cost table the authority for provider identity. Cost is gone; the
    authority that remains is the runtime's own provider set — the adapters it has
    registered plus the ids its server mode supports. That is the same kind of
    check the pricing table was standing in for, without the cost data.

    Registered adapters cover the configured and seeded providers; the mode's
    default ids cover the case where seeding has not run yet, which is how the
    planning tests build a runtime. A provider named only in project config is NOT
    accepted: being requested is not the same as existing, which is the behaviour
    the pricing check had and the behaviour its test still asserts.
    """
    if not provider_id:
        return False
    if runtime.get_provider(provider_id) is not None:
        return True
    if provider_id in runtime.list_providers():
        return True
    from film_pipeline.providers import supported_provider_ids

    return provider_id in supported_provider_ids(runtime.server_mode)


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
) -> Any:
    """Derive the GenerationPlan from the shot matrix.

    Cost estimation was removed as a feature. This function used a lookup in the
    provider *pricing* table as its unknown-provider guard, which meant a cost
    table was the authority for whether a provider id was valid. The guard now
    checks the resolved config's own video-provider route, which is where the id
    came from and which survives the removal.
    """
    from film_pipeline.schemas.generation import GenerationPlan, ShotPlan

    provider_id, model_id = _fallback_video_route(runtime, state)
    if not _known_provider(runtime, provider_id):
        raise ValueError(f"Cannot create generation plan for unknown provider '{provider_id}'.")
    if not model_id:
        raise ValueError(f"Cannot create generation plan for '{provider_id}' without a model.")
    shots = [
        ShotPlan(
            shot_id=row.shot_id,
            priority=3,
            risk=str(getattr(row, "risk_level", "medium")),
            provider_id=provider_id,
            model_id=model_id,
            estimated_duration=float(getattr(row, "duration_seconds", 5)),
            generation_order=i,
        )
        for i, row in enumerate(matrix.rows)
    ]

    return GenerationPlan(
        project_id=project_id,
        shots=shots,
        provider_utilization={provider_id: len(shots)},
    )


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
    active = require_project_state(args)
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    try:
        matrix = _load_master_matrix(store, project_id)
    except ValueError as exc:
        return _error(str(exc))
    if matrix is None:
        return _error("MasterFilmMatrix not found. Run generate_shot_bible first.")

    try:
        plan = _build_generation_plan(
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
        )
    except Exception as exc:
        return _error(f"Plan generation failed: {exc}")
