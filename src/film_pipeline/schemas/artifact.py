"""Artifact metadata, version, and reference."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import Field

from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase, SchemaBase

_REF_VERSION_PATTERN = re.compile(r"^v(\d+)$")


class ArtifactRef(SchemaBase):
    """A pointer to a specific artifact version.

    Canonical string form: ``artifact:<phase>:<artifact_id>:v<N>``. The legacy
    phase-less form ``artifact:<artifact_id>:v<N>`` (and historical ids that
    embedded colons) still parse — ``phase`` is ``None`` for those and callers
    resolve the phase through the store's index.
    """

    artifact_id: str
    version: int = Field(ge=1)
    phase: str | None = None

    def to_string(self) -> str:
        """Render the canonical ref string."""
        if self.phase:
            return f"artifact:{self.phase}:{self.artifact_id}:v{self.version}"
        return f"artifact:{self.artifact_id}:v{self.version}"

    @classmethod
    def from_string(cls, ref: str) -> ArtifactRef:
        """Parse a canonical or legacy ref string."""
        parts = ref.split(":")
        if not parts or parts[0] != "artifact" or len(parts) < 3:
            raise ValueError(
                f"Invalid artifact ref '{ref}'. Expected "
                "'artifact:<phase>:<artifact_id>:v<N>' or "
                "'artifact:<artifact_id>:v<N>'."
            )
        version_match = _REF_VERSION_PATTERN.match(parts[-1])
        if version_match is None:
            raise ValueError(f"Invalid artifact ref '{ref}': version must be 'v<number>'.")
        version = int(version_match.group(1))
        middle = parts[1:-1]
        if not all(middle):
            raise ValueError(f"Invalid artifact ref '{ref}': empty artifact id segment.")
        if len(middle) == 1:
            return cls(artifact_id=middle[0], version=version)
        # Four+ segments: either canonical (phase, id) or a legacy id that
        # itself contained colons. The fixed phase vocabulary disambiguates.
        candidate_phase, candidate_id = middle[0], ":".join(middle[1:])
        try:
            FilmPhase(candidate_phase)
        except ValueError:
            pass
        else:
            return cls(artifact_id=candidate_id, version=version, phase=candidate_phase)
        return cls(artifact_id=":".join(middle), version=version)


class ArtifactMetadata(SchemaBase):
    """Attached to every stored artifact."""

    artifact_id: str
    artifact_type: ArtifactType
    project_id: str
    phase: FilmPhase
    version: int = Field(ge=1)
    status: ArtifactStatus = ArtifactStatus.CANDIDATE
    parents: list[ArtifactRef] = Field(default_factory=list)
    created_by: str = Field(description="Agent id that produced this artifact.")
    reviewed_by: list[str] = Field(default_factory=list)
    validation_refs: list[str] = Field(default_factory=list)
    approval_ref: str | None = None
    kb_context_ref: str | None = None
    created_at: datetime
    schema_version: str = "v1"
    built_from: dict[str, str] = Field(
        default_factory=dict,
        description="Map of artifact_id → version_ref at creation time.",
    )
    change_summary: str = Field(
        default="",
        description="What changed in this version (set on repair/revision).",
    )


class ArtifactVersion(SchemaBase):
    """One version of an artifact with its lineage."""

    version_id: str
    artifact_id: str
    project_id: str
    parent_version_id: str | None = None
    created_at: datetime
    created_by: str
    reason: str = Field(default="", description="Why this version was created.")
    change_summary: str = ""
    validation_refs: list[str] = Field(default_factory=list)
    approval_ref: str | None = None
    status: ArtifactStatus = ArtifactStatus.CANDIDATE
    path: str = Field(description="Path to the versioned artifact content.")
