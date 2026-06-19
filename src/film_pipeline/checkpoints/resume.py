"""Resume manager — lightweight runtime snapshots for crash recovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class ResumeSnapshot:
    """Lightweight checkpoint for resuming after interruption."""

    snapshot_id: str
    generation_id: str
    graph_node: str
    provider_job_id: str | None = None
    last_safe_step: str = ""
    next_action: str = ""
    state: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ResumeManager:
    """Manages runtime snapshots for generation crash recovery.

    Write snapshots: before submit, after job_id, after each poll,
    after download, after frame extraction, after failure decision.
    """

    snapshots: dict[str, list[ResumeSnapshot]] = field(default_factory=dict)

    def create(
        self,
        generation_id: str,
        graph_node: str,
        provider_job_id: str | None = None,
        last_safe_step: str = "",
        next_action: str = "",
        state: dict[str, Any] | None = None,
    ) -> ResumeSnapshot:
        snapshot = ResumeSnapshot(
            snapshot_id=f"snapshot:{generation_id}:{uuid4().hex[:8]}",
            generation_id=generation_id,
            graph_node=graph_node,
            provider_job_id=provider_job_id,
            last_safe_step=last_safe_step,
            next_action=next_action,
            state=state,
        )
        self.snapshots.setdefault(generation_id, []).append(snapshot)
        return snapshot

    def find_latest(self, generation_id: str) -> ResumeSnapshot | None:
        snaps = self.snapshots.get(generation_id, [])
        return snaps[-1] if snaps else None

    def find_all(self, generation_id: str) -> list[ResumeSnapshot]:
        return self.snapshots.get(generation_id, [])

    def clear(self, generation_id: str) -> None:
        self.snapshots.pop(generation_id, None)

    def resume(self, snapshot: ResumeSnapshot) -> dict[str, Any]:
        """Return the state to resume from."""
        return snapshot.state or {}
