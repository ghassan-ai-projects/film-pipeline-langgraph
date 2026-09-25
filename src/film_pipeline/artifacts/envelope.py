"""Compatibility aliases for :mod:`film_pipeline.storage.envelope`."""

from __future__ import annotations

from film_pipeline.storage.envelope import ArtifactCurrentMeta as ArtifactCurrentMeta
from film_pipeline.storage.envelope import ArtifactEnvelope as ArtifactEnvelope
from film_pipeline.storage.envelope import ArtifactIndex as ArtifactIndex
from film_pipeline.storage.envelope import ArtifactIndexEntry as ArtifactIndexEntry
from film_pipeline.storage.envelope import ChecksumMismatchError as ChecksumMismatchError
from film_pipeline.storage.envelope import (
    MutableRevisionMismatchError as MutableRevisionMismatchError,
)
from film_pipeline.storage.envelope import SchemaTooNewError as SchemaTooNewError
from film_pipeline.storage.envelope import payload_checksum as payload_checksum

__all__ = [
    "ArtifactCurrentMeta",
    "ArtifactEnvelope",
    "ArtifactIndex",
    "ArtifactIndexEntry",
    "ChecksumMismatchError",
    "MutableRevisionMismatchError",
    "SchemaTooNewError",
    "payload_checksum",
]
