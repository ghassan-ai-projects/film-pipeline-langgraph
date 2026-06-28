"""Shared fixtures for tests/unit/mcp/tools.

Tests in this package rely on the module-level runtime singleton in
``film_pipeline.app.runtime`` (``get_runtime`` / ``reset_runtime``). Other
test modules in the suite (e.g. ``tests/unit/test_mcp.py``) call
``reset_runtime("real")`` without restoring "mock" mode afterwards, which
leaves the global ``_RUNTIME_MODE_OVERRIDE`` set for any test that runs
later in the same process/worker. To keep this package's tests independent
of execution order, force the runtime back to mock mode before and after
every test here.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from film_pipeline.app.runtime import reset_runtime


@pytest.fixture(autouse=True)
def _reset_runtime_to_mock() -> Iterator[None]:
    reset_runtime("mock")
    try:
        yield
    finally:
        reset_runtime("mock")
