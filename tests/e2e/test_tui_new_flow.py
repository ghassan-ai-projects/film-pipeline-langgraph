"""End-to-end flow for the redesigned Film Studio TUI in mock mode.

Drives FilmStudioApp from project creation through delivery using the
in-process gateway, exercising create, approve, validate, generate, and
view assets/scripts/prompts.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.app.services.models import ProjectCreateRequest
from film_pipeline.app.services.operator import OperatorService
from film_pipeline.tui.app import FilmStudioApp
from film_pipeline.tui.gateways.inprocess import InProcessStudioGateway
from film_pipeline.tui.screens.studio import StudioScreen


@pytest.mark.e2e
def test_tui_new_full_mock_flow(tmp_path: Path) -> None:
    """Create a film in the redesigned TUI and drive it to delivery."""

    async def run() -> None:
        runtime_root = tmp_path / "runtime"
        runtime = StudioRuntime(runtime_root=runtime_root, server_mode="mock")
        runtime.seed_default_provider_health()
        service = OperatorService(runtime=runtime)
        gateway = InProcessStudioGateway(service)
        app = FilmStudioApp(gateway=gateway)

        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()

            # Create project via the command palette.
            await pilot.press("slash")
            await pilot.pause()
            create_cmd = (
                "create tui-new-flow | TUI New Flow | A one-minute demo about a lost message."
            )
            await pilot.press(*list(create_cmd))
            await pilot.pause()
            await pilot.press("enter")

            # Wait for background creation and navigation to the studio.
            for _ in range(120):
                await pilot.pause()
                if isinstance(app.screen, StudioScreen):
                    break
            assert isinstance(app.screen, StudioScreen), f"still on {app.screen}"
            assert app.active_project_id == "tui-new-flow"

            phase_history: list[str] = []
            last_phase = ""
            for _ in range(200):
                snapshot = app.state.snapshot
                if snapshot is None or snapshot.dashboard is None:
                    await pilot.pause()
                    continue

                dashboard = snapshot.dashboard
                if dashboard.current_phase in {"delivery", "complete"} and (
                    dashboard.status == "complete"
                ):
                    break
                if dashboard.current_phase != last_phase:
                    phase_history.append(dashboard.current_phase)
                    last_phase = dashboard.current_phase

                if dashboard.current_phase == "generation":
                    gen_snapshot = app.state.snapshot
                    generation = gen_snapshot.generation if gen_snapshot else None
                    if (
                        generation is not None
                        and generation.completed > 0
                        and "approve_phase" in dashboard.eligible_actions
                    ):
                        app._run_command("approve")
                    elif generation is None or generation.running == 0:
                        app._run_command("generate")
                    # Wait for the batch or approval to change state.
                    for _ in range(60):
                        await pilot.pause(delay=0.5)
                        new_snapshot = app.state.snapshot
                        if (
                            new_snapshot
                            and new_snapshot.dashboard
                            and new_snapshot.dashboard.current_phase != "generation"
                        ):
                            break
                elif dashboard.has_blockers or (
                    snapshot.validation and snapshot.validation.blocking_issues
                ):
                    app._run_command("validate")
                elif "approve_phase" in dashboard.eligible_actions:
                    app._run_command("approve")

                # Wait for the action to take effect.
                for _ in range(30):
                    await pilot.pause()
                    new_snapshot = app.state.snapshot
                    if (
                        new_snapshot
                        and new_snapshot.dashboard
                        and new_snapshot.dashboard.current_phase != dashboard.current_phase
                    ):
                        break
                    if (
                        new_snapshot
                        and new_snapshot.dashboard
                        and new_snapshot.dashboard.eligible_actions != dashboard.eligible_actions
                    ):
                        break

            final_snapshot = app.state.snapshot
            assert final_snapshot is not None
            assert final_snapshot.dashboard is not None
            dashboard = final_snapshot.dashboard
            assert dashboard.current_phase in {"delivery", "complete"}
            assert dashboard.status == "complete"
            assert "generation" in phase_history

            # Open asset viewer via the command palette.
            app._run_command("assets")
            for _ in range(20):
                await pilot.pause()

            # Return home.
            await app.action_back()
            for _ in range(10):
                await pilot.pause()

            # Final state assertions.
            assert len(final_snapshot.assets) > 0
            assert any(asset.get("kind") == "generated_clip" for asset in final_snapshot.assets)
            assert len(final_snapshot.checkpoints) >= 2
            assert len(final_snapshot.audit_events) >= 2

    asyncio.run(run())


@pytest.mark.e2e
def test_tui_new_text_only_full_flow_does_not_create_media(tmp_path: Path) -> None:
    """Drive a text-only project through delivery without generated clips or frames."""

    async def run() -> None:
        runtime_root = tmp_path / "runtime"
        runtime = StudioRuntime(runtime_root=runtime_root, server_mode="mock")
        runtime.seed_default_provider_health()
        service = OperatorService(runtime=runtime)
        gateway = InProcessStudioGateway(service)
        app = FilmStudioApp(gateway=gateway)

        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            app.create_project(
                ProjectCreateRequest(
                    project_id="tui-text-only-flow",
                    title="TUI Text Only Flow",
                    slug="tui-text-only-flow",
                    idea="A one-minute demo reviewed without rendered media.",
                    runtime_mode="mock",
                    workflow_mode="manual",
                    project_kind="production",
                    generation_policy="text_only",
                )
            )

            for _ in range(120):
                await pilot.pause()
                if isinstance(app.screen, StudioScreen):
                    break
            assert isinstance(app.screen, StudioScreen), f"still on {app.screen}"

            saw_generation = False
            for _ in range(220):
                snapshot = app.state.snapshot
                if snapshot is None or snapshot.dashboard is None:
                    await pilot.pause()
                    continue

                dashboard = snapshot.dashboard
                if (
                    dashboard.current_phase in {"delivery", "complete"}
                    and dashboard.status == "complete"
                ):
                    break

                if dashboard.current_phase == "generation":
                    saw_generation = True
                    assert dashboard.generation_policy == "text_only"
                    assert not any(
                        asset.get("kind") in {"generated_clip", "last_frame", "mid_frame"}
                        for asset in snapshot.assets
                    )
                    generation = snapshot.generation
                    if generation is not None and generation.completed > 0:
                        assert "approve_phase" in dashboard.eligible_actions
                        app._run_command("approve")
                    else:
                        app._run_command("generate")
                elif dashboard.has_blockers or (
                    snapshot.validation and snapshot.validation.blocking_issues
                ):
                    app._run_command("validate")
                elif "approve_phase" in dashboard.eligible_actions:
                    app._run_command("approve")

                for _ in range(40):
                    await pilot.pause()
                    new_snapshot = app.state.snapshot
                    if (
                        new_snapshot
                        and new_snapshot.dashboard
                        and new_snapshot.dashboard.current_phase != dashboard.current_phase
                    ):
                        break
                    if (
                        new_snapshot
                        and new_snapshot.dashboard
                        and new_snapshot.dashboard.eligible_actions != dashboard.eligible_actions
                    ):
                        break

            final_snapshot = app.state.snapshot
            assert final_snapshot is not None
            assert final_snapshot.dashboard is not None
            assert saw_generation
            assert final_snapshot.dashboard.current_phase in {"delivery", "complete"}
            assert final_snapshot.dashboard.status == "complete"
            assert any(asset.get("kind") == "text_only_delivery" for asset in final_snapshot.assets)
            assert not any(
                asset.get("kind") in {"generated_clip", "last_frame", "mid_frame"}
                for asset in final_snapshot.assets
            )

    asyncio.run(run())
