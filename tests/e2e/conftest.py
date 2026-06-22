"""E2E test conftest — shared fixtures for mock mini-film scenarios."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from film_pipeline.agents.mvp import MVP_AGENTS
from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.runner import PromptRunner
from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.checkpoints.manager import CheckpointManager
from film_pipeline.graph.services import GraphServices
from film_pipeline.kb.manifest import KBManifest
from film_pipeline.kb.packets import KBContextPacketBuilder
from film_pipeline.providers.health import ProviderHealthTracker
from film_pipeline.providers.mock_provider import MockVideoProvider
from film_pipeline.providers.registry import ProviderRegistry
from film_pipeline.schemas.registries.provider_registry import (
    CostProfile,
    ProviderCapabilities,
    ProviderRegistryEntry,
)
from film_pipeline.testing.mock_human import DecisionProfile, MockHumanActor
from film_pipeline.testing.mock_model import MockModelAdapter
from film_pipeline.validation.registry import ValidatorRegistry
from film_pipeline.validation.validators import MVP_VALIDATORS


@pytest.fixture
def mock_human() -> MockHumanActor:
    return MockHumanActor(profile=DecisionProfile.APPROVE_ALL)


@pytest.fixture
def mock_model() -> MockModelAdapter:
    model = MockModelAdapter()
    # Pre-register responses for all MVP agents
    for agent in MVP_AGENTS:
        model.register(agent.agent_id, {"status": "ok", "agent": agent.agent_id, "output": {}})
    # Pre-register responses for all MVP validators
    for validator in MVP_VALIDATORS:
        model.register(validator.validator_id, {"score": 90, "status": "pass", "issues": []})
    return model


@pytest.fixture
def agent_registry() -> AgentRegistry:
    reg = AgentRegistry()
    reg.register_many(MVP_AGENTS)
    return reg


@pytest.fixture
def validator_registry() -> ValidatorRegistry:
    reg = ValidatorRegistry()
    reg.register_many(MVP_VALIDATORS)
    return reg


@pytest.fixture
def mock_provider() -> MockVideoProvider:
    entry = ProviderRegistryEntry(
        provider_id="mock-video-provider",
        provider_type="video",
        models=["mock-fast"],
        capabilities=ProviderCapabilities(
            text_to_video=True,
            image_to_video=True,
            return_last_frame=True,
            max_duration_seconds=30,
            aspect_ratios=["16:9"],
        ),
        cost_profile=CostProfile(unit="second", estimated_rate_usd=0.0),
    )
    return MockVideoProvider(entry=entry)


@pytest.fixture
def provider_registry(mock_provider: MockVideoProvider) -> ProviderRegistry:
    reg = ProviderRegistry()
    reg.register(mock_provider)
    return reg


@pytest.fixture
def health_tracker() -> ProviderHealthTracker:
    tracker = ProviderHealthTracker()
    tracker.register("mock-video-provider")
    return tracker


@pytest.fixture
def kb_manifest() -> KBManifest:
    manifest_path = Path("film-knowledge-base/index/kb-manifest.yaml")
    if not manifest_path.exists():
        pytest.skip("kb-manifest.yaml not found")
    return KBManifest.from_yaml(manifest_path)


@pytest.fixture
def kb_builder(kb_manifest: KBManifest) -> KBContextPacketBuilder:
    return KBContextPacketBuilder(kb_manifest)


@pytest.fixture
def git_backend(tmp_path: Path) -> GitBackend:
    return GitBackend.init_temp(tmp_path / "repo")


@pytest.fixture
def checkpoint_manager(git_backend: GitBackend) -> CheckpointManager:
    return CheckpointManager(git_backend)


@pytest.fixture
def graph_services(
    mock_model: MockModelAdapter,
    agent_registry: AgentRegistry,
    kb_builder: KBContextPacketBuilder,
    tmp_path: Path,
) -> GraphServices:
    """GraphServices wired with mock model and in-memory registries."""
    from film_pipeline.graph.services import _default_mock_responses

    runner = PromptRunner(mock_responses=_default_mock_responses())
    return GraphServices(
        prompt_runner=runner,
        artifact_store=ArtifactStore(root=tmp_path / "artifacts"),
        agent_registry=agent_registry,
        kb_builder=kb_builder,
    )


@pytest.fixture
def studio_runtime(
    graph_services: GraphServices,
    mock_provider: MockVideoProvider,
    tmp_path: Path,
) -> Generator[StudioRuntime, None, None]:
    """A fully wired StudioRuntime for E2E MCP-driven tests.

    Sets the global ``_RUNTIME`` singleton so MCP tools resolve to this
    runtime, and restores the previous value on teardown so tests do not
    bleed into each other.
    """
    import film_pipeline.app.runtime as rt_mod

    rt = StudioRuntime(runtime_root=tmp_path / "e2e-runtime")
    rt.services = graph_services
    rt.register_provider("mock-video-provider", mock_provider)
    rt.provider_health["mock-video-provider"] = {
        "status": "healthy",
        "reason": "",
    }

    # Save and replace the global singleton so MCP tools see this runtime
    previous_runtime = rt_mod._RUNTIME
    rt_mod._RUNTIME = rt
    try:
        yield rt
    finally:
        rt_mod._RUNTIME = previous_runtime


def invoke_tool(
    rt: StudioRuntime,
    tool_name: str,
    **args: Any,
) -> dict[str, Any]:
    """Synchronously invoke an MCP tool by name against the runtime.

    Sets the runtime singleton so MCP tools resolve to the test runtime.
    """
    import importlib

    # Set the runtime singleton for MCP tools
    import film_pipeline.app.runtime as rt_mod

    rt_mod._RUNTIME = rt

    async def _invoke() -> dict[str, Any]:
        mod = importlib.import_module("film_pipeline.mcp.tools")
        handler = getattr(mod, tool_name, None)
        if handler is None:
            raise ValueError(f"Unknown MCP tool: {tool_name}")
        return await handler(dict(args))  # type: ignore[no-any-return]

    return asyncio.run(_invoke())
