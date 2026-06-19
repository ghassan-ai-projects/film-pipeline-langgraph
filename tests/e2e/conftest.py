"""E2E test conftest — shared fixtures for mock mini-film scenarios."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.agents.mvp import MVP_AGENTS
from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.checkpoints.manager import CheckpointManager
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
