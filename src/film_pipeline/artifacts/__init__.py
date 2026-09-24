"""Artifact storage, versioning, and asset manifests — canonical registry."""

from __future__ import annotations

from film_pipeline.artifacts.envelope import (
    ArtifactCurrentMeta,
    ArtifactEnvelope,
    SchemaTooNewError,
    payload_checksum,
)
from film_pipeline.artifacts.manifest import (
    AssetEntry,
    AssetManifest,
    read_manifest,
    write_manifest,
)
from film_pipeline.artifacts.paths import (
    artifact_dir,
    artifact_path,
    media_scene_dir,
    phase_dir,
    project_dir,
)
from film_pipeline.artifacts.registry import (
    REGISTRY,
    ArtifactKindRegistry,
    KindNotRegisteredError,
    KindSpec,
)
from film_pipeline.artifacts.store import ArtifactStore

__all__ = [
    "REGISTRY",
    "ArtifactCurrentMeta",
    "ArtifactEnvelope",
    "ArtifactKindRegistry",
    "ArtifactStore",
    "AssetEntry",
    "AssetManifest",
    "KindNotRegisteredError",
    "KindSpec",
    "SchemaTooNewError",
    "artifact_dir",
    "artifact_path",
    "media_scene_dir",
    "payload_checksum",
    "phase_dir",
    "project_dir",
    "read_manifest",
    "write_manifest",
]
