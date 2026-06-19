"""Environment bible — locations, zones, viewpoints, lighting states."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class EnvironmentZone(SchemaBase):
    """A sub-area of a root environment."""

    zone_id: str
    description: str
    allowed_viewpoints: list[str] = Field(
        default_factory=list,
        description="Approved viewpoint ids from this zone.",
    )


class Viewpoint(SchemaBase):
    """One approved camera viewpoint for a zone."""

    viewpoint_id: str
    description: str
    lens: str = ""
    framing: str = ""


class LightingState(SchemaBase):
    """A named, repeatable lighting state for an environment."""

    state_id: str
    description: str
    shadow_direction: str = ""
    color_temperature: str = ""
    primary_source: str = ""


class EnvironmentFingerprint(SchemaBase):
    """Compressed invariant block inserted into every prompt for this env."""

    text: str = Field(
        description="Stable one-paragraph invariant block describing the environment.",
    )


class EnvironmentBible(SchemaBase):
    """Aggregate environment artifact.

    Once approved, prompts for every shot in this environment include the
    ``locked_prompt_block`` and ``fingerprint``.
    """

    environment_id: str
    project_id: str
    name: str
    locked_prompt_block: str = Field(
        description="Stable prompt block used as the root description.",
    )
    invariants: list[str] = Field(default_factory=list)
    zones: list[EnvironmentZone] = Field(default_factory=list)
    viewpoints: list[Viewpoint] = Field(default_factory=list)
    lighting_states: list[LightingState] = Field(default_factory=list)
    color_palette: list[str] = Field(default_factory=list)
    fingerprint: EnvironmentFingerprint
    reference_assets: list[str] = Field(default_factory=list)
    must_not_change: list[str] = Field(default_factory=list)
