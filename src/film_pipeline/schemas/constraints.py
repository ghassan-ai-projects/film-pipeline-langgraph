"""Project constraints schema.

Constraints are user-intent-derived requirements extracted from the submitted
idea (or supplied explicitly). They are distinct from operational profile
configuration and are propagated to agent prompts so every downstream phase
can respect them.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from film_pipeline.schemas.base import FilmType, SchemaBase
from film_pipeline.schemas.project import DeliveryMode


class ProjectConstraints(SchemaBase):
    """User-intent-derived project requirements.

    All fields are optional. When a field is unset it should be omitted from
    the rendered prompt block rather than shown as empty / unknown.
    """

    project_id: str
    target_runtime_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Target final runtime in seconds.",
    )
    target_scene_count: int | None = Field(
        default=None,
        ge=1,
        description="Number of scenes the story should contain.",
    )
    min_scene_count: int | None = Field(
        default=None,
        ge=1,
        description="Hard floor for scene count.",
    )
    target_shot_count: int | None = Field(
        default=None,
        ge=1,
        description="Number of shots the film should contain.",
    )
    max_shot_count: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of shots allowed.",
    )
    max_characters: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of named characters.",
    )
    film_type: FilmType | None = Field(
        default=None,
        description="Canonical film type/category.",
    )
    pacing_style: Literal["slow_cinema", "standard", "dynamic"] | None = Field(
        default=None,
        description="Canonical pacing style.",
    )
    tone: str | None = Field(
        default=None,
        description="Emotional tone, e.g. 'dark', 'hopeful', 'comedic'.",
    )
    genre: str | None = Field(
        default=None,
        description="Genre, e.g. 'sci-fi drama'.",
    )
    visual_style: str | None = Field(
        default=None,
        description="Visual style direction, e.g. 'noir', 'minimalist'.",
    )
    rating: str | None = Field(
        default=None,
        description="Target content rating, e.g. 'PG', 'R'.",
    )
    target_audience: str | None = Field(
        default=None,
        description="Target audience, e.g. 'children', 'adults'.",
    )
    themes: list[str] = Field(
        default_factory=list,
        description="Required themes or motifs.",
    )
    dialogue_language: str | None = Field(
        default=None,
        description="Language for dialogue, e.g. 'English'.",
    )
    budget_cap_usd: float | None = Field(
        default=None,
        ge=0,
        description="Hard spend cap in USD.",
    )
    provider_preferences: list[str] = Field(
        default_factory=list,
        description="Ordered provider preferences by id.",
    )
    delivery_modes: list[DeliveryMode] = Field(
        default_factory=list,
        description="Container formats to produce at delivery.",
    )
    forbidden_topics: list[str] = Field(
        default_factory=list,
        description="Topics, imagery, or tropes to avoid.",
    )
    required_elements: list[str] = Field(
        default_factory=list,
        description="Story elements that must appear.",
    )
    locations: list[str] = Field(
        default_factory=list,
        description="Required or allowed locations/environments.",
    )
    character_constraints: list[str] = Field(
        default_factory=list,
        description="Constraints on characters, e.g. 'protagonist is a child'.",
    )
    target_phase: str | None = Field(
        default=None,
        description="Furthest phase the pipeline should run.",
    )
    notes: str | None = Field(
        default=None,
        description="Free-form notes for the prompt block.",
    )


def render_constraints(constraints: ProjectConstraints | dict[str, Any] | None) -> str:
    """Render a compact, prompt-ready constraints block.

    Empty / unknown values are omitted so the block does not bloat prompts
    with placeholders.
    """
    if constraints is None:
        return ""

    if isinstance(constraints, ProjectConstraints):
        data = constraints.model_dump(mode="json", exclude_none=True)
    else:
        data = {k: v for k, v in constraints.items() if v is not None}

    # project_id is structural metadata, not a creative constraint.
    data.pop("project_id", None)
    data.pop("schema_version", None)

    lines: list[str] = []
    for key, value in data.items():
        if value is None or value == [] or value == "":
            continue
        label = " ".join(part.capitalize() for part in key.split("_"))
        rendered = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
        lines.append(f"- {label}: {rendered}")

    if not lines:
        return ""
    return "=== PROJECT CONSTRAINTS ===\n" + "\n".join(lines)
