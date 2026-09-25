"""Film constitution — the creative law of the film.

Locks theme, tone, visual language, camera philosophy, character truths,
and taboo mistakes before any generation.
"""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas.base import SchemaBase


class CharacterTruth(SchemaBase):
    """One durable truth about a character that all agents must respect."""

    character_id: str
    truth: str = Field(description="Sentence-form truth about the character.")
    must_not_change: bool = True


class FilmConstitution(SchemaBase):
    """Top-level creative contract for a film.

    Once approved, every artifact in the film must be consistent with
    the values here. Changes require an invalidation report.
    """

    project_id: str
    theme: str = Field(description="Single-sentence thematic statement.")
    tone: str = Field(description="Tonal keywords, e.g. 'melancholic, painterly'.")
    emotional_promise: str = Field(
        description="What the viewer should feel at the end of the film.",
    )
    visual_language: str = Field(description="Visual style keywords and references.")
    camera_philosophy: str = Field(
        description="Camera language rules, e.g. 'observational, breath-paced'.",
    )
    quality_bar: str = Field(description="What 'good' looks like for this film.")
    character_truths: list[CharacterTruth] = Field(default_factory=list)
    taboo_mistakes: list[str] = Field(
        default_factory=list,
        description="Forbidden creative moves the agents must avoid.",
    )
