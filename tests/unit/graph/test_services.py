"""Tests for graph services and node artifact persistence."""

from __future__ import annotations

from pathlib import Path

from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.runner import PromptRunner
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.graph.nodes import _run_agent, _save_artifact
from film_pipeline.graph.services import SERVICES_KEY, GraphServices
from film_pipeline.schemas._base import AgentFamily, AgentRole
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
    registry = AgentRegistry()
    services = GraphServices(agent_registry=registry)
    state = {"project_id": "p1", SERVICES_KEY: services}
    result = _run_agent(state, "nonexistent", "script", "task")
    assert result == {"status": "agent_not_found", "agent": "nonexistent"}


def test_run_agent_no_impl() -> None:
    contract = AgentRegistration(
        agent_id="unknown-agent",
        family=AgentFamily.OPERATIONS,
        role=AgentRole.CREATOR,
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
    result = _run_agent(state, "unknown-agent", "script", "task")
    assert result["status"] == "no_impl"
    assert result["agent"] == "unknown-agent"


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
