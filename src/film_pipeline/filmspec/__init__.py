"""Pure film vocabulary and phase order shared by every studio layer."""

from __future__ import annotations

from enum import StrEnum


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


class IssueSeverity(StrEnum):
    """Severity levels for issue records."""

    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


PHASE_SEQUENCE: tuple[str, ...] = tuple(phase.value for phase in FilmPhase)

PHASE_GATES: dict[str, str] = {
    "intake": "config",
    "constitution": "constitution",
    "development": "treatment",
    "script": "script",
    "visual_dev": "visual_bible",
    "shot_bible": "shot_bible",
    "gen_planning": "generation_spend",
    "generation": "generation_batch",
    "qc": "qc",
    "post": "assembly",
    "delivery": "final_delivery",
}
PHASE_AGNOSTIC_PHASES: set[str] = {
    "intake",
    "constitution",
    "development",
    "script",
    "visual_dev",
    "shot_bible",
    "gen_planning",
    "qc",
    "post",
    "delivery",
}
GENERATION_DEPENDENT_PHASES: set[str] = {"generation"}

# Closed transition vocabulary shared by validation and post production.
TRANSITION_TYPES: tuple[str, ...] = ("cut", "dissolve", "fade_in", "fade_out", "crossfade")
# A bare "fade" means fade to black; "wipe" has no canonical equivalent.
LEGACY_TRANSITION_ALIASES: dict[str, str] = {"fade": "fade_out"}


def next_phase(phase: str) -> str | None:
    """Return the next phase, or ``None`` for delivery or an unknown phase."""
    try:
        index = PHASE_SEQUENCE.index(phase)
    except ValueError:
        return None
    if index == len(PHASE_SEQUENCE) - 1:
        return None
    return PHASE_SEQUENCE[index + 1]
