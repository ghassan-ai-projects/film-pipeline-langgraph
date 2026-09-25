"""Compatibility aliases for :mod:`film_pipeline.studio.smoke`."""

from __future__ import annotations

from film_pipeline.studio.smoke import ALL_CHECKS as ALL_CHECKS
from film_pipeline.studio.smoke import check_agent_registry as check_agent_registry
from film_pipeline.studio.smoke import check_config_loads as check_config_loads
from film_pipeline.studio.smoke import check_graph_compiles as check_graph_compiles
from film_pipeline.studio.smoke import check_kb_manifest as check_kb_manifest
from film_pipeline.studio.smoke import check_validator_registry as check_validator_registry
from film_pipeline.studio.smoke import run_smoke_checks as run_smoke_checks

__all__ = [
    "ALL_CHECKS",
    "check_agent_registry",
    "check_config_loads",
    "check_graph_compiles",
    "check_kb_manifest",
    "check_validator_registry",
    "run_smoke_checks",
]
