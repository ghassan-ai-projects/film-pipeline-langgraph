"""Reference index and strategy."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import ArtifactStatus, SchemaBase
from film_pipeline.schemas.validation import ValidationIssue


class ReferenceValidationSummary(SchemaBase):
    """Validation state for a generated reference asset."""

    status: str = Field(
        default="pending",
        description=(
            "'pending' | 'approved' | 'approved_with_notes' | "
            "'needs_delta_fix' | 'needs_regeneration' | 'human_review_required' | 'rejected'."
        ),
    )
    score: float = Field(default=0.0, ge=0, le=100)
    reports: list[str] = Field(default_factory=list)


class ReferenceAIUsability(SchemaBase):
    """AI-usability score and risk tags for a reference asset."""

    score: float = Field(default=0.0, ge=0, le=100)
    risks: list[str] = Field(default_factory=list)
    notes: str = ""


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
    provider: str = ""
    tier: str = Field(
        default="fast",
        description="Provider quality tier: 'fast' | 'standard' | 'ultra'.",
    )
    frame_role: str = Field(
        default="",
        description="e.g. 'front-face', '3-4-left', 'wide-establishing', 'detail-texture'.",
    )
    expression: str = Field(
        default="",
        description="e.g. 'neutral', 'frustrated', 'tired' — for character expression entries.",
    )
    lighting: str = Field(
        default="",
        description="e.g. 'cool night', 'golden afternoon' — for environment lighting variants.",
    )
    prompt_text: str = ""
    prompt_refs: list[str] = Field(default_factory=list)
    source_frames: list[str] = Field(default_factory=list)
    moderation_risk: str = Field(default="low", description="'low' | 'medium' | 'high'.")
    notes: str = ""
    generation_status: str = Field(
        default="planned",
        description="'planned' | 'generated' | 'failed' | 'validated'.",
    )
    original_mime_type: str = ""
    normalized_mime_type: str = "image/png"
    status: ArtifactStatus = ArtifactStatus.CANDIDATE
    version: int = 1
    locked: bool = False
    validation: ReferenceValidationSummary = Field(default_factory=ReferenceValidationSummary)
    ai_usability: ReferenceAIUsability = Field(default_factory=ReferenceAIUsability)
    issues: list[ValidationIssue] = Field(default_factory=list)


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
