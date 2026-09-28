"""The headless driver must reach the domain through MCP dispatch, not past it.

## What these tests pin

`docs/modularity-improvements/01` found two ways to run an MCP tool handler and
only one of them applies the tool contract:

- **Path A — `MCPServer.call`** resolves `project_ref`, then runs
  `_check_confirmation` (the 9 `confirm=True` tools), `_check_active_project` (the
  44 `active_project=True` tools), and maps service errors to typed responses.
- **Path B — call the handler function directly.** `HeadlessDriver._call_tool`
  did `importlib.import_module("film_pipeline.mcp.tools")` + `getattr`, so none of
  those three checks ran.

The reproduced consequence (`docs/modularity-improvements/probe_dispatch_paths.py`):

```text
A  approve_phase, unconfirmed -> confirmation_required
B  approve_phase, unconfirmed -> ok=True  phase intake -> constitution
```

Through Path B a **human gate is approved with no `confirmed` flag**. The shipped
CLI always passes `confirmed=True`, so this is not a live bypass today — it is a
gate whose enforcement depends on every caller remembering to use the other path,
which is the shape that stops being true the first time someone adds a caller.

## Reading a failure

Both tests fail on the pre-fix tree, one per check:

- `test_driver_enforces_the_active_project_precondition` — today raises
  `ProjectNotFoundError` from inside the handler instead of returning
  `NO_ACTIVE_PROJECT`.
- `test_driver_enforces_confirmation_on_a_human_gate` — today advances the phase.

They are written against the driver's *public* surface (`_call_tool`), because
that is the seam 01 replaces.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from film_pipeline.cli.driver import HeadlessDriver
from film_pipeline.mcp.errors import MCPErrorCode


@pytest.fixture
def driver(tmp_path: Path) -> HeadlessDriver:
    """A mock-mode driver with a runtime installed, and no active project."""
    rt = HeadlessDriver.setup_runtime("mock", tmp_path / "runtime")
    return HeadlessDriver(rt, "dispatch-test")


def test_driver_enforces_the_active_project_precondition(driver: HeadlessDriver) -> None:
    """A `requires_active_project` tool with no project yields a typed error.

    Through dispatch this is `NO_ACTIVE_PROJECT`. Through the direct path the
    handler's own `require_project_id` raised `ProjectNotFoundError` — an
    exception escaping the tool boundary, where the contract promises a typed
    response. The difference is not cosmetic: a caller cannot branch on a raise
    the way it branches on `error.code`.
    """
    result = asyncio.run(driver._call_tool("get_blockers"))

    assert result.get("ok") is not True, (
        "get_blockers succeeded with no active project. The driver is bypassing "
        "the dispatch-level active-project precondition."
    )
    assert result.get("error") == MCPErrorCode.NO_ACTIVE_PROJECT, (
        f"expected the typed NO_ACTIVE_PROJECT error, got {result!r}. A raise or "
        "an ok=True both mean the driver is not going through MCPServer.call."
    )


def test_driver_enforces_confirmation_on_a_human_gate(driver: HeadlessDriver) -> None:
    """`approve_phase` without `confirmed` is refused, not silently applied.

    This is the finding's sharpest form: on the direct path the call *succeeded*
    and advanced the phase from intake to constitution, with no confirmation.
    """
    asyncio.run(
        driver._call_tool(
            "create_film_project",
            project_id="dispatch-test",
            title="Dispatch Test",
            slug="dispatch-test",
            runtime_mode="mock",
        )
    )
    asyncio.run(driver._call_tool("set_active_project", project_ref="dispatch-test"))
    asyncio.run(
        driver._call_tool("submit_idea", idea="A lighthouse keeper finds a door in the sea.")
    )

    before = driver.rt.get_project("dispatch-test")["current_phase"]  # type: ignore[index]
    result = asyncio.run(driver._call_tool("approve_phase"))
    after = driver.rt.get_project("dispatch-test")["current_phase"]  # type: ignore[index]

    assert result.get("error") == MCPErrorCode.CONFIRMATION_REQUIRED, (
        f"approve_phase without `confirmed` was not refused: {result!r}. The "
        "confirmation gate is enforced at dispatch, so a driver that skips "
        "dispatch skips the gate."
    )
    assert after == before, f"a human gate advanced without confirmation: phase {before} -> {after}"
