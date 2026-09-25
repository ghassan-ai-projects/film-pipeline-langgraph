"""Compatibility aliases for :mod:`film_pipeline.storage.manifest`."""

from __future__ import annotations

from film_pipeline.storage.manifest import AssetEntry as AssetEntry
from film_pipeline.storage.manifest import AssetManifest as AssetManifest
from film_pipeline.storage.manifest import read_manifest as read_manifest
from film_pipeline.storage.manifest import write_manifest as write_manifest

__all__ = [
    "AssetEntry",
    "AssetManifest",
    "read_manifest",
    "write_manifest",
]
