"""Reference index and strategy."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import ArtifactStatus, SchemaBase


class ReferenceIndexEntry(SchemaBase):
    """One approved reference asset."""

    reference_id: str
    asset_path: str = Field(description="Relative path under the project's references/ directory.")
    asset_type: str = Field(description="e.g. 'character_identity_sheet'.")
    subject_type: str = Field(
        description="'character' | 'environment' | 'prop' | 'style' | 'camera'."
    )
    subject_id: str = Field(description="character_id / environment_id / prop_id / profile_id.")
    approved_for: list[str] = Field(
        default_factory=lambda: ["prompt_anchor"],
        description="Use cases, e.g. 'prompt_anchor', 're_anchor', 'clip_validation'.",
    )
    quality_score: float = Field(ge=0, le=100)
    moderation_risk: str = Field(default="low", description="'low' | 'medium' | 'high'.")
    notes: str = ""
    status: ArtifactStatus = ArtifactStatus.CANDIDATE
    version: int = 1
    locked: bool = False


class ReferenceIndex(SchemaBase):
    """Aggregate reference index for a project."""

    project_id: str
    entries: list[ReferenceIndexEntry] = Field(default_factory=list)


class ReferenceStrategy(SchemaBase):
    """Planned reference generation plan."""

    project_id: str
    character_priorities: list[str] = Field(default_factory=list)
    environment_priorities: list[str] = Field(default_factory=list)
    prop_priorities: list[str] = Field(default_factory=list)
    provider_plan: list[str] = Field(default_factory=list)
    cost_estimate_usd: float = Field(default=0.0, ge=0)
    notes: str = ""
