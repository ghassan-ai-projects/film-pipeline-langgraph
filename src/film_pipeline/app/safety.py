"""Compatibility aliases for :mod:`film_pipeline.studio.safety`."""

from __future__ import annotations

from film_pipeline.studio.safety import ProductionDataError as ProductionDataError

# Private helpers still reached through this path during migration.
from film_pipeline.studio.safety import _is_under as _is_under
from film_pipeline.studio.safety import _temp_roots as _temp_roots
from film_pipeline.studio.safety import can_delete_project as can_delete_project
from film_pipeline.studio.safety import is_safe_to_delete as is_safe_to_delete
from film_pipeline.studio.safety import move_to_trash as move_to_trash
from film_pipeline.studio.safety import persist_root as persist_root
from film_pipeline.studio.safety import require_safe_to_delete as require_safe_to_delete
from film_pipeline.studio.safety import safe_rmtree as safe_rmtree

__all__ = [
    "ProductionDataError",
    "can_delete_project",
    "is_safe_to_delete",
    "move_to_trash",
    "persist_root",
    "require_safe_to_delete",
    "safe_rmtree",
]
