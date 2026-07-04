"""Manual real-mode TUI end-to-end test.

**NOT in CI.** Gated behind ``RUN_REAL_TUI_E2E=1`` and requires
``OPENROUTER_API_KEY`` in the environment.

Usage::

    RUN_REAL_TUI_E2E=1 OPENROUTER_API_KEY=sk-or-v1-... \\
        pytest tests/e2e/test_real_tui_e2e.py -v -s

Cost: ~2 short LLM calls (intake + constitution).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any

import pytest
from textual.widgets import Input, Select, TextArea

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.app.services.operator import OperatorService
from film_pipeline.tui.app import FilmStudioApp
from film_pipeline.tui.gateways.inprocess import InProcessStudioGateway
from film_pipeline.tui.screens.studio import StudioScreen

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_REAL_TUI_E2E") or not os.getenv("OPENROUTER_API_KEY"),
    reason="RUN_REAL_TUI_E2E and OPENROUTER_API_KEY required",
)


@pytest.mark.e2e
def test_real_tui_create_project_and_approve_intake(tmp_path: Path) -> None:
    """Drive the TUI to create a real-mode project, run intake, and approve it."""
    asyncio.run(_run_real_tui_flow(tmp_path))


async def _run_real_tui_flow(tmp_path: Path) -> None:
    project_id = f"real-tui-{uuid.uuid4().hex[:8]}"
    runtime = StudioRuntime(server_mode="real", runtime_root=tmp_path / "runtime")
    assert runtime.services is not None
    runtime.services.artifact_store._root = tmp_path / "projects"

    service = OperatorService(runtime=runtime)
    gateway = InProcessStudioGateway(service=service)
    app = FilmStudioApp(gateway=gateway)

    async with app.run_test() as pilot:
        await pilot.pause()

        # Open the new-project form.
        await pilot.press("n")
        await pilot.pause()

        # Fill the form.  Values are the option values, not the labels.
        app.query_one("#pf_id", Input).value = project_id
        app.query_one("#pf_title", Input).value = "Real TUI Lighthouse Test"
        app.query_one("#pf_idea", TextArea).text = (
            "A short documentary about a lighthouse keeper in Nova Scotia "
            "who discovers a message in a bottle. Tone: melancholic but hopeful. "
            "Target: 4 minutes."
        )
        app.query_one("#pf_runtime", Select).value = "real"
        app.query_one("#pf_provider", Select).value = "local-real-provider"

        # Create the project and run intake.  This blocks until the graph step
        # returns from the real provider.
        await asyncio.wait_for(pilot.click("#pf_create"), timeout=120)
        await pilot.pause()

        assert isinstance(app.screen, StudioScreen)
        dashboard = app.state.dashboard
        assert dashboard is not None
        assert dashboard.project_id == project_id
        assert dashboard.current_phase == "intake"
        assert "approve_phase" in dashboard.eligible_actions

        # Approve intake via the command palette.  This runs the next graph
        # step against the real provider.
        await pilot.press("/")
        await pilot.pause()
        await pilot.press("a", "p", "p", "r", "o", "v", "e")
        await asyncio.wait_for(pilot.press("enter"), timeout=120)
        await pilot.pause()

        dashboard = app.state.dashboard
        assert dashboard is not None
        assert dashboard.current_phase == "constitution"
        assert "approve_phase" in dashboard.eligible_actions

        # Sanity-check that the constitution artifact was actually written.
        state: dict[str, Any] = runtime.get_project(project_id) or {}
        assert state.get("constitution_ref"), (
            f"constitution_ref missing; keys: {sorted(state.keys())}"
        )
