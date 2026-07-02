"""End-to-end TUI flow using the in-process gateway in mock mode.

Drives the cockpit from project creation through delivery, exercising every
workspace tab and the generation batch along the way.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from textual.widgets import TabbedContent

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.app.services.operator import OperatorService
from film_pipeline.tui.app import FilmCockpitApp
from film_pipeline.tui.gateways.inprocess import InProcessStudioGateway


@pytest.mark.e2e
def test_tui_full_mock_flow(tmp_path: Path) -> None:
    """Create a film, approve every phase, generate clips, and reach delivery."""

    async def run() -> None:
        runtime_root = tmp_path / "runtime"
        runtime = StudioRuntime(runtime_root=runtime_root, server_mode="mock")
        runtime.seed_default_provider_health()
        service = OperatorService(runtime=runtime)
        gateway = InProcessStudioGateway(service)
        app = FilmCockpitApp(gateway=gateway)

        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()

            # Create project via command palette
            await pilot.press("slash")
            await pilot.pause()
            create_cmd = (
                "create tui-mock-flow | TUI Mock Flow | A one-minute demo about a lost message."
            )
            await pilot.press(*list(create_cmd))
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            # Wait for background creation worker
            for _ in range(60):
                if app.busy_label == "":
                    break
                await pilot.pause()
            assert app.active_project_id == "tui-mock-flow"

            # Drive pipeline to completion
            phase_history: list[str] = []
            for _ in range(80):
                snapshot = app.snapshot
                if snapshot is None:
                    await pilot.pause()
                    continue
                dashboard = snapshot.dashboard
                assert dashboard is not None
                if dashboard.current_phase == "complete":
                    break
                if dashboard.current_phase not in phase_history:
                    phase_history.append(dashboard.current_phase)
                if "approve_phase" in dashboard.eligible_actions:
                    app.action_approve_phase()
                    await pilot.pause()
                    # Confirm
                    app.action_approve_phase()
                    for _ in range(60):
                        if app.busy_label == "":
                            break
                        await pilot.pause()
                elif dashboard.current_phase == "generation":
                    app.action_run_generation()
                    for _ in range(180):
                        if app.busy_label == "":
                            break
                        await pilot.pause()
                else:
                    await pilot.pause()

            assert app.snapshot is not None
            dashboard = app.snapshot.dashboard
            assert dashboard is not None
            assert dashboard.current_phase in {"delivery", "complete"}
            assert dashboard.status == "complete"

            # Visit every workspace tab
            tabs = app.query_one("#tabs", TabbedContent)
            for tab_id in (
                "review",
                "generate",
                "scenes",
                "assets",
                "matrix",
                "guide",
                "validation",
                "ops",
            ):
                app.action_open_tab(tab_id)
                await pilot.pause()
                assert tabs.active == tab_id

            # Assets were generated
            assert len(app.snapshot.assets) > 0
            # Checkpoints and audit events accumulated
            assert len(app.snapshot.checkpoints) >= 2
            assert len(app.snapshot.audit_events) >= 2

    asyncio.run(run())
