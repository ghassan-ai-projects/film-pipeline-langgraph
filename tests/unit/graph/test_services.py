"""Tests for graph services and node artifact persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from film_pipeline.agents.model_routing import ModelRouter
from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.runner import PromptRunner
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.graph.nodes import _run_agent, _save_artifact
from film_pipeline.graph.services import SERVICES_KEY, GraphServices
from film_pipeline.schemas._base import (
    AgentFamily,
    AgentRole,
    ArtifactStatus,
    ArtifactType,
    FilmPhase,
)
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.schemas.film_constitution import FilmConstitution
from film_pipeline.schemas.handoff import AgentRegistration
from film_pipeline.schemas.kb import KBContextPacket
from film_pipeline.schemas.script import Script


def test_save_artifact_no_services(tmp_path: Path) -> None:
    state: dict[str, object] = {}
    ref = _save_artifact(state, Script(project_id="p1", title="T"), "script", "script")
    assert ref is None


def test_save_artifact_with_services(tmp_path: Path) -> None:
    store = ArtifactStore(root=tmp_path / "artifacts")
    services = GraphServices(artifact_store=store)
    state = {
        "project_id": "p1",
        SERVICES_KEY: services,
    }
    ref = _save_artifact(state, Script(project_id="p1", title="T", scenes=[]), "script", "script")
    assert ref is not None
    assert ref == "artifact:script:v1"


def test_run_agent_no_services() -> None:
    state: dict[str, object] = {}
    result = _run_agent(state, "test-agent", "script", "task")
    assert result == {"status": "no_services", "agent": "test-agent"}


def test_run_agent_not_found() -> None:
    """Dynamically-routed agent resolves to default for phase but registry is empty."""
    registry = AgentRegistry()
    services = GraphServices(agent_registry=registry)
    state = {"project_id": "p1", SERVICES_KEY: services}
    result = _run_agent(state, "nonexistent", "script", "task")
    # Routing resolves 'nonexistent' → 'screenwriter-agent' (default for script phase)
    # Empty registry → agent_not_found for resolved agent
    assert result["status"] == "agent_not_found"
    assert result["agent"] == "screenwriter-agent"


def test_run_agent_no_impl() -> None:
    """Agent registered but not in agent_map — returns no_impl status."""
    contract = AgentRegistration(
        agent_id="orchestrator-agent",  # Registered but not in agent_map
        family=AgentFamily.OPERATIONS,
        role=AgentRole.ORCHESTRATOR,
        capabilities=[],
        input_artifacts=[],
        output_artifacts=[],
        allowed_kb_domains=[],
        blocked_kb_domains=[],
        reviewed_by=[],
        failure_modes=[],
    )
    registry = AgentRegistry()
    registry.register(contract)
    runner = PromptRunner(mock_responses={"task": {"output": "data"}})
    services = GraphServices(prompt_runner=runner, agent_registry=registry)
    state = {"project_id": "p1", SERVICES_KEY: services}
    # delivery phase defaults to orchestrator-agent — registered but no impl class
    result = _run_agent(state, "some-agent", "delivery", "task")
    assert result["status"] == "no_impl"
    assert result["agent"] == "orchestrator-agent"


def test_graph_services_kb_for_without_builder() -> None:
    services = GraphServices()
    kb = services.kb_for("p1", "script", "agent1", "task1")
    assert isinstance(kb, KBContextPacket)
    assert kb.project_id == "p1"
    assert kb.phase == "script"


def test_run_agent_with_intake_agent(tmp_path: Path) -> None:
    """Full agent execution: IntakeAgent with mock model response."""
    contract = AgentRegistration(
        agent_id="intake-classifier-agent",
        family=AgentFamily.DEVELOPMENT,
        role=AgentRole.CREATOR,
        capabilities=["input_classification"],
        input_artifacts=[],
        output_artifacts=["classified_input"],
        allowed_kb_domains=[],
        blocked_kb_domains=[],
        reviewed_by=[],
        failure_modes=[],
    )
    registry = AgentRegistry()
    registry.register(contract)
    runner = PromptRunner(
        mock_responses={
            "Classify the user's film idea and produce a project profile.": {
                "intake": {
                    "project_id": "p1",
                    "title": "Test",
                    "slug": "test",
                    "target_runtime_seconds": 300,
                }
            }
        }
    )
    store = ArtifactStore(root=tmp_path / "artifacts")
    services = GraphServices(
        prompt_runner=runner,
        agent_registry=registry,
        artifact_store=store,
    )
    state: dict[str, object] = {
        "project_id": "p1",
        "idea": "A test film.",
        SERVICES_KEY: services,
    }
    result = _run_agent(
        state,
        agent_id="intake-classifier-agent",
        phase="intake",
        task="Classify the user's film idea and produce a project profile.",
    )
    assert "profile" in result
    assert result["profile"].identity.title == "Test"


def test_run_agent_injects_artifact_content_into_prompt(tmp_path: Path) -> None:
    class CaptureAdapter:
        def __init__(self) -> None:
            self.prompt = ""

        def chat_json(
            self,
            prompt: str,
            *,
            model: str,
            system: str = "",
            max_tokens: int = 4096,
            temperature: float = 0.7,
            top_p: float = 0.95,
            frequency_penalty: float = 0.0,
        ) -> dict[str, Any]:
            _ = (model, system, max_tokens, temperature, top_p, frequency_penalty)
            self.prompt = prompt
            return {
                "development": {
                    "treatment": {
                        "text": "A treatment rooted in the constitution.",
                        "themes": ["memory"],
                        "act_map": {
                            "act1_setup": "Setup",
                            "act2_confrontation": "Confrontation",
                            "act3_resolution": "Resolution",
                        },
                    },
                    "scenes": [
                        {
                            "scene_id": "s_001",
                            "dramatic_function": "Open",
                            "emotional_shift": "fear to resolve",
                            "conflict": "internal",
                            "outcome": "commitment",
                        }
                    ],
                }
            }

    contract = AgentRegistration(
        agent_id="treatment-agent",
        family=AgentFamily.DEVELOPMENT,
        role=AgentRole.CREATOR,
        capabilities=["story_development"],
        input_artifacts=["film_constitution"],
        output_artifacts=["treatment", "scene_list"],
        allowed_kb_domains=[],
        blocked_kb_domains=[],
        reviewed_by=[],
        failure_modes=[],
    )
    registry = AgentRegistry()
    registry.register(contract)
    adapter = CaptureAdapter()
    runner = PromptRunner(model_adapter=adapter, model_router=ModelRouter())  # type: ignore[arg-type]
    store = ArtifactStore(root=tmp_path / "artifacts")
    constitution = FilmConstitution(
        project_id="p1",
        theme="Memory is a wound.",
        tone="dark, intimate",
        emotional_promise="Uneasy recognition.",
        visual_language="wet neon realism",
        camera_philosophy="patient observation",
        quality_bar="No generic thriller beats.",
        taboo_mistakes=["No amnesia cliches."],
    )
    meta = ArtifactMetadata(
        artifact_id="film_constitution",
        artifact_type=ArtifactType.FILM_CONSTITUTION,
        project_id="p1",
        phase=FilmPhase("constitution"),
        version=1,
        status=ArtifactStatus.CANDIDATE,
        created_by="test",
        created_at=datetime.now(UTC),
    )
    store.save(constitution, meta)
    services = GraphServices(
        prompt_runner=runner,
        agent_registry=registry,
        artifact_store=store,
    )
    state: dict[str, object] = {
        "project_id": "p1",
        "idea": "A memory story.",
        "constitution_ref": "artifact:film_constitution:v1",
        SERVICES_KEY: services,
    }
    result = _run_agent(
        state,
        agent_id="treatment-agent",
        phase="development",
        task="Write the film treatment and scene breakdown from the constitution.",
    )
    assert "treatment" in result
    assert "Memory is a wound." in adapter.prompt
    assert "artifact:film_constitution:v1" in adapter.prompt
