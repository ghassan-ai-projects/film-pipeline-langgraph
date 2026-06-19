"""Integration tests for generation MCP tools via StudioRuntime."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest import mock

import pytest

from film_pipeline.agents.mvp import MVP_AGENTS
from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.runner import PromptRunner
from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.graph.services import GraphServices
from film_pipeline.mcp.tools import (  # type: ignore[attr-defined]
    approve_generation_spend,
    cancel_generation_request,
    get_generation_status,
    list_active_generations,
    plan_generation_batch,
    resume_generation_polling,
)


@pytest.fixture
def rt(tmp_path: Path) -> StudioRuntime:
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
    rt.create_project("gen-test", "Gen Test")
    rt.set_active("gen-test")
    with mock.patch("film_pipeline.mcp.tools.get_runtime", return_value=rt):
        yield rt


class TestGenerationMCPTools:
    def test_plan_batch_with_shot_ids(self, rt: StudioRuntime) -> None:
        async def _run() -> dict[str, object]:
            return await plan_generation_batch({
                "shot_ids": ["S001", "S002"],
                "provider": "mock-video-provider",
                "model": "mock-fast",
                "mode": "test",
            })
        result = asyncio.run(_run())
        assert result.get("ok") is True
        assert result.get("planned") == 2

    def test_plan_batch_idempotent(self, rt: StudioRuntime) -> None:
        async def _run(ids: list[str]) -> dict[str, object]:
            return await plan_generation_batch({
                "shot_ids": ids,
                "provider": "p",
                "model": "m",
            })
        asyncio.run(_run(["S001"]))
        result = asyncio.run(_run(["S001", "S002"]))
        assert result.get("planned") == 2
        assert result.get("total_rows") == 2

    def test_plan_batch_no_shot_ids(self, rt: StudioRuntime) -> None:
        async def _run() -> dict[str, object]:
            return await plan_generation_batch({"provider": "p", "model": "m"})
        result = asyncio.run(_run())
        assert result.get("ok") is not True

    def test_approve_spend(self, rt: StudioRuntime) -> None:
        asyncio.run(plan_generation_batch({
            "shot_ids": ["S001"], "provider": "p", "model": "m",
        }))
        result = asyncio.run(approve_generation_spend({}))
        assert result.get("ok") is True
        assert result.get("approved") == 1

    def test_get_status(self, rt: StudioRuntime) -> None:
        plan_result = asyncio.run(plan_generation_batch({
            "shot_ids": ["S001"], "provider": "p", "model": "m",
        }))
        gen_id = plan_result["rows"][0]["generation_id"]
        result = asyncio.run(get_generation_status({"generation_id": gen_id}))
        assert result.get("ok") is True
        assert result.get("status") == "prepared"

    def test_get_status_not_found(self, rt: StudioRuntime) -> None:
        result = asyncio.run(get_generation_status({"generation_id": "nonexistent"}))
        assert result.get("ok") is not True

    def test_list_active(self, rt: StudioRuntime) -> None:
        asyncio.run(plan_generation_batch({
            "shot_ids": ["S001", "S002"], "provider": "p", "model": "m",
        }))
        result = asyncio.run(list_active_generations({}))
        assert result.get("ok") is True
        assert result.get("count") == 2

    def test_cancel_locally(self, rt: StudioRuntime) -> None:
        plan_result = asyncio.run(plan_generation_batch({
            "shot_ids": ["S001"], "provider": "p", "model": "m",
        }))
        gen_id = plan_result["rows"][0]["generation_id"]
        result = asyncio.run(cancel_generation_request({"generation_id": gen_id}))
        assert result.get("ok") is True
        assert result.get("cancelled") is True

    def test_cancel_not_found(self, rt: StudioRuntime) -> None:
        result = asyncio.run(cancel_generation_request({"generation_id": "nonexistent"}))
        assert result.get("ok") is not True

    def test_resume_no_provider_job(self, rt: StudioRuntime) -> None:
        plan_result = asyncio.run(plan_generation_batch({
            "shot_ids": ["S001"], "provider": "p", "model": "m",
        }))
        gen_id = plan_result["rows"][0]["generation_id"]
        result = asyncio.run(resume_generation_polling({"generation_id": gen_id}))
        assert result.get("ok") is not True
