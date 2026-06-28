"""Story Scope Contract — the forward, deterministic scope of a film.

Computed once (at intake) from the user-supplied runtime and the profile's
film_type/pacing, BEFORE any creative writing happens. Downstream phases must
*fill* this contract rather than be measured against the finished story after
the fact. This is what prevents "too few scenes" and "runtime too short": the
scope is decided up front and enforced, not reverse-engineered.
"""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class StoryScopeContract(SchemaBase):
    """Concrete, deterministic scope targets derived from runtime x film style."""

    project_id: str
    target_runtime_seconds: int = Field(ge=1, description="User-supplied authoritative runtime.")
    film_type: str = Field(default="narrative")
    pacing_style: str = Field(
        default="standard",
        description="Canonical pacing: 'slow_cinema', 'standard', or 'dynamic'.",
    )
    avg_shot_duration_seconds: float = Field(
        gt=0, description="Average seconds per shot for this pacing (single-clip-safe)."
    )
    target_scene_count: int = Field(
        ge=1, description="Scenes the development phase should produce."
    )
    min_scene_count: int = Field(ge=1, description="Hard floor — fewer than this is a failure.")
    target_shot_count: int = Field(ge=1, description="Shots the shot bible should produce.")
    shots_per_scene_low: int = Field(ge=1)
    shots_per_scene_high: int = Field(ge=1)
