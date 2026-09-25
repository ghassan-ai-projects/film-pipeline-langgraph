"""Shared base classes and enums for all schemas.

Every concrete schema inherits :class:`SchemaBase` and declares ``schema_version``.
Re-exports the canonical enums used across artifacts, approvals, validation,
generation, KB, and provider state.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# --- Enums used across the studio -----------------------------------------


class ArtifactStatus(StrEnum):
    """Lifecycle status of a versioned artifact."""

    CANDIDATE = "candidate"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ArtifactType(StrEnum):
    """Catalog of artifact types produced by the studio."""

    PROJECT_CONFIG = "project_config"
    PROJECT_CONSTRAINTS = "project_constraints"
    INTAKE_ANALYSIS = "intake_analysis"
    FILM_CONSTITUTION = "film_constitution"
    LOGLINE = "logline"
    PREMISE = "premise"
    TREATMENT = "treatment"
    ACT_MAP = "act_map"
    SCENE_LIST = "scene_list"
    SCENE_INTENT = "scene_intent"
    SCRIPT = "script"
    DIALOGUE_PASS = "dialogue_pass"
    CHARACTER_BIBLE = "character_bible"
    ENVIRONMENT_BIBLE = "environment_bible"
    CAMERA_LANGUAGE_BIBLE = "camera_language_bible"
    STYLE_BIBLE = "style_bible"
    REFERENCE_SHEET = "reference_sheet"
    REFERENCE_INDEX = "reference_index"
    SHOT_BIBLE = "shot_bible"
    MATRIX_ROW = "matrix_row"
    MASTER_FILM_MATRIX = "master_film_matrix"
    COVERAGE_GROUP = "coverage_group"
    CONTINUITY_LEDGER = "continuity_ledger"
    PROMPT_PACKAGE = "prompt_package"
    PROMPT_REGISTRY = "prompt_registry"
    GENERATION_PLAN = "generation_plan"
    GENERATION_LEDGER = "generation_ledger"
    BUDGET_STATE = "budget_state"
    CLIP = "clip"
    LAST_FRAME = "last_frame"
    MID_FRAME = "mid_frame"
    VALIDATION_REPORT = "validation_report"
    REVIEW_PACKAGE = "review_package"
    APPROVAL_RECORD = "approval_record"
    REVISION_REQUEST = "revision_request"
    ISSUE_RECORD = "issue_record"
    KB_CONTEXT_PACKET = "kb_context_packet"
    CHECKPOINT = "checkpoint"
    ROLLBACK_RECORD = "rollback_record"
    INVALIDATION_REPORT = "invalidation_report"
    ASSEMBLY_MANIFEST = "assembly_manifest"
    REVIEW_CUT = "review_cut"
    FINAL_CUT = "final_cut"
    DELIVERY_PACKAGE = "delivery_package"
    SUBTITLE = "subtitle"


class FilmPhase(StrEnum):
    """The canonical production phases of a film."""

    INTAKE = "intake"
    CONSTITUTION = "constitution"
    DEVELOPMENT = "development"
    SCRIPT = "script"
    VISUAL_DEV = "visual_dev"
    SHOT_BIBLE = "shot_bible"
    GEN_PLANNING = "gen_planning"
    GENERATION = "generation"
    QC = "qc"
    POST = "post"
    DELIVERY = "delivery"


class AgentRole(StrEnum):
    """Role classifications for registered agents."""

    ORCHESTRATOR = "orchestrator"
    CREATOR = "creator"
    REVIEWER = "reviewer"
    VALIDATOR = "validator"
    SYNTHESIZER = "synthesizer"
    OPERATOR = "operator"
    CURATOR = "curator"


class AgentFamily(StrEnum):
    """Agent family groupings."""

    OPERATIONS = "operations"
    PRODUCER = "producer"
    DEVELOPMENT = "development"
    SCREENWRITING = "screenwriting"
    VISUAL_DEV = "visual_dev"
    REFERENCE = "reference"
    DIRECTING = "directing"
    PROMPT_PLANNING = "prompt_planning"
    GENERATION = "generation"
    QC = "qc"
    POST = "post"
    MEMORY = "memory"


class ValidationStatus(StrEnum):
    """Validator output status."""

    PASS = "pass"
    PASS_WITH_NOTES = "pass_with_notes"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"
    ERROR = "error"


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


class GenerationStatus(StrEnum):
    """Status of a generation ledger row."""

    PREPARED = "prepared"
    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    BLOCKED_PROVIDER = "blocked_provider"
    BLOCKED_BUDGET = "blocked_budget"


class GenerationMode(StrEnum):
    """Generation modes for cost control."""

    MOCK = "mock"
    TEST = "test"
    PREVIEW = "preview"
    PRODUCTION = "production"


class IssueSeverity(StrEnum):
    """Severity levels for issue records."""

    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


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
