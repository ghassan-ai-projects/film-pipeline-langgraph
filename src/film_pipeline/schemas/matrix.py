"""Master film matrix — the production backbone.

Every generated clip maps to one matrix row. Every matrix row maps to a
scene intent, references, prompt, and validation records.
"""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas.base import SchemaBase


class ChainingConfig(SchemaBase):
    """How this shot chains to the previous one."""

    input_frame_ref: str | None = Field(
        default=None,
        description="Asset id of the frame to use as input (e.g. previous last frame).",
    )
    input_frame_type: str = Field(default="last_frame")
    return_last_frame: bool = True
    re_anchor: bool = False
    re_anchor_refs: list[str] = Field(default_factory=list)


class CoverageGroup(SchemaBase):
    """Several shots showing the same story moment from different angles."""

    coverage_group_id: str
    scene_id: str
    story_moment: str
    continuity_event: str
    coverage_type: str = Field(description="e.g. 'emotional_reveal', 'dialogue_exchange'.")
    required_angles: list[str] = Field(default_factory=list)
    editorial_intent: str = ""


class MasterFilmMatrixRow(SchemaBase):
    """One row in the master film matrix.

    This is the canonical contract between story, characters, environment,
    camera, prompt, reference, generation, validation, and post.
    """

    shot_id: str
    act_id: str
    sequence_id: str
    scene_id: str
    beat_id: str = ""
    story_function: str = Field(default="", description="e.g. 'inciting image'.")
    scene_intent_ref: str = Field(description="Artifact id of the scene intent.")
    duration_seconds: int = Field(ge=1, le=120)
    priority: str = Field(default="standard", description="'hero', 'standard', 'filler'.")
    risk_level: str = Field(default="medium", description="'low', 'medium', 'high'.")
    characters: list[str] = Field(default_factory=list)
    environment: str = ""
    environment_zone: str = ""
    environment_state: str = ""
    viewpoint: str = ""
    lighting_state: str = ""
    camera_profile: str = ""
    state_in_ref: str = ""
    state_out_ref: str = ""
    reference_strategy_ref: str = ""
    prompt_ref: str = ""
    provider_plan_ref: str = ""
    generation_order: int = Field(default=0, ge=0)
    chaining: ChainingConfig = Field(default_factory=ChainingConfig)
    coverage_group_id: str | None = None
    coverage_role: str | None = None
    validation_refs: list[str] = Field(default_factory=list)
    asset_refs: list[str] = Field(default_factory=list)
    post_refs: list[str] = Field(default_factory=list)
    status: str = "planned"
    auto_filled: bool = Field(
        default=False,
        description="True when this row was added by deterministic coverage back-fill.",
    )


class MasterFilmMatrix(SchemaBase):
    """Aggregate matrix artifact — the production bible's operational table."""

    project_id: str
    rows: list[MasterFilmMatrixRow] = Field(default_factory=list)
    coverage_groups: list[CoverageGroup] = Field(default_factory=list)
