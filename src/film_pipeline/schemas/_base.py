"""Shared base classes and enums for all schemas.

Every concrete schema inherits :class:`SchemaBase` and declares ``schema_version``.
Re-exports the canonical enums used across artifacts, approvals, validation,
generation, KB, and provider state.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from film_pipeline.filmspec import (
    AgentFamily as AgentFamily,
)
from film_pipeline.filmspec import (
    AgentRole as AgentRole,
)
from film_pipeline.filmspec import (
    ArtifactType as ArtifactType,
)
from film_pipeline.filmspec import (
    FilmPhase as FilmPhase,
)
from film_pipeline.filmspec import (
    GenerationStatus as GenerationStatus,
)
from film_pipeline.filmspec import (
    IssueSeverity as IssueSeverity,
)
from film_pipeline.filmspec import (
    ValidationStatus as ValidationStatus,
)

# --- Enums used across the studio -----------------------------------------


class ArtifactStatus(StrEnum):
    """Lifecycle status of a versioned artifact."""

    CANDIDATE = "candidate"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ValidationScope(StrEnum):
    """Validation scope axis from the validation matrix."""

    ARTIFACT = "artifact"
    CLIP = "clip"
    SCENE = "scene"
    SEQUENCE = "sequence"
    ACT = "act"
    FULL_MOVIE = "full_movie"
    DELIVERY = "delivery"


class ValidationModality(StrEnum):
    """Validation modality axis from the validation matrix."""

    TEXT = "text"
    IMAGE = "image"
    CAMERA = "camera"
    CONTINUITY = "continuity"
    FLOW = "flow"
    VIDEO = "video"
    ASSEMBLY = "assembly"


class ProviderStatus(StrEnum):
    """Provider health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED_QUOTA = "blocked_quota"
    BLOCKED_CREDIT = "blocked_credit"
    BLOCKED_AUTH = "blocked_auth"
    BLOCKED_OUTAGE = "blocked_outage"
    DISABLED_BY_USER = "disabled_by_user"


class GenerationMode(StrEnum):
    """Generation modes for cost control."""

    MOCK = "mock"
    TEST = "test"
    PREVIEW = "preview"
    PRODUCTION = "production"


class FailureClass(StrEnum):
    """Failure classification by the failure-handling agent."""

    RECOVERABLE_EXECUTION = "recoverable_execution"
    CREATIVE_VALIDATION = "creative_validation"
    PROVIDER_ACCOUNT = "provider_account"
    BUDGET = "budget"
    CONTINUITY = "continuity"


class ReviewStrategy(StrEnum):
    """How many reviewers and how they are chosen."""

    SINGLE = "single"
    PARALLEL_INDEPENDENT = "parallel_independent"
    SPECIALIST_PANEL = "specialist_panel"
    DEBATE_SYNTHESIS = "debate_synthesis"
    HUMAN_ARBITRATED = "human_arbitrated"


class FilmType(StrEnum):
    """Film type categories used in profiles."""

    NARRATIVE = "narrative"
    VISUAL_POETRY = "visual_poetry"
    EXPERIMENTAL = "experimental"
    SHORT_DRAMA = "short_drama"
    COMMERCIAL = "commercial"


class QualityLevel(StrEnum):
    """Quality bar applied to validation and review strictness."""

    DRAFT = "draft"
    INTERNAL_REVIEW = "internal_review"
    STUDIO = "studio"
    FESTIVAL = "festival"
    SOCIAL = "social"


class KbAuthority(StrEnum):
    """Authority level of a KB item."""

    CANONICAL = "canonical"
    ACTIVE_PLAYBOOK = "active_playbook"
    CASE_STUDY = "case_study"
    RAW_ARCHIVE = "raw_archive"


# --- Shared vocabularies ----------------------------------------------------


# Closed vocabulary of transitions the studio plans, validates, and executes.
TRANSITION_TYPES: tuple[str, ...] = ("cut", "dissolve", "fade_in", "fade_out", "crossfade")

# Legacy transition spellings resolved onto TRANSITION_TYPES before validation.
# "fade" survives in assembly prompt prose ("fade for chapter breaks"); a bare
# fade is a fade to black, so it maps onto the executable fade_out. "wipe" has
# no honest canonical equivalent and stays unrecognized.
LEGACY_TRANSITION_ALIASES: dict[str, str] = {"fade": "fade_out"}


# --- Base models -----------------------------------------------------------


class SchemaBase(BaseModel):
    """Common base for every schema.

    All schemas inherit this and declare ``schema_version`` so the artifact
    layer can detect and migrate older versions safely.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)
    schema_version: str = Field(default="v1", description="Schema version identifier.")


class MutableSchemaBase(BaseModel):
    """Schema base for objects that mutate during a run (e.g. budgets)."""

    model_config = ConfigDict(frozen=False, extra="ignore", populate_by_name=True)
    schema_version: str = Field(default="v1", description="Schema version identifier.")
