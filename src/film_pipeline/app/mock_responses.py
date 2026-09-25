"""Compatibility aliases for :mod:`film_pipeline.studio.mock_responses`."""

from __future__ import annotations

# Private helpers still reached through this path during migration.
from film_pipeline.studio.mock_responses import _CAMERA_PROFILES as _CAMERA_PROFILES
from film_pipeline.studio.mock_responses import _DEMO_MOVEMENT_DURATIONS as _DEMO_MOVEMENT_DURATIONS
from film_pipeline.studio.mock_responses import _DEMO_RUNTIME_SECONDS as _DEMO_RUNTIME_SECONDS
from film_pipeline.studio.mock_responses import (
    _SEEDANCE_RATE_USD_PER_SECOND as _SEEDANCE_RATE_USD_PER_SECOND,
)
from film_pipeline.studio.mock_responses import _STORY_FUNCTIONS as _STORY_FUNCTIONS
from film_pipeline.studio.mock_responses import _demo_shot_groups as _demo_shot_groups
from film_pipeline.studio.mock_responses import _demo_shot_rows as _demo_shot_rows
from film_pipeline.studio.mock_responses import default_mock_responses as default_mock_responses

__all__ = [
    "default_mock_responses",
]
