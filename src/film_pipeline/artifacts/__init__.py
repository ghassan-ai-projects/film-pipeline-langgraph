"""Compatibility aliases for the artifact storage owner.

Artifact storage now lives in :mod:`film_pipeline.storage`. This package keeps
the historical import paths working while consumers migrate; every name below
is the storage package's own object, never a copy.
"""

from __future__ import annotations

from film_pipeline.storage.contract import KindSpec as KindSpec
from film_pipeline.storage.envelope import (
    ArtifactCurrentMeta as ArtifactCurrentMeta,
)
from film_pipeline.storage.envelope import (
    ArtifactEnvelope as ArtifactEnvelope,
)
from film_pipeline.storage.envelope import (
    ChecksumMismatchError as ChecksumMismatchError,
)
from film_pipeline.storage.envelope import (
    MutableRevisionMismatchError as MutableRevisionMismatchError,
)
from film_pipeline.storage.envelope import SchemaTooNewError as SchemaTooNewError
from film_pipeline.storage.envelope import payload_checksum as payload_checksum
from film_pipeline.storage.manifest import AssetEntry as AssetEntry
from film_pipeline.storage.manifest import AssetManifest as AssetManifest
from film_pipeline.storage.manifest import read_manifest as read_manifest
from film_pipeline.storage.manifest import write_manifest as write_manifest
from film_pipeline.storage.paths import media_scene_dir as media_scene_dir
from film_pipeline.storage.paths import phase_dir as phase_dir
from film_pipeline.storage.paths import project_dir as project_dir
from film_pipeline.storage.registry import REGISTRY as REGISTRY
from film_pipeline.storage.registry import (
    ArtifactKindRegistry as ArtifactKindRegistry,
)
from film_pipeline.storage.registry import (
    KindNotRegisteredError as KindNotRegisteredError,
)
from film_pipeline.storage.serialization import (
    NonFiniteNumberError as NonFiniteNumberError,
)
from film_pipeline.storage.store import ArtifactStore as ArtifactStore

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
