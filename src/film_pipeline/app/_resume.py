"""Compatibility aliases for :mod:`film_pipeline.studio._resume`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.studio._resume import _approval_made_progress as _approval_made_progress
from film_pipeline.studio._resume import _build_resume_payload as _build_resume_payload
from film_pipeline.studio._resume import (
    _has_stale_generation_request_blocker as _has_stale_generation_request_blocker,
)
from film_pipeline.studio._resume import (
    _preserve_external_generation_requests as _preserve_external_generation_requests,
)
from film_pipeline.studio._resume import (
    _strip_stale_generation_request_blockers as _strip_stale_generation_request_blockers,
)

__all__ = []
