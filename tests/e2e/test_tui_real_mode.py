"""End-to-end TUI flow using real runtime mode with mocked provider adapters.

Uses real LLM agents (OpenRouter/Gemini) for scripts, prompts, and upstream
artifacts, but swaps the video/image provider adapters to zero-cost mocks so no
paid clips or reference images are generated. This verifies real-mode agent
wiring, provider registry state, and all cockpit views without media generation
costs.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from textual.widgets import TabbedContent

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.app.services.models import ProjectCreateRequest
from film_pipeline.app.services.operator import OperatorService
from film_pipeline.graph.services import GraphServices
from film_pipeline.providers import credentials, factory
from film_pipeline.providers.mock_image_provider import MockImageProvider
from film_pipeline.providers.mock_provider import MockVideoProvider
from film_pipeline.schemas.registries.provider_registry import (
    CostProfile,
    ProviderCapabilities,
    ProviderRegistryEntry,
)
from film_pipeline.tui.app import FilmCockpitApp
from film_pipeline.tui.gateways.inprocess import InProcessStudioGateway


def _mock_entry(provider_id: str, provider_type: str, models: list[str]) -> ProviderRegistryEntry:
    return ProviderRegistryEntry(
        provider_id=provider_id,
        provider_type=provider_type,
        models=models,
        capabilities=ProviderCapabilities(
            text_to_video=provider_type == "video",
            text_to_image=provider_type == "image",
            return_last_frame=True,
            max_duration_seconds=15,
            aspect_ratios=["16:9"],
        ),
        cost_profile=CostProfile(unit="second", estimated_rate_usd=0.0),
    )


def _mock_build_provider_adapter(
    provider_id: str,
    *,
    provider_type: str = "video",
    models: list[str] | None = None,
) -> object:
    if provider_type == "image" or provider_id in {"gemini-imagen-4", "imagen-4"}:
        return MockImageProvider(
            entry=_mock_entry(
                provider_id, "image", list(models or ["imagen-4.0-fast-generate-001"])
            )
        )
    return MockVideoProvider(
        entry=_mock_entry(provider_id, "video", list(models or ["bytedance/seedance-2.0"]))
    )


@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("FILM_PIPELINE_RUN_REAL_LLM") != "1",
    reason="Set FILM_PIPELINE_RUN_REAL_LLM=1 to run real LLM agents (slow, costs tokens)",
)
@pytest.mark.skipif(
    not credentials.is_configured("seedance-openrouter"),
    reason="OPENROUTER_API_KEY not configured",
)
def test_tui_real_mode_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Create a film with real agents, mock providers, and inspect all views."""

    async def run() -> None:
        runtime_root = tmp_path / "runtime"
        services = GraphServices.for_real_runtime(str(runtime_root / "projects"))
        runtime = StudioRuntime(
            runtime_root=runtime_root,
            server_mode="real",
            services=services,
        )
        monkeypatch.setattr(credentials, "is_configured", lambda _pid: True)
        monkeypatch.setattr(factory, "build_provider_adapter", _mock_build_provider_adapter)
        runtime.seed_default_provider_health()

        service = OperatorService(runtime=runtime)
        service.create_project(
            ProjectCreateRequest(
                project_id="tui-real-flow",
                title="TUI Real Mode Flow",
                idea="A 20-second demo about a lost key found by moonlight.",
                runtime_mode="real",
            )
        )
        service.set_active_project("tui-real-flow")

        gateway = InProcessStudioGateway(service)
        app = FilmCockpitApp(gateway=gateway)

        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            for _ in range(120):
                if app.active_project_id == "tui-real-flow":
                    break
                await pilot.pause()
            assert app.active_project_id == "tui-real-flow"

            phase_history: list[str] = []
            for _ in range(200):
                snapshot = app.snapshot
                if snapshot is None:
                    await pilot.pause()
                    continue
                dashboard = snapshot.dashboard
                assert dashboard is not None
                if dashboard.current_phase in {"delivery", "complete"}:
                    break
                if dashboard.current_phase not in phase_history:
                    phase_history.append(dashboard.current_phase)
                if "approve_phase" in dashboard.eligible_actions:
                    app.action_approve_phase()
                    await pilot.pause()
                    app.action_approve_phase()
                    for _ in range(300):
                        if app.busy_label == "":
                            break
                        await pilot.pause()
                elif dashboard.current_phase == "generation":
                    app.action_run_generation()
                    for _ in range(300):
                        if app.busy_label == "":
                            break
                        await pilot.pause()
                else:
                    await pilot.pause()

            assert app.snapshot is not None
            dashboard = app.snapshot.dashboard
            assert dashboard is not None
            assert dashboard.current_phase in {"generation", "qc", "post", "delivery", "complete"}
            assert dashboard.runtime_mode == "real"

            # Real-mode provider adapters should be visible in the Ops tab.
            provider_ids = {p["provider_id"] for p in app.snapshot.providers}
            assert "seedance-openrouter" in provider_ids

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

            assert len(app.snapshot.assets) > 0
            assert dashboard.status in {"awaiting_review", "complete"}

    asyncio.run(run())
