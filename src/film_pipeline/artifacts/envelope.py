"""Versioned storage envelope for artifacts (storage-upgrade plan D4).

Every versioned artifact is stored as one immutable envelope file
(``versions/vNNN.json``) carrying the payload plus its full provenance, and
one mutable artifact-level pointer file (``meta.json``) that names the current
version and its status. Generated views (``current.md``) and the derived
project index are rebuildable and carry no version of their own.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from film_pipeline.artifacts.serialization import NonFiniteNumberError
from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.schemas.artifact import ArtifactRef


class SchemaTooNewError(RuntimeError):
    """Raised when a stored artifact was written by a newer schema generation."""

    def __init__(self, kind: str, found: int, max_supported: int, path: str) -> None:
        self.kind = kind
        self.found = found
        self.max_supported = max_supported
        self.path = path
        super().__init__(
            f"Artifact {path} was written with {kind} schema_version {found}, but this "
            f"build supports at most {max_supported}. Upgrade film-pipeline to read it."
        )


class ChecksumMismatchError(RuntimeError):
    """Raised when a stored envelope fails its integrity check."""


class MutableRevisionMismatchError(RuntimeError):
    """Raised when a ref names a mutable kind's superseded revision.

    A mutable kind keeps exactly one revision-counted file, so an older ref
    cannot be satisfied. Returning the current content instead would silently
    answer a question the caller did not ask.
    """

    def __init__(self, artifact_id: str, requested: int, current: int) -> None:
        self.artifact_id = artifact_id
        self.requested = requested
        self.current = current
        super().__init__(
            f"Mutable artifact '{artifact_id}' is at revision {current}, but "
            f"revision {requested} was requested. Mutable kinds keep only their "
            "current revision; re-read the artifact to get the current ref."
        )


def payload_checksum(payload: dict[str, Any]) -> str:
    """Content checksum over the canonical payload form (stable across runs).

    ``allow_nan=False`` keeps the canonical form legal JSON: Python's default
    emits bare ``NaN``/``Infinity``, which a reader normalizes, so the
    recomputed checksum would differ and the artifact would be unreadable.
    """
    try:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except ValueError as exc:
        raise NonFiniteNumberError(
            f"Artifact payload contains a non-finite number and cannot be "
            f"checksummed or stored: {exc}"
        ) from exc
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


class ArtifactEnvelope(BaseModel):
    """One immutable version of one artifact: provenance + payload.

    Deliberately not a ``SchemaBase`` subclass: the base's string
    ``schema_version`` is superseded here by the per-kind int version.
    """

    model_config = ConfigDict(extra="allow")

    kind: str = Field(description="Registry key, e.g. 'film.studio/script'.")
    schema_version: int = Field(
        ge=0,
        description=(
            "Per-kind payload schema version; the envelope itself is v1. "
            "Version 0 marks a pre-versioning writer, readable via migrations."
        ),
    )
    artifact_id: str
    artifact_type: ArtifactType
    project_id: str
    phase: FilmPhase
    version: int = Field(ge=1)
    created_at: datetime
    created_by: str = ""
    reviewed_by: list[str] = Field(default_factory=list)
    validation_refs: list[str] = Field(default_factory=list)
    approval_ref: str | None = None
    kb_context_ref: str | None = None
    parents: list[ArtifactRef] = Field(default_factory=list)
    built_from: dict[str, str] = Field(default_factory=dict)
    prompt_template_version: str | None = None
    model_profile: str | None = None
    change_summary: str = ""
    checksum: str = ""
    revision: int | None = Field(
        default=None,
        description="Mutable kinds only: monotonically increasing write count.",
    )
    payload: dict[str, Any]


class ArtifactCurrentMeta(BaseModel):
    """Artifact-level current pointer and status (the mutable ``meta.json``).

    Status is a property of the artifact via its current version: a version
    that is no longer current is superseded by definition.
    """

    model_config = ConfigDict(extra="ignore")

    schema_version: int = Field(default=1, ge=1, description="Meta file format version.")
    artifact_id: str
    artifact_type: ArtifactType
    project_id: str
    phase: FilmPhase
    current_version: int = Field(ge=1)
    status: ArtifactStatus = ArtifactStatus.CANDIDATE
    created_at: datetime
    updated_at: datetime
    created_by: str = ""
    reviewed_by: list[str] = Field(default_factory=list)
    validation_refs: list[str] = Field(default_factory=list)
    approval_ref: str | None = None
    kb_context_ref: str | None = None
    checksum: str = ""


class ArtifactIndexEntry(BaseModel):
    """One row of the derived ``index/artifacts.json`` cache.

    Typed so the one persisted boundary that used raw dicts now validates on
    both write and read (AGENTS.md: no raw dicts across boundaries). The index
    is derived and rebuildable, so it carries no schema version of its own.
    """

    model_config = ConfigDict(extra="ignore")

    artifact_id: str
    artifact_type: ArtifactType
    phase: FilmPhase
    current_version: int = Field(ge=1)
    status: ArtifactStatus = ArtifactStatus.CANDIDATE
    created_at: datetime
    updated_at: datetime


class ArtifactIndex(BaseModel):
    """The derived per-project artifact index (``index/artifacts.json``)."""

    model_config = ConfigDict(extra="ignore")

    schema_version: int = Field(default=1, ge=1, description="Index format version.")
    artifacts: list[ArtifactIndexEntry] = Field(default_factory=list)
