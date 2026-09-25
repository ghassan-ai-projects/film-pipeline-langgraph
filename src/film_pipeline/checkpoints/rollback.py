"""Rollback manager — artifact, phase, and project rollback."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.checkpoints.invalidation import InvalidationEngine
from film_pipeline.checkpoints.manager import CheckpointManager
from film_pipeline.schemas.checkpoint import (
    CheckpointMetadata,
    InvalidationReport,
    RollbackOutcome,
    RollbackRecord,
)


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

        report = self._invalidation_report(checkpoint_id, checkpoint, artifact_types)
        self._restore_checkpoint_files(checkpoint)
        record = self._record_rollback(
            checkpoint_id=checkpoint_id,
            project_id=checkpoint.project_id,
            performed_by=performed_by,
        )
        # Create a new commit for the rollback (does not rewrite history)
        self.git.commit(
            f"rollback: to {checkpoint_id} by {performed_by}",
            files=None,
        )
        return record, report

    def _invalidation_report(
        self,
        checkpoint_id: str,
        checkpoint: CheckpointMetadata,
        artifact_types: list[str] | None,
    ) -> InvalidationReport:
        """Report which artifacts rolling back to this checkpoint reverts or invalidates."""
        return self.invalidation.report(
            rollback_target=checkpoint_id,
            artifact_types=artifact_types or list(checkpoint.artifact_versions.keys()),
            requires_regeneration=checkpoint.phase.value in ("generation", "qc", "post"),
        )

    def _restore_checkpoint_files(self, checkpoint: CheckpointMetadata) -> None:
        """Restore every file tracked at the checkpoint commit."""
        if checkpoint.git_commit:
            self.git.restore_files(checkpoint.git_commit, ["."])

    def _record_rollback(
        self,
        checkpoint_id: str,
        project_id: str,
        performed_by: str,
    ) -> RollbackRecord:
        """Append the success audit record for this rollback."""
        record = RollbackRecord(
            rollback_id=f"rollback:{checkpoint_id}:{uuid4().hex[:8]}",
            project_id=project_id,
            target_checkpoint_id=checkpoint_id,
            invalidation_report_ref=f"invalidation:{checkpoint_id}",
            performed_by=performed_by,
            created_at=datetime.now(UTC),
            outcome=RollbackOutcome.SUCCESS,
        )
        self.records.append(record)
        return record

    def rollback_artifact(
        self,
        artifact_id: str,
        target_commit: str,
        performed_by: str = "system",
    ) -> None:
        """Rollback a single artifact to a previous commit.

        Artifact ids are not git paths — the tracked tree stores them under
        their layout directories (e.g. ``artifacts/01-vision/<id>/...``).
        Resolve the tracked paths from the commit tree instead of passing the
        bare id, which can never match.
        """
        _ = performed_by
        tracked = [
            path
            for path in self.git.list_files(target_commit)
            if path == artifact_id
            or path.startswith(f"{artifact_id}/")
            or f"/{artifact_id}/" in path
        ]
        if not tracked:
            raise ValueError(
                f"Cannot rollback artifact '{artifact_id}': no tracked files for it "
                f"exist at commit {target_commit[:8]}."
            )
        self.git.restore_files(target_commit, tracked)
        self.git.commit(f"rollback: artifact {artifact_id} to {target_commit[:8]}")
