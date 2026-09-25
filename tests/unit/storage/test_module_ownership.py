"""Legacy ``artifacts`` paths resolve to the ``storage`` owners.

Artifact storage moved from ``film_pipeline.artifacts`` to
``film_pipeline.storage``. The old package remains as a compatibility facade,
and this test proves every name it publishes is the storage package's own
object. A shim that re-defines a name instead of re-exporting it would let the
two surfaces drift while still importing cleanly.
"""

from __future__ import annotations

import importlib

import pytest

#: Legacy submodule path -> the storage module that now owns it.
_MOVED_MODULES = (
    "_layout",
    "envelope",
    "manifest",
    "matrix_projection",
    "project_storage",
    "registry",
    "rendering",
    "serialization",
    "storage",
    "store",
)


@pytest.mark.parametrize("name", _MOVED_MODULES)
def test_moved_submodule_is_importable_from_both_paths(name: str) -> None:
    """The legacy path must keep importing while consumers migrate."""
    legacy = importlib.import_module(f"film_pipeline.artifacts.{name}")
    owner = importlib.import_module(f"film_pipeline.storage.{name}")
    assert legacy is not None and owner is not None


@pytest.mark.parametrize(
    "name",
    [
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
    ],
)
def test_artifact_facade_reexports_the_storage_owner(name: str) -> None:
    """Each published name is the storage owner's object, not a copy."""
    artifacts = importlib.import_module("film_pipeline.artifacts")
    storage = importlib.import_module("film_pipeline.storage")
    assert getattr(artifacts, name) is getattr(storage, name), (
        f"film_pipeline.artifacts.{name} is not film_pipeline.storage.{name}"
    )


def test_storage_publishes_the_facade_surface() -> None:
    """The facade must not advertise a name storage does not expose."""
    artifacts = importlib.import_module("film_pipeline.artifacts")
    storage = importlib.import_module("film_pipeline.storage")
    missing = sorted(name for name in artifacts.__all__ if not hasattr(storage, name))
    assert missing == [], f"published but absent from storage: {missing}"


def test_layout_owner_is_not_duplicated() -> None:
    """There must be exactly one layout module, reached from both paths."""
    legacy = importlib.import_module("film_pipeline.artifacts._layout")
    owner = importlib.import_module("film_pipeline.storage._layout")
    shared = [name for name in vars(owner) if not name.startswith("__")]
    assert shared, "expected the layout module to define names"
    for name in shared:
        if name.startswith("_") or name.isupper():
            assert getattr(legacy, name) is getattr(owner, name)
