"""Checkpoint rollback use cases shared by operator surfaces."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel

from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.checkpoints.invalidation import InvalidationEngine
from film_pipeline.checkpoints.rollback import RollbackManager
from film_pipeline.schemas import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.schemas.checkpoint import (
    CheckpointMetadata,
    RollbackOutcome,
    RollbackRecord,
)

from .errors import BackendOperationError
from .models import ArtifactRollbackResult, CheckpointRollbackResult

if TYPE_CHECKING:
    from .operator import OperatorService


def get_checkpoint(
    service: OperatorService,
    checkpoint_id: str,
) -> CheckpointMetadata | None:
    """Find checkpoint metadata by globally unique identifier."""
    return service.runtime.get_checkpoint(checkpoint_id)


def rollback_to_checkpoint(
    service: OperatorService,
    checkpoint: CheckpointMetadata,
    project_id: str,
) -> CheckpointRollbackResult:
    """Restore a project's checkpoint and persist rollback bookkeeping."""
    manager = service.runtime.checkpoint_managers.get(project_id)
    if manager is None:
        raise BackendOperationError("No checkpoint manager for project.")

    rollback_manager = RollbackManager(checkpoint_manager=manager, git=manager.git)
    rollback_manager.rollback_to_checkpoint(checkpoint.checkpoint_id, performed_by="operator")
    invalidation_ref, rollback_ref = _save_rollback_artifacts(
        _artifact_store(service),
        project_id,
        checkpoint.checkpoint_id,
        list(checkpoint.artifact_versions.keys()),
        performed_by="operator",
    )
    return CheckpointRollbackResult(
        rollback_target=checkpoint.checkpoint_id,
        phase=checkpoint.phase.value,
        reason=checkpoint.reason,
        invalidation_report_ref=invalidation_ref,
        rollback_record_ref=rollback_ref,
    )


def rollback_artifact(
    service: OperatorService,
    project_id: str,
    artifact_id: str,
    checkpoint_id: str = "",
) -> ArtifactRollbackResult:
    """Restore an artifact from a specific checkpoint or its latest matching one."""
    if checkpoint_id:
        checkpoint = get_checkpoint(service, checkpoint_id)
        if checkpoint is None:
            raise BackendOperationError(f"Checkpoint '{checkpoint_id}' not found.")
        if not checkpoint.git_commit:
            raise BackendOperationError(f"Checkpoint '{checkpoint_id}' has no git commit ref.")
        return _restore_artifact_at_commit(
            service, project_id, artifact_id, checkpoint, checkpoint_id
        )

    checkpoints = service.runtime.list_checkpoints(project_id)
    for checkpoint in sorted(checkpoints, key=lambda item: item.created_at, reverse=True):
        if checkpoint.git_commit and artifact_id in checkpoint.artifact_versions:
            try:
                return _restore_artifact_at_commit(
                    service,
                    project_id,
                    artifact_id,
                    checkpoint,
                    checkpoint.checkpoint_id,
                )
            except Exception:
                continue
    raise BackendOperationError(f"No checkpoint found containing artifact '{artifact_id}'.")


def _restore_artifact_at_commit(
    service: OperatorService,
    project_id: str,
    artifact_id: str,
    checkpoint: CheckpointMetadata,
    rollback_target: str,
) -> ArtifactRollbackResult:
    """Restore one artifact and persist invalidation and rollback records."""
    manager = service.runtime.checkpoint_managers.get(project_id)
    if manager is None:
        raise BackendOperationError("No checkpoint manager for project.")
    rollback_manager = RollbackManager(checkpoint_manager=manager, git=manager.git)
    rollback_manager.rollback_artifact(artifact_id, checkpoint.git_commit, performed_by="operator")
    invalidation_ref, rollback_ref = _save_rollback_artifacts(
        _artifact_store(service),
        project_id,
        rollback_target,
        list(checkpoint.artifact_versions.keys()) or [artifact_id],
        performed_by="operator",
    )
    return ArtifactRollbackResult(
        artifact_id=artifact_id,
        restored_from=rollback_target,
        git_commit=checkpoint.git_commit[:8],
        invalidation_report_ref=invalidation_ref,
        rollback_record_ref=rollback_ref,
    )


def _artifact_store(service: OperatorService) -> ArtifactStore:
    services = service.runtime.services
    if services is None:
        raise BackendOperationError("Runtime services are not initialized.")
    return services.artifact_store


def _save_rollback_artifacts(
    store: ArtifactStore,
    project_id: str,
    rollback_target: str,
    artifact_types: list[str],
    performed_by: str,
) -> tuple[str, str]:
    """Persist an invalidation report and rollback record to the artifact store."""
    invalidation_report = InvalidationEngine().report(
        rollback_target=rollback_target,
        artifact_types=artifact_types,
    )
    invalidation_id = f"invalidation_report_{uuid4().hex[:8]}"
    invalidation_ref = _persist_candidate(
        store,
        project_id,
        ArtifactType.INVALIDATION_REPORT,
        invalidation_id,
        invalidation_report,
    )
    record = RollbackRecord(
        rollback_id=f"rollback:{project_id}:{uuid4().hex[:8]}",
        project_id=project_id,
        target_checkpoint_id=rollback_target,
        invalidation_report_ref=invalidation_ref,
        performed_by=performed_by,
        created_at=datetime.now(UTC),
        outcome=RollbackOutcome.SUCCESS,
    )
    record_id = f"rollback_record_{uuid4().hex[:8]}"
    rollback_ref = _persist_candidate(
        store,
        project_id,
        ArtifactType.ROLLBACK_RECORD,
        record_id,
        record,
    )
    return invalidation_ref, rollback_ref


def _persist_candidate(
    store: ArtifactStore,
    project_id: str,
    artifact_type: ArtifactType,
    artifact_id: str,
    payload: BaseModel,
) -> str:
    """Persist one candidate artifact and return its artifact reference."""
    version = store.next_version(project_id, "intake", artifact_id)
    metadata = ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        project_id=project_id,
        phase=FilmPhase.INTAKE,
        version=version,
        status=ArtifactStatus.CANDIDATE,
        created_by="rollback_tool",
        created_at=datetime.now(UTC),
    )
    return store.save(payload, metadata).to_string()
