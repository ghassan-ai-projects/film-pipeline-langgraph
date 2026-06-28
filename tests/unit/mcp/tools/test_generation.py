"""Unit tests for film_pipeline.mcp.tools.generation (start/promote paths).

The bulk of plan/approve/status/cancel/resume coverage already lives in
``tests/integration/test_generation_mcp.py``; this file focuses on
``start_generation_batch`` and ``promote_test_to_production``, which were
previously untested in isolation.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any, cast
from unittest import mock

import pytest

from film_pipeline.agents.mvp import MVP_AGENTS
from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.runner import PromptRunner
from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.graph.services import GraphServices
from film_pipeline.mcp.tools import (
    approve_generation_spend,
    plan_generation_batch,
    promote_test_to_production,
    start_generation_batch,
)
from film_pipeline.providers.factory import build_provider_adapter


@pytest.fixture
def rt(tmp_path: Path) -> Generator[StudioRuntime, None, None]:
    runner = PromptRunner()
    registry = AgentRegistry()
    registry.register_many(MVP_AGENTS)
    services = GraphServices(
        prompt_runner=runner,
        artifact_store=ArtifactStore(root=tmp_path / "artifacts"),
        agent_registry=registry,
    )
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.services = services
    rt.create_project("gen-start-test", "Gen Start Test")
    rt.set_active("gen-start-test")
    rt.register_provider(
        "mock-video-provider",
        build_provider_adapter("mock-video-provider", provider_type="video", models=["mock-fast"]),
    )
    rt.set_provider_health("mock-video-provider", "healthy")
    with mock.patch("film_pipeline.mcp.tools.get_runtime", return_value=rt):
        yield rt


async def _plan_and_approve(shot_ids: list[str]) -> dict[str, object]:
    await plan_generation_batch(
        {"shot_ids": shot_ids, "provider": "mock-video-provider", "model": "mock-fast"}
    )
    return await approve_generation_spend({})


def test_start_generation_batch_no_submitted_rows(rt: StudioRuntime) -> None:
    import asyncio

    result = asyncio.run(start_generation_batch({}))
    assert result["ok"] is True
    assert result["submitted"] == 0
    assert "Approve spend first" in cast(str, result["message"])


def test_start_generation_batch_unknown_provider(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(
        plan_generation_batch({"shot_ids": ["S001"], "provider": "no-such-provider", "model": "m"})
    )
    asyncio.run(approve_generation_spend({}))

    result = asyncio.run(start_generation_batch({}))
    assert result["ok"] is True
    assert result["failed"] == 1
    assert result["submitted"] == 0
    failures = cast(list[dict[str, Any]], result["failures"])
    assert "not registered" in failures[0]["error"]


def test_start_generation_batch_success(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(_plan_and_approve(["S001"]))

    result = asyncio.run(start_generation_batch({}))
    assert result["ok"] is True
    assert result["submitted"] == 1
    assert result["failed"] == 0
    successes = cast(list[dict[str, Any]], result["successes"])
    assert successes[0]["provider_job_id"]


def test_start_generation_batch_skips_already_submitted(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(_plan_and_approve(["S001"]))
    first = asyncio.run(start_generation_batch({}))
    assert first["submitted"] == 1

    # Re-approving has nothing new to submit since rows already moved past
    # SUBMITTED, but calling start again should be a no-op (no SUBMITTED rows).
    second = asyncio.run(start_generation_batch({}))
    assert second["ok"] is True
    assert second["submitted"] == 0


def test_promote_test_to_production_no_active_project() -> None:
    import asyncio

    from film_pipeline.app.runtime import get_runtime as gr

    rt2 = gr()
    rt2.active_project_id = ""
    result = asyncio.run(promote_test_to_production({}))
    assert result["ok"] is False


def test_promote_test_to_production_no_eligible_rows(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(_plan_and_approve(["S001"]))
    # Rows are SUBMITTED, not yet COMPLETED, so nothing is eligible to promote.
    result = asyncio.run(promote_test_to_production({}))
    assert result["ok"] is True
    assert result["promoted"] == 0
