"""Pure film vocabulary and phase order shared by every studio layer."""

from __future__ import annotations

__all__ = [
    "GENERATION_DEPENDENT_PHASES",
    "LEGACY_TRANSITION_ALIASES",
    "NO_ACTIVE_PROJECT",
    "PHASE_AGNOSTIC_PHASES",
    "PHASE_GATES",
    "PHASE_SEQUENCE",
    "STALE_GENERATION_REQUEST_CODES",
    "TEXT_ONLY_POLICY",
    "TRANSITION_TYPES",
    "AgentFamily",
    "AgentRole",
    "ArtifactType",
    "FilmPhase",
    "GenerationStatus",
    "IssueSeverity",
    "ValidationStatus",
    "blocking_issues",
    "is_blocking_issue",
    "is_text_only_policy",
    "next_phase",
]
from enum import StrEnum
from typing import Any


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


class IssueSeverity(StrEnum):
    """Severity levels for issue records."""

    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


def is_blocking_issue(issue: object) -> bool:
    """Return whether an issue record's severity blocks phase advancement.

    The single definition of "this issue blocks". It was re-derived at more than
    a dozen call sites across eight packages as a bare
    ``issue.get("severity") == "blocking"``, and they had already diverged: some
    guarded against a malformed record with ``isinstance(issue, dict)`` and at
    least one did not, so a non-mapping issue raised ``AttributeError`` on that
    path while the others skipped it.

    Non-mappings are never blocking rather than an error: an issue list is
    persisted state, and crash recovery must not depend on every entry being
    well-formed.
    """
    if not isinstance(issue, dict):
        return False
    return str(issue.get("severity", "")) == IssueSeverity.BLOCKING.value


def blocking_issues(issues: object) -> list[dict[str, Any]]:
    """Return the issues whose severity blocks advancement."""
    if not isinstance(issues, (list, tuple)):
        return []
    return [issue for issue in issues if is_blocking_issue(issue)]


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

# Issue codes raised by the generation-planning gates when a project has no
# dispatchable work yet. They are reusable vocabulary rather than a per-module
# detail: the gate that raises them lives in the orchestrator validators, while
# the graph resume path, the operator service, and the MCP text-only policy all
# have to recognise and clear them once requests exist. Declaring them once
# keeps the producer and those three consumers from drifting apart.
STALE_GENERATION_REQUEST_CODES: frozenset[str] = frozenset(
    {"empty_generation_requests", "no_generation_requests"}
)


#: The ``generation_policy`` value that selects text-only delivery.
#:
#: The policy string is written by project creation and read by the generation
#: paths. The predicate lived as two byte-identical copies — one in
#: `operations._generation_ops`, one in `mcp.tools.generation._text_only` — with the
#: literal in three places, so the vocabulary is owned here.
#:
#: `operations._generation_ops` was deleted with the orphaned operator surface (doc
#: 03 slice 1), leaving `mcp` as the only reader. The *string* and this predicate
#: stay: the value is vocabulary and the predicate is the one-line rule that reads
#: it. The row *builders* that used to sit below moved to
#: `generation/text_only.py` (doc 06 slice 6.7) — they construct rows, which is not
#: vocabulary.
TEXT_ONLY_POLICY = "text_only"


def is_text_only_policy(state: object) -> bool:
    """Return whether a project state selects the text-only generation policy."""
    if not isinstance(state, dict):
        return False
    return str(state.get("generation_policy", "")).strip().lower() == TEXT_ONLY_POLICY


#: The one message for "this request has no project to act on". Both the MCP
#: dispatcher and the tool layer need it, and a constant in either package would
#: import the other. It was previously written inline at 48 call sites in three
#: wordings, with five different emptiness tests — `if not active` and
#: `if active is None` disagree on an empty dict — so one condition produced
#: different answers.
NO_ACTIVE_PROJECT = "No active project."


def next_phase(phase: str) -> str | None:
    """Return the next phase, or ``None`` for delivery or an unknown phase."""
    try:
        index = PHASE_SEQUENCE.index(phase)
    except ValueError:
        return None
    if index == len(PHASE_SEQUENCE) - 1:
        return None
    return PHASE_SEQUENCE[index + 1]
