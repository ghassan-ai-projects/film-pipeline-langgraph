"""Creative branch management — alternate endings, tone experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.schemas.checkpoint import BranchMetadata


@dataclass
class BranchManager:
    """Manage creative branches for alternative film explorations."""

    git: GitBackend
    branches: dict[str, BranchMetadata] = field(default_factory=dict)

    def create(
        self,
        project_id: str,
        base_checkpoint_id: str,
        purpose: str,
    ) -> BranchMetadata:
        branch_id = f"branch:{project_id}:{uuid4().hex[:8]}"
        branch_name = f"creative/{uuid4().hex[:6]}"

        self.git.branch(branch_name)

        meta = BranchMetadata(
            branch_id=branch_id,
            project_id=project_id,
            base_checkpoint_id=base_checkpoint_id,
            purpose=purpose,
            active=True,
        )
        self.branches[branch_id] = meta
        return meta

    def list_active(self) -> list[BranchMetadata]:
        return [b for b in self.branches.values() if b.active]

    def get(self, branch_id: str) -> BranchMetadata | None:
        return self.branches.get(branch_id)
