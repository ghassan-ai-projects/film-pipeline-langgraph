"""Compatibility aliases for consistency checks, now owned by ``governance``."""

from film_pipeline.governance.consistency import (
    check_phase_consistency as check_phase_consistency,
)
from film_pipeline.governance.consistency import check_staleness as check_staleness

__all__ = ["check_phase_consistency", "check_staleness"]
