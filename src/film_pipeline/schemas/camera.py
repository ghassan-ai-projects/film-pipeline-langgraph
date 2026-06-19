"""Camera language bible — cinematic grammar per profile."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class CameraProfile(SchemaBase):
    """One camera profile used to write shot prompts."""

    profile_id: str
    use_case: str = Field(description="What kind of shot this profile serves.")
    lens: str = Field(description="Lens signature, e.g. '35mm prime'.")
    framing: str = Field(description="Framing rules, e.g. 'rule of thirds left-weighted'.")
    movement: str = Field(description="Movement rules, e.g. 'static or slow push-in'.")
    depth_of_field: str = Field(description="DOF rules, e.g. 'shallow, f/2.0'.")
    composition_rules: list[str] = Field(default_factory=list)
    transition_rules: list[str] = Field(default_factory=list)
    emotional_meaning: str = Field(default="", description="What this profile communicates.")


class CameraLanguageBible(SchemaBase):
    """Aggregate camera grammar for the project."""

    project_id: str
    profiles: list[CameraProfile] = Field(default_factory=list)
    default_profile_id: str = Field(
        default="",
        description="Profile id used when a shot does not specify one.",
    )
