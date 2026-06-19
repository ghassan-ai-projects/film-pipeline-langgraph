"""Script schema — the full screenplay artifact."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class DialogueLine(SchemaBase):
    """One line of dialogue in a scene."""

    character_id: str
    line: str = Field(description="The spoken dialogue text.")
    direction: str = Field(default="", description="Parenthetical or action direction.")


class ScriptScene(SchemaBase):
    """A single scene in the script."""

    scene_id: str
    scene_heading: str = Field(description="INT./EXT. Location — Time of Day")
    action_lines: list[str] = Field(default_factory=list)
    dialogue: list[DialogueLine] = Field(default_factory=list)
    intent_ref: str = Field(default="", description="Reference to parent SceneIntent.")


class Script(SchemaBase):
    """The full screenplay artifact produced by the screenwriter agent."""

    project_id: str
    title: str = ""
    scenes: list[ScriptScene] = Field(default_factory=list)
    total_scenes: int = 0
    total_dialogue_lines: int = 0
