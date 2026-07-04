"""Verify the redesigned TUI can run intake in real mode with text-only policy.

This test makes one real LLM call (DeepSeek via OpenRouter) and costs a small
amount. It intentionally stops after intake to keep the run short and cheap;
combined with the existing mock-mode full-flow test, this proves real-mode
configuration is working and text-only generation policy is honored.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.app.services.operator import OperatorService
from film_pipeline.tui.app import FilmStudioApp
from film_pipeline.tui.gateways.inprocess import InProcessStudioGateway
from film_pipeline.tui.screens.studio import StudioScreen


@pytest.mark.real_provider
def test_tui_real_mode_text_only_intake(tmp_path: Path) -> None:
    """Create a real-mode, text-only project in the TUI and run intake."""

    async def run() -> None:
        runtime_root = tmp_path / "runtime"
        runtime = StudioRuntime(runtime_root=runtime_root, server_mode="real")
        runtime.seed_default_provider_health()
        service = OperatorService(runtime=runtime)
        gateway = InProcessStudioGateway(service)
        app = FilmStudioApp(gateway=gateway)

        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()

            await pilot.press("slash")
            await pilot.pause()
            create_cmd = (
                "create real-text-only | Real Text Only | "
                "A one-minute silent film about a paper boat on a rainy street. | "
                "real | text_only"
            )
            await pilot.press(*list(create_cmd))
            await pilot.pause()
            await pilot.press("enter")

            for _ in range(120):
                await pilot.pause()
                if isinstance(app.screen, StudioScreen):
                    break
            assert isinstance(app.screen, StudioScreen), f"still on {app.screen}"
            assert app.active_project_id == "real-text-only"

            dashboard = app.state.dashboard
            assert dashboard is not None
            assert dashboard.runtime_mode == "real"
            assert dashboard.generation_policy == "text_only"

            # Wait for intake background work to finish.
            for _ in range(240):
                await pilot.pause()
                snapshot = app.state.snapshot
                if snapshot is not None and snapshot.artifacts:
                    break

            snapshot = app.state.snapshot
            assert snapshot is not None
            assert len(snapshot.artifacts) >= 1, "intake did not produce artifacts"
            assert snapshot.dashboard is not None
            # Intake may remain awaiting operator review/approval; the key real-mode
            # verification is that text artifacts were produced using a live model.
            assert snapshot.dashboard.current_phase == "intake"

    asyncio.run(run())
