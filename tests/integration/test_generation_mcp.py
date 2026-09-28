"""Integration tests for generation MCP tools via StudioRuntime."""

from __future__ import annotations

from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any, cast
from unittest import mock

import pytest

from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.roster import MVP_AGENTS
from film_pipeline.agents.runner import PromptRunner
from film_pipeline.mcp.tools import (
    cancel_generation_request,
    get_generation_status,
    list_active_generations,
    plan_generation_batch,
    resume_generation_polling,
)
from film_pipeline.orchestration.services import GraphServices
from film_pipeline.storage.store import ArtifactStore
from film_pipeline.studio.runtime import StudioRuntime

CallTool = Callable[..., Any]


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
    rt.create_project("gen-test", "Gen Test")
    rt.set_active("gen-test")
    with mock.patch("film_pipeline.mcp.tools.get_runtime", return_value=rt):
        yield rt


class TestGenerationMCPTools:
    def test_plan_batch_with_shot_ids(self, rt: StudioRuntime, call_tool: CallTool) -> None:
        def _run() -> dict[str, object]:
            result: dict[str, object] = call_tool(
                plan_generation_batch,
                {
                    "shot_ids": ["S001", "S002"],
                    "provider": "mock-video-provider",
                    "model": "mock-fast",
                    "mode": "test",
                },
            )
            return result

        result = _run()
        assert result.get("ok") is True
        assert result.get("planned") == 2

    def test_plan_batch_idempotent(self, rt: StudioRuntime, call_tool: CallTool) -> None:
        def _run(ids: list[str]) -> dict[str, object]:
            result: dict[str, object] = call_tool(
                plan_generation_batch,
                {
                    "shot_ids": ids,
                    "provider": "p",
                    "model": "m",
                },
            )
            return result

        _run(["S001"])
        result = _run(["S001", "S002"])
        assert result.get("planned") == 2
        assert result.get("total_rows") == 2

    def test_plan_batch_no_shot_ids(self, rt: StudioRuntime, call_tool: CallTool) -> None:
        def _run() -> dict[str, object]:
            result: dict[str, object] = call_tool(
                plan_generation_batch, {"provider": "p", "model": "m"}
            )
            return result

        result = _run()
        assert result.get("ok") is not True

    def test_approve_spend(self, rt: StudioRuntime, call_tool: CallTool) -> None:
        """Approval moves planned rows to SUBMITTED.

        The MCP `approve_generation_spend` tool was removed with the cost feature;
        this asserts the transition it performed, through the operator use case
        that survives it.
        """
        call_tool(
            plan_generation_batch,
            {
                "shot_ids": ["S001"],
                "provider": "p",
                "model": "m",
            },
        )
        # The operator method went with the operator surface; GenerationExecutor
        # owns the PREPARED -> SUBMITTED transition.
        from film_pipeline.generation.executor import GenerationExecutor
        from film_pipeline.mcp.tools import get_runtime

        runtime = get_runtime()
        services = runtime.services
        assert services is not None
        executor = GenerationExecutor(services.artifact_store, runtime.provider_adapters)
        project_id = str((runtime.get_active() or {})["project_id"])
        assert executor.approve_spend(project_id).processed == 1, "expected one submitted row"

    def test_get_status(self, rt: StudioRuntime, call_tool: CallTool) -> None:
        plan_result = call_tool(
            plan_generation_batch,
            {
                "shot_ids": ["S001"],
                "provider": "p",
                "model": "m",
            },
        )
        gen_id = cast(list[dict[str, Any]], plan_result["rows"])[0]["generation_id"]
        result = call_tool(get_generation_status, {"generation_id": gen_id})
        assert result.get("ok") is True
        assert result.get("status") == "prepared"

    def test_get_status_not_found(self, rt: StudioRuntime, call_tool: CallTool) -> None:
        result = call_tool(get_generation_status, {"generation_id": "nonexistent"})
        assert result.get("ok") is not True

    def test_list_active(self, rt: StudioRuntime, call_tool: CallTool) -> None:
        call_tool(
            plan_generation_batch,
            {
                "shot_ids": ["S001", "S002"],
                "provider": "p",
                "model": "m",
            },
        )
        result = call_tool(list_active_generations, {})
        assert result.get("ok") is True
        assert result.get("count") == 2

    def test_cancel_locally(self, rt: StudioRuntime, call_tool: CallTool) -> None:
        plan_result = call_tool(
            plan_generation_batch,
            {
                "shot_ids": ["S001"],
                "provider": "p",
                "model": "m",
            },
        )
        gen_id = cast(list[dict[str, Any]], plan_result["rows"])[0]["generation_id"]
        result = call_tool(cancel_generation_request, {"generation_id": gen_id})
        assert result.get("ok") is True
        assert result.get("cancelled") is True

    def test_cancel_not_found(self, rt: StudioRuntime, call_tool: CallTool) -> None:
        result = call_tool(cancel_generation_request, {"generation_id": "nonexistent"})
        assert result.get("ok") is not True

    def test_resume_no_provider_job(self, rt: StudioRuntime, call_tool: CallTool) -> None:
        plan_result = call_tool(
            plan_generation_batch,
            {
                "shot_ids": ["S001"],
                "provider": "p",
                "model": "m",
            },
        )
        gen_id = cast(list[dict[str, Any]], plan_result["rows"])[0]["generation_id"]
        result = call_tool(resume_generation_polling, {"generation_id": gen_id})
        assert result.get("ok") is not True
