"""Artifact storage, versioning, and asset manifests — canonical registry."""

from __future__ import annotations

from film_pipeline.artifacts.envelope import (
    ArtifactCurrentMeta,
    ArtifactEnvelope,
    ChecksumMismatchError,
    MutableRevisionMismatchError,
    SchemaTooNewError,
    payload_checksum,
)
from film_pipeline.artifacts.manifest import (
    AssetEntry,
    AssetManifest,
    read_manifest,
    write_manifest,
)
from film_pipeline.artifacts.registry import (
    REGISTRY,
    ArtifactKindRegistry,
    KindNotRegisteredError,
)
from film_pipeline.artifacts.serialization import NonFiniteNumberError
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.storage.contract import KindSpec
from film_pipeline.storage.paths import (
    media_scene_dir,
    phase_dir,
    project_dir,
)

__all__ = [
    "REGISTRY",
    "ArtifactCurrentMeta",
    "ArtifactEnvelope",
    "ArtifactKindRegistry",
    "ArtifactStore",
    "AssetEntry",
    "AssetManifest",
    "ChecksumMismatchError",
    "KindNotRegisteredError",
    "KindSpec",
    "MutableRevisionMismatchError",
    "NonFiniteNumberError",
    "SchemaTooNewError",
    "media_scene_dir",
    "payload_checksum",
    "phase_dir",
    "project_dir",
    "read_manifest",
    "write_manifest",
]
