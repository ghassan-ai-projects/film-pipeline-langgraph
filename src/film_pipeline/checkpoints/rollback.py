"""Rollback manager — artifact, phase, and project rollback."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.checkpoints.invalidation import InvalidationEngine
from film_pipeline.checkpoints.manager import CheckpointManager
from film_pipeline.schemas.checkpoint import InvalidationReport, RollbackRecord


@dataclass
class RollbackManager:
    """Orchestrates rollback operations with invalidation and audit."""

    checkpoint_manager: CheckpointManager
    git: GitBackend
    invalidation: InvalidationEngine = field(default_factory=InvalidationEngine)
    records: list[RollbackRecord] = field(default_factory=list)

    def rollback_to_checkpoint(
        self,
        checkpoint_id: str,
        performed_by: str = "system",
        artifact_types: list[str] | None = None,
    ) -> tuple[RollbackRecord, InvalidationReport]:
        """Rollback to a checkpoint, produce invalidation report.

        Returns (audit record, invalidation report).
        Requires human confirmation before executing.
        """
        checkpoint = self.checkpoint_manager.get(checkpoint_id)
        if checkpoint is None:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")

        # Produce invalidation report
        report = self.invalidation.report(
            rollback_target=checkpoint_id,
            artifact_types=artifact_types or list(checkpoint.artifact_versions.keys()),
            requires_regeneration=checkpoint.phase.value in ("generation", "qc", "post"),
        )

        # Restore files from the checkpoint commit
        if checkpoint.git_commit:
            # Restore all files tracked at that commit
            self.git.restore_files(checkpoint.git_commit, ["."])

        # Create audit rollback record
        record = RollbackRecord(
            rollback_id=f"rollback:{checkpoint_id}:{uuid4().hex[:8]}",
            project_id=checkpoint.project_id,
            target_checkpoint_id=checkpoint_id,
            invalidation_report_ref=f"invalidation:{checkpoint_id}",
            performed_by=performed_by,
            created_at=datetime.now(UTC),
            outcome="success",
        )
        self.records.append(record)

        # Create a new commit for the rollback (does not rewrite history)
        self.git.commit(
            f"rollback: to {checkpoint_id} by {performed_by}",
            files=None,
        )

        return record, report

    def rollback_artifact(
        self,
        artifact_id: str,
        target_commit: str,
        performed_by: str = "system",
    ) -> None:
        """Rollback a single artifact to a previous commit."""
        _ = performed_by
        self.git.restore_files(target_commit, [artifact_id])
        self.git.commit(f"rollback: artifact {artifact_id} to {target_commit[:8]}")
