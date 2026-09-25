"""Deterministic derivation of the Story Scope Contract.

Single source of truth for the scene/shot density model. Replaces the magic
numbers that were duplicated across prompts and validators (the per-pacing
shot-duration dicts, the open scene-count ranges). Pure functions only — no
LLM, no I/O — so the contract is reproducible for a given (runtime, film_type,
pacing).
"""

from __future__ import annotations

import math
from typing import Any

from film_pipeline.schemas.scope_contract import StoryScopeContract

# Canonical pacing styles used everywhere downstream.
SLOW_CINEMA = "slow_cinema"
STANDARD = "standard"
DYNAMIC = "dynamic"

# Density table: canonical pacing -> (avg_shot_seconds, seconds_per_scene).
# avg_shot_seconds is capped at ~9s so a shot maps to a single provider clip
# (Seedance/Veo single-clip limits ~8-10s); longer "shots" become multi-clip
# later (see WS-H). seconds_per_scene sets scene density.
_DENSITY: dict[str, tuple[float, float]] = {
    SLOW_CINEMA: (9.0, 30.0),
    STANDARD: (6.5, 22.0),
    DYNAMIC: (4.0, 16.0),
}

# Profile pacing vocabulary (and film_type) -> canonical pacing style.
_PACING_ALIASES: dict[str, str] = {
    # canonical
    "slow_cinema": SLOW_CINEMA,
    "standard": STANDARD,
    "dynamic": DYNAMIC,
    # profile pacing vocab
    "meditative": SLOW_CINEMA,
    "contemplative": SLOW_CINEMA,
    "character_driven": STANDARD,
    "narrative": STANDARD,
    "irregular": STANDARD,
    "action": DYNAMIC,
    "fast": DYNAMIC,
}

# Fallback canonical pacing per film_type when no explicit pacing is given.
_FILM_TYPE_DEFAULT_PACING: dict[str, str] = {
    "visual_poetry": SLOW_CINEMA,
    "narrative": STANDARD,
    "short_drama": STANDARD,
    "experimental": STANDARD,
    "commercial": DYNAMIC,
}

# Floor as a fraction of the target scene count.
_MIN_SCENE_FRACTION = 0.8


def normalize_pacing(pacing: str | None, film_type: str | None) -> str:
    """Map a profile pacing value (or film_type default) to a canonical style."""
    if pacing:
        canon = _PACING_ALIASES.get(str(pacing).strip().lower())
        if canon:
            return canon
    return _FILM_TYPE_DEFAULT_PACING.get(str(film_type or "").strip().lower(), STANDARD)


def derive_scope_contract(
    project_id: str,
    target_runtime_seconds: int,
    film_type: str,
    pacing: str | None,
    user_scene_count: int | None = None,
) -> StoryScopeContract:
    """Derive concrete scene/shot targets from runtime x film style.

    When ``user_scene_count`` is supplied (e.g. parsed from the user's idea or
    set explicitly via ``submit_idea``), it overrides the runtime-derived scene
    count so the pipeline honors an explicit creative request.

    Deterministic: the same inputs always yield the same contract.
    """
    runtime = max(int(target_runtime_seconds), 1)
    canonical = normalize_pacing(pacing, film_type)
    avg_shot, sec_per_scene = _DENSITY.get(canonical, _DENSITY[STANDARD])

    target_shot_count = max(1, round(runtime / avg_shot))
    if user_scene_count is not None and user_scene_count > 0:
        target_scene_count = user_scene_count
        # When the user fixed the scene count, hold the line at that count.
        min_scene_count = target_scene_count
    else:
        target_scene_count = max(1, round(runtime / sec_per_scene))
        min_scene_count = max(1, math.ceil(target_scene_count * _MIN_SCENE_FRACTION))

    # Never plan fewer shots than scenes (each scene needs >= 1 shot).
    target_shot_count = max(target_shot_count, target_scene_count)

    shots_per_scene = target_shot_count / target_scene_count
    shots_per_scene_low = max(1, math.floor(shots_per_scene))
    shots_per_scene_high = max(shots_per_scene_low, math.ceil(shots_per_scene) + 1)

    return StoryScopeContract(
        project_id=project_id,
        target_runtime_seconds=runtime,
        film_type=str(film_type or "narrative"),
        pacing_style=canonical,
        avg_shot_duration_seconds=avg_shot,
        target_scene_count=target_scene_count,
        min_scene_count=min_scene_count,
        target_shot_count=target_shot_count,
        shots_per_scene_low=shots_per_scene_low,
        shots_per_scene_high=shots_per_scene_high,
    )


def avg_shot_duration_for(pacing_style: str | None) -> float:
    """Return the canonical average shot duration for a pacing style.

    Single source of truth shared by the scope contract and the orchestrator
    validators, so planned and validated runtimes use the same model.
    """
    canon = _PACING_ALIASES.get(str(pacing_style or "").strip().lower(), STANDARD)
    return _DENSITY.get(canon, _DENSITY[STANDARD])[0]


def pacing_from_config(resolved_config: dict[str, Any] | None) -> str | None:
    """Extract the profile pacing value from resolved config, if present."""
    if not isinstance(resolved_config, dict):
        return None
    pacing = resolved_config.get("pacing")
    return str(pacing) if pacing else None
