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
    "is_text_only_policy",
    "next_phase",
    "text_only_generation_request",
    "text_only_generation_requests",
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
#: paths in two packages. The predicate lived as two byte-identical copies — one
#: in `operations._generation_ops`, one in `mcp.tools.generation._text_only` —
#: with the literal in three places, so the vocabulary is owned here.
TEXT_ONLY_POLICY = "text_only"


def is_text_only_policy(state: object) -> bool:
    """Return whether a project state selects the text-only generation policy."""
    if not isinstance(state, dict):
        return False
    return str(state.get("generation_policy", "")).strip().lower() == TEXT_ONLY_POLICY


def text_only_generation_request(
    project_id: str,
    shot_id: str,
    provider: str,
    model: str,
) -> dict[str, Any]:
    """Build one completed text-only generation request row.

    The text-only policy satisfies the generation gates without producing media.
    Both the operator service and the MCP tool path build these rows, and they
    must agree on the id scheme and field set, so the shape is declared once.
    The ``shot_id`` of ``"all"`` marks the single fallback row used when no shot
    rows exist, and carries no ``shot_id`` in its prompt payload.
    """
    payload: dict[str, Any] = {"text_only": True}
    if shot_id != "all":
        payload["shot_id"] = shot_id
    return {
        "generation_request_id": f"text-only-{project_id}-{shot_id}",
        "generation_id": f"text-only-{project_id}-{shot_id}",
        "project_id": project_id,
        "shot_id": shot_id,
        "mode": "text_only",
        "provider": provider,
        "model": model,
        "prompt_ref": "",
        "prompt_payload": payload,
        "reference_refs": [],
        "status": "completed",
    }


def text_only_generation_requests(
    project_id: str,
    shot_rows: list[dict[str, Any]],
    provider: str,
    model: str,
) -> list[dict[str, Any]]:
    """Build one completed text-only request per shot row, or a single fallback.

    Rows without a usable ``shot_id`` (falling back to ``scene_id``) are
    skipped; if that leaves nothing, the fallback ``"all"`` row is emitted so
    the generation gate is still satisfied.
    """
    requests: list[dict[str, Any]] = []
    for row in shot_rows:
        shot_id = str(row.get("shot_id", "") or row.get("scene_id", "")).strip()
        if not shot_id:
            continue
        requests.append(text_only_generation_request(project_id, shot_id, provider, model))
    if not requests:
        requests.append(text_only_generation_request(project_id, "all", provider, model))
    return requests


#: The one message for "this request has no project to act on". It lives in the
#: shared vocabulary module because both the MCP dispatcher and the tool layer
#: need it, and a constant in either package would import the other. It was
#: previously written inline at 48 call sites in three different wordings, with
#: five different emptiness tests — `if not active` and `if active is None`
#: disagree on an empty dict — so one condition produced different answers.
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
