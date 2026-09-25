"""Compatibility aliases for :mod:`film_pipeline.studio.health`."""

from __future__ import annotations

from film_pipeline.studio.health import HealthStatus as HealthStatus

# Private helpers still reached through this path during migration.
from film_pipeline.studio.health import _record_bootstrap_status as _record_bootstrap_status
from film_pipeline.studio.health import _record_kb_status as _record_kb_status
from film_pipeline.studio.health import _record_provider_status as _record_provider_status
from film_pipeline.studio.health import check_readiness as check_readiness

__all__ = [
    "HealthStatus",
    "check_readiness",
]
