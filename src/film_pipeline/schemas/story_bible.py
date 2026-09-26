"""Story bible — narrative structure down to scene intent."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas.base import SchemaBase


class Logline(SchemaBase):
    """One-sentence film logline."""

    text: str = Field(min_length=10, description="A single-sentence logline.")
    hook: str = Field(default="", description="Optional second sentence highlighting hook.")


class Premise(SchemaBase):
    """Premise — the central dramatic question."""

    text: str
    dramatic_question: str = ""


class ActMap(SchemaBase):
    """Three-act structure summary."""

    act1_setup: str
    act2_confrontation: str
    act3_resolution: str


class SetupPayoffEntry(SchemaBase):
    """One setup→payoff pair across the script."""

    setup_scene_id: str
    payoff_scene_id: str
    description: str


class SceneIntent(SchemaBase):
    """Scene-level dramatic intent — what the scene must accomplish."""

    scene_id: str
    dramatic_function: str = Field(description="Why this scene exists.")
    emotional_shift: str = Field(description="What changes emotionally.")
    conflict: str = Field(description="The central tension of the scene.")
    outcome: str = Field(description="What is true after the scene ends.")


class SceneList(SchemaBase):
    """Ordered list of scenes with intents."""

    scenes: list[SceneIntent] = Field(default_factory=list)


class Treatment(SchemaBase):
    """Long-form prose treatment."""

    text: str = Field(description="Multi-paragraph treatment prose.")
    themes: list[str] = Field(default_factory=list)
    act_map: ActMap | None = None


class StoryBible(SchemaBase):
    """Aggregate narrative artifact."""

    project_id: str
    logline: Logline
    premise: Premise
    treatment: Treatment
    act_map: ActMap
    scene_list: SceneList
    setup_payoff_map: list[SetupPayoffEntry] = Field(default_factory=list)
    unresolved_threads: list[str] = Field(default_factory=list)
    theme_map: list[str] = Field(default_factory=list)
