"""Character bible — the durable truth about one character."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class CharacterIdentity(SchemaBase):
    """Visual + narrative identity for a character."""

    character_id: str
    name: str
    role: str = Field(description="narrative role, e.g. 'protagonist', 'foil'.")
    age: str = ""
    physical_description: str = ""
    identity_block: str = Field(
        description="Locked descriptive block used in reference-image and video prompts.",
    )


class VoiceRules(SchemaBase):
    """Voice and dialogue rules."""

    cadence: str = ""
    vocabulary: list[str] = Field(default_factory=list)
    forbidden_phrasings: list[str] = Field(default_factory=list)
    signature_moves: list[str] = Field(default_factory=list)


class WardrobeRules(SchemaBase):
    """Wardrobe rules per act or state."""

    baseline: str = ""
    act_variants: dict[str, str] = Field(
        default_factory=dict,
        description="Map of act_id → wardrobe description.",
    )


class EmotionalArc(SchemaBase):
    """Emotional arc points."""

    start_state: str
    midpoint_state: str
    end_state: str
    key_turning_points: list[str] = Field(default_factory=list)


class RelationshipMap(SchemaBase):
    """One relationship between this character and another."""

    other_character_id: str
    relation: str
    evolution: str = Field(default="", description="How the relation changes across the film.")


class CharacterBible(SchemaBase):
    """Aggregate character artifact.

    Locked after approval. Changes require an invalidation report covering
    references, prompts, and clip validators.
    """

    character_id: str
    project_id: str
    visual_identity: CharacterIdentity
    voice_rules: VoiceRules
    wardrobe_rules: WardrobeRules
    emotional_arc: EmotionalArc
    relationship_map: list[RelationshipMap] = Field(default_factory=list)
    reference_assets: list[str] = Field(
        default_factory=list,
        description="Reference asset ids approved for this character.",
    )
    must_not_change: list[str] = Field(
        default_factory=list,
        description="Identity invariants the agents must never alter.",
    )
