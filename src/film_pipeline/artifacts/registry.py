"""Artifact kind registry — the single map from artifact id to storage spec.

Registering a kind is what makes an artifact storable: the registry assigns
the stable kind key, the payload schema version, and mutability. Adding a new
artifact kind means defining its payload model and one registration line —
no changes to the store, path helpers, or MCP tools.

Unknown ids raise :class:`KindNotRegisteredError` at save time so the catalog
cannot silently drift; prefix entries cover dynamic ids such as
``matrix_patch_<phase>`` or ``invalidation_report_<hex8>``.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from film_pipeline.schemas.approval import ProfileChangeApproval, ProfileChangeProposal
from film_pipeline.schemas.checkpoint import CheckpointState, InvalidationReport, RollbackRecord
from film_pipeline.schemas.generation import GenerationLedger
from film_pipeline.schemas.matrix_patch import MatrixPatch
from film_pipeline.schemas.validation import ConsensusReport, ValidationReport

Migration = Callable[[dict[str, Any]], dict[str, Any]]

#: Artifact ids must be lowercase snake_case so directory names stay clean
#: and unambiguous on case-insensitive filesystems.
ARTIFACT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class KindNotRegisteredError(RuntimeError):
    """Raised when saving an artifact id that has no registered kind."""

    def __init__(self, artifact_id: str) -> None:
        self.artifact_id = artifact_id
        super().__init__(
            f"Artifact id '{artifact_id}' has no registered kind. Register it in "
            "film_pipeline.artifacts.registry before saving."
        )


def validate_artifact_id(artifact_id: str) -> None:
    """Enforce the artifact id rules (lowercase snake_case, filesystem-safe)."""
    if not ARTIFACT_ID_PATTERN.match(artifact_id):
        raise ValueError(
            f"Invalid artifact id '{artifact_id}': must match {ARTIFACT_ID_PATTERN.pattern} "
            "(lowercase snake_case, no ':' or '/')."
        )


def sanitize_artifact_id(raw_id: str) -> str:
    """Map an arbitrary entity id onto a valid artifact id, injectively.

    Entity ids (proposal ids, run ids) may contain ``:`` or ``-``; artifact
    ids may not. Non-conforming characters are hex-escaped (``:`` → ``_3a_``)
    so distinct entity ids can never collide into one artifact directory.
    """
    sanitized = re.sub(r"[^a-z0-9_]", lambda match: f"_{ord(match.group()):02x}_", raw_id.lower())
    if not sanitized or not ARTIFACT_ID_PATTERN.match(sanitized):
        sanitized = f"a_{sanitized}" if sanitized else "a"
    return sanitized


@dataclass(frozen=True)
class KindSpec:
    """Storage contract for one artifact kind."""

    artifact_id: str
    kind: str  # stable registry key, e.g. "film.studio/script"
    schema_version: int = 1
    payload_model: type[BaseModel] | None = None  # None: payload stays a plain dict
    mutable: bool = False  # mutable kinds rewrite a single file instead of versioning
    renderer: Callable[[dict[str, Any]], str] | None = None  # typed view; P5


class ArtifactKindRegistry:
    """Exact-match + prefix registry of artifact kinds."""

    def __init__(self) -> None:
        self._exact: dict[str, KindSpec] = {}
        self._prefixes: dict[str, KindSpec] = {}

    def register(self, spec: KindSpec) -> None:
        self._exact[spec.artifact_id] = spec

    def register_prefix(self, prefix: str, spec: KindSpec) -> None:
        self._prefixes[prefix] = spec

    def spec_for(self, artifact_id: str) -> KindSpec:
        spec = self._exact.get(artifact_id)
        if spec is not None:
            return spec
        for prefix in sorted(self._prefixes, key=len, reverse=True):
            if artifact_id.startswith(prefix):
                return self._prefixes[prefix]
        raise KindNotRegisteredError(artifact_id)

    def known_ids(self) -> list[str]:
        return sorted(self._exact)


def _kind_slug(artifact_id: str) -> str:
    return f"film.studio/{artifact_id.replace('_', '-')}"


def _spec(artifact_id: str, **kw: Any) -> KindSpec:
    return KindSpec(artifact_id=artifact_id, kind=_kind_slug(artifact_id), **kw)


def _register_defaults(registry: ArtifactKindRegistry) -> None:
    exact: dict[str, KindSpec] = {
        # intake
        "project_profile": _spec("project_profile"),
        "project_constraints": _spec("project_constraints"),
        "scope_contract": _spec("scope_contract"),
        "intake_analysis": _spec("intake_analysis"),
        "project_config": _spec("project_config"),
        # vision / development / script
        "film_constitution": _spec("film_constitution"),
        "logline": _spec("logline"),
        "premise": _spec("premise"),
        "treatment": _spec("treatment"),
        "act_map": _spec("act_map"),
        "scene_list": _spec("scene_list"),
        "story_bible": _spec("story_bible"),
        "script": _spec("script"),
        "dialogue_pass": _spec("dialogue_pass"),
        "scene_intent": _spec("scene_intent"),
        # visual dev / shot bible
        "reference_index": _spec("reference_index"),
        "reference_sheet": _spec("reference_sheet"),
        "character_bible": _spec("character_bible"),
        "environment_bible": _spec("environment_bible"),
        "camera_language_bible": _spec("camera_language_bible"),
        "style_bible": _spec("style_bible"),
        "execution_brief": _spec("execution_brief"),
        "shot_matrix": _spec("shot_matrix"),
        "shot_bible": _spec("shot_bible"),
        # planning / generation
        "cost_estimate": _spec("cost_estimate"),
        "generation_plan": _spec("generation_plan"),
        "generation_ledger": _spec(
            "generation_ledger", payload_model=GenerationLedger, mutable=True
        ),
        "budget_state": _spec("budget_state"),
        "prompt_package": _spec("prompt_package"),
        "prompt_registry": _spec("prompt_registry"),
        "coverage_group": _spec("coverage_group"),
        "continuity_ledger": _spec("continuity_ledger"),
        # qc / post / delivery
        "consensus_report": _spec("consensus_report", payload_model=ConsensusReport),
        "validation_report": _spec("validation_report", payload_model=ValidationReport),
        "issue_record": _spec("issue_record"),
        "review_package": _spec("review_package"),
        "approval_record": _spec("approval_record"),
        "revision_request": _spec("revision_request"),
        "kb_context_packet": _spec("kb_context_packet"),
        "assembly_manifest": _spec("assembly_manifest"),
        "review_cut": _spec("review_cut"),
        "final_cut": _spec("final_cut"),
        "delivery_package": _spec("delivery_package"),
        "subtitle": _spec("subtitle"),
        "subtitles": _spec("subtitles"),
        "master_film_matrix": _spec("master_film_matrix"),
        "matrix_row": _spec("matrix_row"),
    }
    for spec in exact.values():
        registry.register(spec)

    # Dynamic ids: stable prefixes with per-entity suffixes.
    registry.register_prefix("matrix_patch_", _spec("matrix_patch", payload_model=MatrixPatch))
    registry.register_prefix("repair_feedback_", _spec("repair_feedback"))
    registry.register_prefix(
        "profile_change_proposal_",
        _spec("profile_change_proposal", payload_model=ProfileChangeProposal),
    )
    registry.register_prefix(
        "profile_change_approval_",
        _spec("profile_change_approval", payload_model=ProfileChangeApproval),
    )
    registry.register_prefix(
        "invalidation_report_", _spec("invalidation_report", payload_model=InvalidationReport)
    )
    registry.register_prefix(
        "rollback_record_", _spec("rollback_record", payload_model=RollbackRecord)
    )
    registry.register_prefix("checkpoint_", _spec("checkpoint", payload_model=CheckpointState))
    # Per-profile-version project config snapshots (project_config_v1, v2, ...).
    registry.register_prefix("project_config_v", _spec("project_config"))


REGISTRY = ArtifactKindRegistry()
_register_defaults(REGISTRY)


# --- Payload schema migrations -------------------------------------------------

#: Registered payload migrations keyed by (kind, from_version). Each entry
#: upgrades a payload one version; reads chain them up to the kind's current
#: schema_version. Only N → N+1 steps ever need live code (plan D4).
MIGRATIONS: dict[tuple[str, int], Migration] = {}


def register_migration(kind: str, from_version: int, migration: Migration) -> None:
    """Register a one-step payload migration ``from_version`` → ``+1``."""
    MIGRATIONS[(kind, from_version)] = migration


def migrate_payload(
    kind: str, payload: dict[str, Any], from_version: int, to_version: int
) -> dict[str, Any]:
    """Chain registered migrations to bring ``payload`` up to ``to_version``."""
    current = payload
    version = from_version
    while version < to_version:
        migration = MIGRATIONS.get((kind, version))
        if migration is None:
            raise KeyError(
                f"No migration registered for {kind} v{version} (target v{to_version}). "
                "The stored artifact is older than this build supports; run the "
                "storage migration."
            )
        current = migration(current)
        version += 1
    return current
