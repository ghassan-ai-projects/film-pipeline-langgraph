"""StyleBible — visual style definition (palette, texture, grain, mood)."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class StyleBible(SchemaBase):
    """Locked visual style contract for a film.

    Defines the color palette, texture, grain, visual mood, and reference
    stills that every generated image and clip must respect.
    """

    project_id: str
    color_palette: list[str] = Field(
        default_factory=list,
        description="Hex color codes defining the film's color identity (e.g. '#1a1a2e').",
    )
    texture: str = Field(
        default="",
        description="Surface quality keywords, e.g. 'gritty, painterly, smooth'.",
    )
    grain: str = Field(
        default="",
        description="Film grain description, e.g. 'heavy 16mm grain', 'clean digital'.",
    )
    visual_mood: str = Field(
        default="",
        description="Overall visual mood keywords, e.g. 'melancholic, high-contrast'.",
    )
    reference_stills: list[str] = Field(
        default_factory=list,
        description="Paths or URLs to approved visual reference images.",
    )
    must_not_change: list[str] = Field(
        default_factory=list,
        description="Visual invariants agents must never alter.",
    )
