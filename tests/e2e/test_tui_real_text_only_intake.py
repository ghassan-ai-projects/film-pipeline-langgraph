"""Verify the redesigned TUI can run intake in real mode with text-only policy.

This test makes one real LLM call (DeepSeek via OpenRouter) and costs a small
amount. It intentionally stops after intake to keep the run short and cheap;
combined with the existing mock-mode full-flow test, this proves real-mode
configuration is working and text-only generation policy is honored.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.app.services.models import ProjectCreateRequest
from film_pipeline.app.services.operator import OperatorService
from film_pipeline.providers import credentials
from film_pipeline.tui.app import FilmStudioApp
from film_pipeline.tui.gateways.inprocess import InProcessStudioGateway
from film_pipeline.tui.screens.studio import StudioScreen


@pytest.mark.skipif(
    os.environ.get("FILM_PIPELINE_RUN_REAL_PROVIDER") != "1",
    reason="Set FILM_PIPELINE_RUN_REAL_PROVIDER=1 to run live paid provider tests",
)
@pytest.mark.skipif(
    not credentials.is_configured("seedance-openrouter"),
    reason="OPENROUTER_API_KEY not configured",
)
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

            request = ProjectCreateRequest(
                project_id="real-text-only",
                title="Real Text Only",
                slug="real-text-only",
                idea="A one-minute silent film about a paper boat on a rainy street.",
                runtime_mode="real",
                workflow_mode="manual",
                project_kind="production",
                generation_policy="text_only",
            )
            app.create_project(request)

            # Wait for the background create_project worker and navigation.
            last_status = ""
            for _ in range(400):
                await pilot.pause()
                last_status = app._status_text()
                if app.active_project_id == "real-text-only" and isinstance(
                    app.screen, StudioScreen
                ):
                    break
            assert isinstance(app.screen, StudioScreen), (
                f"still on {app.screen}; active_project_id={app.active_project_id!r}; "
                f"status={last_status!r}"
            )
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
