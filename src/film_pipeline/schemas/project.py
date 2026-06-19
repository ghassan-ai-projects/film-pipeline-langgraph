"""Project identity, profile, and resolved config schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, cast

from pydantic import Field

from film_pipeline.schemas._base import FilmType, SchemaBase

DeliveryMode = Literal["mp4", "webm", "mov", "gif"]


class ProjectIdentity(SchemaBase):
    """Stable identifiers for a film project.

    ``project_id`` is immutable; ``slug`` is stable; ``title`` and ``aliases``
    may change over time.
    """

    project_id: str = Field(description="Immutable machine id, e.g. 'film_2026_0001'.")
    slug: str = Field(description="Human-readable stable slug, e.g. 'memory-in-color'.")
    title: str = Field(description="Display title, e.g. 'Memory In Color'.")
    aliases: list[str] = Field(default_factory=list, description="Alternate names for lookup.")


class ProjectProfile(SchemaBase):
    """Production container for a film.

    Holds the user-facing knobs: runtime, aspect, delivery modes, budget,
    and provider preferences.
    """

    identity: ProjectIdentity
    film_type: FilmType = FilmType.NARRATIVE
    target_runtime_seconds: int = Field(ge=1, description="Target final runtime in seconds.")
    aspect_ratio: str = Field(default="16:9", description="Aspect ratio, e.g. '16:9', '9:16'.")
    delivery_modes: list[DeliveryMode] = Field(
        default_factory=lambda: cast(list[DeliveryMode], ["mp4"]),
        description="Container formats to produce at delivery.",
    )
    budget_cap_usd: float | None = Field(default=None, ge=0, description="Hard spend cap.")
    provider_preferences: list[str] = Field(
        default_factory=list,
        description="Ordered provider preferences by id.",
    )
    human_owner: str | None = Field(default=None, description="Human owner identifier.")


class ProjectConfig(SchemaBase):
    """Resolved, fully-inferred project configuration.

    After intake, this is the locked contract: everything below is a
    downstream input that may not contradict the values here without an
    explicit revision and invalidation report.
    """

    profile: ProjectProfile
    resolved_provider: str = Field(description="Provider id selected after intake.")
    resolved_quality: str = Field(description="Quality profile applied.")
    resolved_review_strategy: str = Field(description="Review strategy applied.")
    generation_mode_default: str = Field(
        default="test",
        description="Default generation mode (test/preview/production).",
    )
    created_at: datetime
    updated_at: datetime
    notes: str = Field(default="", description="Free-form operator notes.")
