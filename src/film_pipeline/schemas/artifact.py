"""Artifact metadata, version, and reference."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase, SchemaBase


class ArtifactRef(SchemaBase):
    """A lightweight pointer to a specific artifact version."""

    artifact_id: str
    version: int = Field(ge=1)


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
