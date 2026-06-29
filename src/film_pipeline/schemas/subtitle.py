"""Subtitle artifact schema."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class SubtitleCue(SchemaBase):
    """One subtitle cue."""

    index: int = Field(ge=0)
    start: str  # HH:MM:SS,mmm
    end: str
    text: str


class SubtitleArtifact(SchemaBase):
    """Subtitle artifact persisted by the subtitle agent."""

    plan_id: str
    project_id: str
    language: str = "en"
    cue_count: int = Field(default=0, ge=0)
    srt_content: str = ""
    cues: list[SubtitleCue] = Field(default_factory=list)
