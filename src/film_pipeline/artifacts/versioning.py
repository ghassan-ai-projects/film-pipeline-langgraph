"""Artifact version tracking — chains, status transitions, supersede."""

from __future__ import annotations

from datetime import UTC, datetime

from film_pipeline.schemas._base import ArtifactStatus
from film_pipeline.schemas.artifact import ArtifactVersion


def create_version(
    artifact_id: str,
    project_id: str,
    created_by: str,
    *,
    parent: ArtifactVersion | None = None,
    reason: str = "",
    validation_refs: list[str] | None = None,
    status: ArtifactStatus = ArtifactStatus.CANDIDATE,
) -> ArtifactVersion:
    parent_version = int(parent.version_id.rsplit("v", 1)[1]) if parent else None
    next_number = (parent_version or 0) + 1
    return ArtifactVersion(
        version_id=f"version:{artifact_id}:v{next_number}",
        artifact_id=artifact_id,
        project_id=project_id,
        parent_version_id=parent.version_id if parent else None,
        created_at=datetime.now(UTC),
        created_by=created_by,
        reason=reason,
        change_summary="",
        validation_refs=validation_refs or [],
        approval_ref=None,
        status=status,
        path="",
    )


def approve(version: ArtifactVersion) -> ArtifactVersion:
    """Return the same version marked APPROVED."""
    return _with_status(version, ArtifactStatus.APPROVED)


def supersede(version: ArtifactVersion) -> ArtifactVersion:
    """Return the same version marked SUPERSEDED."""
    return _with_status(version, ArtifactStatus.SUPERSEDED)


def _with_status(version: ArtifactVersion, status: ArtifactStatus) -> ArtifactVersion:
    """Rebuild ``version`` with a new status, revalidating every field."""
    return ArtifactVersion(**{**version.model_dump(), "status": status})
