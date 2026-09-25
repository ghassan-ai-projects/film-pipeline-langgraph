"""Artifact metadata, version, and reference."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import Field

from film_pipeline.schemas.base import ArtifactStatus, ArtifactType, FilmPhase, SchemaBase

_REF_VERSION_PATTERN = re.compile(r"^v(\d+)$")


class ArtifactRef(SchemaBase):
    """A pointer to a specific artifact version.

    Canonical string form: ``artifact:<phase>:<artifact_id>:v<N>`` where
    ``<phase>`` is a :class:`FilmPhase` value.
    """

    artifact_id: str
    version: int = Field(ge=1)
    phase: str

    def to_string(self) -> str:
        """Render the canonical ref string."""
        return f"artifact:{self.phase}:{self.artifact_id}:v{self.version}"

    @classmethod
    def from_string(cls, ref: str) -> ArtifactRef:
        """Parse the canonical ref string; anything else raises ``ValueError``."""
        parts = ref.split(":")
        if len(parts) != 4 or parts[0] != "artifact":
            raise ValueError(
                f"Invalid artifact ref '{ref}'. Expected 'artifact:<phase>:<artifact_id>:v<N>'."
            )
        version_match = _REF_VERSION_PATTERN.match(parts[3])
        if version_match is None:
            raise ValueError(f"Invalid artifact ref '{ref}': version must be 'v<number>'.")
        if not parts[1] or not parts[2]:
            raise ValueError(f"Invalid artifact ref '{ref}': empty segment.")
        # Note: the id charset is enforced by save() (validate_artifact_id), not
        # here. Refs are also parsed for identity/display of ids that were never
        # stored under this grammar, and rejecting them would break version-stem
        # grouping in review/diff.py rather than surfacing a real problem.
        return cls(
            artifact_id=parts[2],
            version=int(version_match.group(1)),
            phase=FilmPhase(parts[1]),
        )


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
