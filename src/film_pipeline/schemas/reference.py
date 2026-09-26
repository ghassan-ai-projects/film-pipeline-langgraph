"""Reference index and strategy."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas.base import ArtifactStatus, SchemaBase
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
    retry_count: int = Field(default=0, ge=0, description="Number of generation attempts.")
    best_score: float = Field(default=0.0, ge=0, description="Best Gemini score across retries.")
    best_attempt: int = Field(default=0, ge=0, description="Attempt number with best score.")
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


class ReferenceFrame(SchemaBase):
    """Per-frame metadata sidecar written alongside each generated PNG.

    Captures the full provenance of a single frame: provider, model, seed,
    prompt, validation scores, and retry history.
    """

    frame_path: str = Field(description="Relative path from project root to the PNG.")
    reference_id: str
    subject_type: str
    subject_id: str
    provider_id: str = ""
    model_id: str = ""
    tier: str = "fast"
    seed: int | None = None
    prompt_text: str = ""
    frame_role: str = ""
    expression: str | None = None
    lighting: str | None = None
    aspect_ratio: str = "1:1"
    generation_status: str = "generated"
    quality_score: float = 0.0
    retry_count: int = 0
    best_score: float = 0.0
    heuristic_checks_passed: bool = False
    mime_type: str = "image/png"
    created_at: str = ""


class TileEntry(SchemaBase):
    """One tile in a composite sheet — which frame went where."""

    tile_name: str
    frame_reference_id: str
    frame_path: str
    position: tuple[int, int, int, int]  # x, y, w, h in sheet coordinates


class CompositeSheetManifest(SchemaBase):
    """Layout manifest written alongside each composite sheet.

    Records which frame went into each tile position so that delta
    regeneration and validation consumers can reconstruct provenance.
    """

    sheet_id: str
    sheet_type: str
    sheet_path: str
    dimensions: tuple[int, int]
    template_version: str = "1.0"
    tiles: list[TileEntry] = Field(default_factory=list)
    placeholder_tiles: list[str] = Field(default_factory=list)
    created_at: str = ""
    validation_status: str = "pending"
    validation_score: float = 0.0
