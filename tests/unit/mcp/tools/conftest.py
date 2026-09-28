"""Shared fixtures for tests/unit/mcp/tools.

Tests in this package rely on the module-level runtime singleton in
``film_pipeline.studio.runtime`` (``get_runtime`` / ``reset_runtime``). Other
test modules in the suite (e.g. ``tests/unit/test_mcp.py``) call
``reset_runtime("real")`` without restoring "mock" mode afterwards, which
leaves the global ``_RUNTIME_MODE_OVERRIDE`` set for any test that runs
later in the same process/worker. To keep this package's tests independent
of execution order, force the runtime back to mock mode before and after
every test here.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Iterator
from typing import Any, cast

import pytest

from film_pipeline.studio.runtime import reset_runtime


@pytest.fixture(autouse=True)
def _reset_runtime_to_mock() -> Iterator[None]:
    reset_runtime("mock")
    # Rebind the package-level accessor so any previous monkeypatch is undone.
    import film_pipeline.mcp.tools as tools_pkg
    from film_pipeline.studio.runtime import get_runtime

    tools_pkg.get_runtime = get_runtime
    try:
        yield
    finally:
        reset_runtime("mock")
        tools_pkg.get_runtime = get_runtime


@pytest.fixture
def call_tool() -> Iterator[Callable[..., Any]]:
    """Call a tool handler the way dispatch does, without the global singleton.

    Doc 01's slice 2 replaces "handler fetches its own runtime via
    ``tools_pkg.get_runtime()``" with "dispatch passes a `ToolContext`". This
    fixture builds that context from a real `StudioRuntime` the test owns, so a
    migrated handler is exercised through its real calling convention rather than
    by patching a package global. The 61 monkeypatch sites this replaces were the
    symptom: every test had to know *how* the handler looked its runtime up.

    The context is rebuilt per call, so a handler that mutates runtime state is
    observed on the same runtime the assertions read.
    """

    def _call(
        handler: Callable[..., Any],
        args: dict[str, Any] | None = None,
        *,
        project_id: str | None = None,
    ) -> Any:
        from film_pipeline.mcp.envelope import new_envelope
        from film_pipeline.mcp.tools.context import ToolContext
        from film_pipeline.studio.runtime import get_runtime

        envelope = new_envelope(project_ref=project_id)
        context = ToolContext(
            runtime=get_runtime(),
            project_id=project_id,
            envelope=envelope,
        )
        # Both handler shapes are legal while doc 01's migration is in flight;
        # the same signature check dispatch uses picks which call this is. A
        # legacy handler still gets `"_envelope"`, exactly as dispatch passes it.
        from film_pipeline.mcp.server import _accepts_context

        any_handler = cast("Any", handler)
        if _accepts_context(handler):
            result = any_handler(context, args or {})
        else:
            result = any_handler({**(args or {}), "_envelope": envelope})
        if inspect.isawaitable(result):
            awaited: Any = asyncio.run(cast("Any", result))
            return awaited
        return result

    yield _call
