"""Assembly manifest — how generated assets become a cut."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class ClipOrderEntry(SchemaBase):
    """One clip's placement on the timeline."""

    shot_id: str
    source_asset_ref: str = Field(description="Path to the selected take.")
    in_seconds: float = Field(ge=0)
    out_seconds: float = Field(ge=0)
    coverage_role: str = ""


class TransitionPlan(SchemaBase):
    """Transitions between clips."""

    from_shot_id: str
    to_shot_id: str
    # Canonical values from TRANSITION_TYPES in schemas/_base.py.
    transition_type: str = Field(
        description="'cut' | 'dissolve' | 'fade_in' | 'fade_out' | 'crossfade'."
    )
    duration_seconds: float = Field(default=0.0, ge=0)


class AudioPlan(SchemaBase):
    """Audio plan for the cut."""

    music_track_refs: list[str] = Field(default_factory=list)
    sfx_track_refs: list[str] = Field(default_factory=list)
    dialogue_track_refs: list[str] = Field(default_factory=list)
    cue_points: list[dict[str, float]] = Field(
        default_factory=list,
        description="List of {'shot_id': str, 'at_seconds': float}.",
    )


class ColorPlan(SchemaBase):
    """Color plan for the cut."""

    look: str = Field(default="", description="Overall grade description.")
    per_scene: dict[str, str] = Field(
        default_factory=dict,
        description="Map of scene_id → grading description.",
    )


class AssemblyManifest(SchemaBase):
    """Aggregate assembly contract."""

    cut_id: str
    project_id: str
    clip_order: list[ClipOrderEntry] = Field(default_factory=list)
    transitions: list[TransitionPlan] = Field(default_factory=list)
    audio_plan: AudioPlan = Field(default_factory=lambda: AudioPlan())
    color_plan: ColorPlan = Field(default_factory=lambda: ColorPlan())
    duration_total_seconds: float = Field(default=0.0, ge=0)
    missing_assets: list[str] = Field(default_factory=list)
    delivery_mode: str = Field(default="mp4")


class AssemblyPlanArtifact(SchemaBase):
    """Artifact persisted by the post-production assembly agent."""

    plan_id: str
    project_id: str
    clip_order: list[dict[str, Any]] = Field(default_factory=list)
    clips: list[str] = Field(default_factory=list)
    total_duration_seconds: float = Field(default=0.0, ge=0)
    clip_count: int = Field(default=0, ge=0)
    missing_assets: list[str] = Field(default_factory=list)
    transitions: list[dict[str, str]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
