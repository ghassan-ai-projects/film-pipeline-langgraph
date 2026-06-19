"""Artifact metadata writer/reader — attaches metadata to every artifact."""

from __future__ import annotations

from pathlib import Path

from film_pipeline.schemas.artifact import ArtifactMetadata


def read_metadata(path: Path) -> ArtifactMetadata:
    return ArtifactMetadata.model_validate_json(path.read_text())


def write_metadata(path: Path, meta: ArtifactMetadata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(meta.model_dump_json(indent=2))
