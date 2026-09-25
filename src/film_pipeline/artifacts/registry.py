"""Compatibility aliases for :mod:`film_pipeline.storage.registry`."""

from __future__ import annotations

from film_pipeline.storage.registry import MIGRATIONS as MIGRATIONS
from film_pipeline.storage.registry import REGISTRY as REGISTRY
from film_pipeline.storage.registry import ArtifactKindRegistry as ArtifactKindRegistry
from film_pipeline.storage.registry import KindNotRegisteredError as KindNotRegisteredError
from film_pipeline.storage.registry import Migration as Migration

# Private helpers still reached through this path during migration.
from film_pipeline.storage.registry import _kind_slug as _kind_slug
from film_pipeline.storage.registry import _register_defaults as _register_defaults
from film_pipeline.storage.registry import _spec as _spec
from film_pipeline.storage.registry import migrate_payload as migrate_payload
from film_pipeline.storage.registry import register_migration as register_migration

__all__ = [
    "MIGRATIONS",
    "REGISTRY",
    "ArtifactKindRegistry",
    "KindNotRegisteredError",
    "Migration",
    "migrate_payload",
    "register_migration",
]
