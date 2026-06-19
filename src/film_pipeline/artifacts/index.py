"""Artifact index — queryable registry of all artifacts in a project."""

from __future__ import annotations

from dataclasses import dataclass, field

from film_pipeline.schemas.artifact import ArtifactMetadata


@dataclass
class ArtifactIndex:
    """In-memory queryable index over artifact metadata."""

    entries: list[ArtifactMetadata] = field(default_factory=list)

    def add(self, meta: ArtifactMetadata) -> None:
        self.entries.append(meta)

    def by_type(self, artifact_type: str) -> list[ArtifactMetadata]:
        return [e for e in self.entries if e.artifact_type.value == artifact_type]

    def by_phase(self, phase: str) -> list[ArtifactMetadata]:
        return [e for e in self.entries if e.phase.value == phase]

    def by_status(self, status: str) -> list[ArtifactMetadata]:
        return [e for e in self.entries if e.status.value == status]

    def latest(self, artifact_id: str) -> ArtifactMetadata | None:
        candidates = [e for e in self.entries if e.artifact_id == artifact_id]
        return max(candidates, key=lambda m: m.version) if candidates else None
