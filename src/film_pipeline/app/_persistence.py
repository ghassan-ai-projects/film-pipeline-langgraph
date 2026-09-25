"""Compatibility aliases for :mod:`film_pipeline.studio._persistence`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.studio._persistence import _adopt_discovered_project as _adopt_discovered_project
from film_pipeline.studio._persistence import _discovered_project_state as _discovered_project_state
from film_pipeline.studio._persistence import _logger as _logger
from film_pipeline.studio._persistence import _restore_audit_events as _restore_audit_events
from film_pipeline.studio._persistence import _restore_checkpoints as _restore_checkpoints
from film_pipeline.studio._persistence import _restore_state_project as _restore_state_project
from film_pipeline.studio._persistence import _stringified as _stringified
from film_pipeline.studio._persistence import artifact_discovery_roots as artifact_discovery_roots
from film_pipeline.studio._persistence import artifact_root as artifact_root
from film_pipeline.studio._persistence import checkpoint_manager_for as checkpoint_manager_for
from film_pipeline.studio._persistence import configured_runtime_root as configured_runtime_root
from film_pipeline.studio._persistence import load_persisted_projects as load_persisted_projects
from film_pipeline.studio._persistence import persist_audit_events as persist_audit_events
from film_pipeline.studio._persistence import persist_checkpoints as persist_checkpoints
from film_pipeline.studio._persistence import persist_project_state as persist_project_state
from film_pipeline.studio._persistence import storage_for as storage_for
from film_pipeline.studio._persistence import use_persistent_runtime as use_persistent_runtime

__all__ = [
    "artifact_discovery_roots",
    "artifact_root",
    "checkpoint_manager_for",
    "configured_runtime_root",
    "load_persisted_projects",
    "persist_audit_events",
    "persist_checkpoints",
    "persist_project_state",
    "storage_for",
    "use_persistent_runtime",
]
