"""Checkpoint manager — create, list, get, compare checkpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.schemas._base import FilmPhase
from film_pipeline.schemas.checkpoint import CheckpointMetadata


@dataclass
class CheckpointManager:
    """Manages semantic checkpoints backed by git.

    Every checkpoint creates a git commit + annotated tag with metadata
    that links artifact versions, approvals, validations, and budget state.
    """

    git: GitBackend
    checkpoints: dict[str, CheckpointMetadata] = field(default_factory=dict)

    def create(
        self,
        project_id: str,
        phase: FilmPhase,
        reason: str,
        artifact_versions: dict[str, str] | None = None,
        approval_refs: list[str] | None = None,
        validation_refs: list[str] | None = None,
        budget_state_ref: str = "",
        graph_state_ref: str = "",
    ) -> CheckpointMetadata:
        checkpoint_id = f"checkpoint:{project_id}:{phase.value}:{uuid4().hex[:8]}"
        tag_name = f"checkpoint/{phase.value}-{uuid4().hex[:6]}"

        commit_msg = f"checkpoint: {phase.value} — {reason}"
        commit_hash = self.git.commit(commit_msg)
        self.git.tag(tag_name, f"Checkpoint: {reason}")

        meta = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            project_id=project_id,
            phase=phase,
            created_at=datetime.now(UTC),
            reason=reason,
            artifact_versions=artifact_versions or {},
            approval_refs=approval_refs or [],
            validation_refs=validation_refs or [],
            budget_state_ref=budget_state_ref,
            graph_state_ref=graph_state_ref,
            git_commit=commit_hash,
            git_tag=tag_name,
        )
        self.checkpoints[checkpoint_id] = meta
        return meta

    def get(self, checkpoint_id: str) -> CheckpointMetadata | None:
        return self.checkpoints.get(checkpoint_id)

    def list_all(self) -> list[CheckpointMetadata]:
        return list(self.checkpoints.values())

    def list_for_project(self, project_id: str) -> list[CheckpointMetadata]:
        return [c for c in self.checkpoints.values() if c.project_id == project_id]

    def __len__(self) -> int:
        return len(self.checkpoints)
