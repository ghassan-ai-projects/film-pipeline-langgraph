"""Assembly manifest — how generated assets become a cut."""

from __future__ import annotations

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
    transition_type: str = Field(description="'cut' | 'dissolve' | 'fade' | 'wipe'.")
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
