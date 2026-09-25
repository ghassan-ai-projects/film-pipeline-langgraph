"""Artifact storage: canonical layout, versioning, and the artifact registry.

This package owns artifact identity and the on-disk representation. Consumers
import the concrete owners directly (``storage.store``, ``storage.manifests``)
or the small set of names published here; the layout vocabulary lives in
``storage.paths`` and the identity rules in ``storage.contract``.
"""

from film_pipeline.storage.contract import (
    ARTIFACT_ID_PATTERN,
    KindSpec,
    Renderer,
    sanitize_artifact_id,
    validate_artifact_id,
)
from film_pipeline.storage.envelope import (
    ArtifactCurrentMeta,
    ArtifactEnvelope,
    ChecksumMismatchError,
    MutableRevisionMismatchError,
    SchemaTooNewError,
    payload_checksum,
)
from film_pipeline.storage.manifest import (
    AssetEntry,
    AssetManifest,
    read_manifest,
    write_manifest,
)
from film_pipeline.storage.paths import (
    PHASE_DIR_MAP,
    media_scene_dir,
    phase_dir,
    project_dir,
)
from film_pipeline.storage.project_storage import (
    ProjectStorage,
    graph_state_location,
)
from film_pipeline.storage.registry import (
    REGISTRY,
    ArtifactKindRegistry,
    KindNotRegisteredError,
)
from film_pipeline.storage.serialization import NonFiniteNumberError
from film_pipeline.storage.storage import (
    PROFILE_PRODUCTION,
    PROFILE_SANDBOX,
    STORAGE_ROOT_ENV,
    StorageMarker,
    StorageRootError,
    default_checkpoints_root,
    default_run_root,
    default_runtime_root,
    default_storage_root,
    ensure_storage_root,
    init_storage_root,
    resolve_storage_root,
)
from film_pipeline.storage.store import ArtifactStore

__all__ = [
    "ARTIFACT_ID_PATTERN",
    "PHASE_DIR_MAP",
    "PROFILE_PRODUCTION",
    "PROFILE_SANDBOX",
    "REGISTRY",
    "STORAGE_ROOT_ENV",
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
    "ProjectStorage",
    "Renderer",
    "SchemaTooNewError",
    "StorageMarker",
    "StorageRootError",
    "default_checkpoints_root",
    "default_run_root",
    "default_runtime_root",
    "default_storage_root",
    "ensure_storage_root",
    "graph_state_location",
    "init_storage_root",
    "media_scene_dir",
    "payload_checksum",
    "phase_dir",
    "project_dir",
    "read_manifest",
    "resolve_storage_root",
    "sanitize_artifact_id",
    "validate_artifact_id",
    "write_manifest",
]
