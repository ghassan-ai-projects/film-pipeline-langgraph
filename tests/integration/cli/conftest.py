"""Shared fixtures for CLI integration tests."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def isolated_runtime() -> Any:
    """Save and restore the global runtime singleton around the test."""
    import film_pipeline.app.runtime as rt_mod

    previous_runtime = rt_mod._RUNTIME
    previous_override = rt_mod._RUNTIME_MODE_OVERRIDE
    try:
        yield None
    finally:
        rt_mod._RUNTIME = previous_runtime
        rt_mod._RUNTIME_MODE_OVERRIDE = previous_override
