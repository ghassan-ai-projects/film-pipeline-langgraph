"""Artifact storage, versioning, and asset manifests — canonical registry."""

from __future__ import annotations

from film_pipeline.artifacts.envelope import (
    ArtifactCurrentMeta,
    ArtifactEnvelope,
    SchemaTooNewError,
    payload_checksum,
)
from film_pipeline.artifacts.index import ArtifactIndex
from film_pipeline.artifacts.manifest import (
    AssetEntry,
    AssetManifest,
    read_manifest,
    write_manifest,
)
from film_pipeline.artifacts.paths import (
    artifact_dir,
    artifact_path,
    checkpoint_dir,
    current_artifact_path,
    generated_asset_dir,
    phase_dir,
    project_dir,
    reference_dir,
    state_dir,
    version_dir,
)
from film_pipeline.artifacts.registry import (
    REGISTRY,
    ArtifactKindRegistry,
    KindNotRegisteredError,
    KindSpec,
)
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.artifacts.versioning import approve, create_version, supersede

__all__ = [
    "REGISTRY",
    "ArtifactCurrentMeta",
    "ArtifactEnvelope",
    "ArtifactIndex",
    "ArtifactKindRegistry",
    "ArtifactStore",
    "AssetEntry",
    "AssetManifest",
    "KindNotRegisteredError",
    "KindSpec",
    "SchemaTooNewError",
    "approve",
    "artifact_dir",
    "artifact_path",
    "checkpoint_dir",
    "create_version",
    "current_artifact_path",
    "generated_asset_dir",
    "payload_checksum",
    "phase_dir",
    "project_dir",
    "read_manifest",
    "reference_dir",
    "state_dir",
    "supersede",
    "version_dir",
    "write_manifest",
]
