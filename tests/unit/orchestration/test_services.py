"""Tests for graph services and node artifact persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from film_pipeline.agents.model_routing import ModelRouter
from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.runner import PromptRunner
from film_pipeline.app.mock_responses import default_mock_responses
from film_pipeline.orchestration.nodes import _run_agent, _save_artifact, script_node
from film_pipeline.orchestration.services import (
    _SERVICES_CTX,
    SERVICES_KEY,
    GraphServices,
    _get_services,
)
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
from film_pipeline.storage.store import ArtifactStore


def test_get_services_prefers_state_then_uses_context_fallback() -> None:
    context_services = object()
    state_services = object()
    token = _SERVICES_CTX.set(cast(GraphServices, context_services))
    try:
        assert _get_services({}) is context_services
        assert _get_services({SERVICES_KEY: state_services}) is state_services
    finally:
        _SERVICES_CTX.reset(token)


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
    assert ref == "artifact:script:script:v1"


def test_save_artifact_records_kb_context_ref(tmp_path: Path) -> None:
    store = ArtifactStore(root=tmp_path / "artifacts")
    services = GraphServices(artifact_store=store)
    state = {
        "project_id": "p1",
        "_last_kb_context_ref": "kbctx:p1:agent:test-1234",
        SERVICES_KEY: services,
    }
    ref = _save_artifact(state, Script(project_id="p1", title="T", scenes=[]), "script", "script")
    assert ref is not None
    metas = store.list_artifacts("p1", FilmPhase("script"))
    assert len(metas) == 1
    assert metas[0].kb_context_ref == "kbctx:p1:agent:test-1234"


def test_script_node_persists_story_bible_and_script_separately(tmp_path: Path) -> None:
    services = GraphServices.for_mock_runtime(
        artifacts_root=str(tmp_path / "artifacts"), mock_responses=default_mock_responses()
    )
    state: dict[str, object] = {
        "project_id": "p1",
        "idea": "A test film.",
        SERVICES_KEY: services,
    }

    updates = script_node(state)

    assert updates["story_bible_ref"] == "artifact:script:story_bible:v1"
    assert updates["script_ref"] == "artifact:script:script:v1"
    assert updates["artifact_refs"] == [
        "artifact:script:story_bible:v1",
        "artifact:script:script:v1",
    ]

    story_bible = services.artifact_store.load("p1", FilmPhase("script"), "story_bible", 1)
    script = services.artifact_store.load("p1", FilmPhase("script"), "script", 1)
    assert story_bible["logline"]["text"]
    assert script["title"] == "After the Fall"
    assert story_bible != script


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
    """Registered non-critical agent without implementation returns no_impl."""
    contract = AgentRegistration(
        agent_id="custom-review-agent",
        family=AgentFamily.OPERATIONS,
        role=AgentRole.REVIEWER,
        capabilities=["custom_review"],
        input_artifacts=["script"],
        output_artifacts=["review_report"],
        allowed_kb_domains=["operations"],
        blocked_kb_domains=[],
        reviewed_by=[],
        failure_modes=[],
    )
    registry = AgentRegistry()
    registry.register(contract)
    runner = PromptRunner(mock_responses={"task": {"output": "data"}})
    services = GraphServices(prompt_runner=runner, agent_registry=registry)
    state = {"project_id": "p1", SERVICES_KEY: services}
    result = _run_agent(state, "custom-review-agent", "script", "task", task_type="review")
    assert result["status"] == "no_impl"
    assert result["agent"] == "custom-review-agent"


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
        "constitution_ref": "artifact:constitution:film_constitution:v1",
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
    assert "artifact:constitution:film_constitution:v1" in adapter.prompt


def test_run_agent_applies_configured_artifact_context_budget(tmp_path: Path) -> None:
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
        quality_bar="No generic thriller beats. " * 800,
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
        "constitution_ref": "artifact:constitution:film_constitution:v1",
        "resolved_config": {"context": {"max_chars_per_artifact": 700}},
        SERVICES_KEY: services,
    }

    result = _run_agent(
        state,
        agent_id="treatment-agent",
        phase="development",
        task="Write the film treatment and scene breakdown from the constitution.",
    )

    assert "treatment" in result
    assert "[COMPRESSED ARTIFACT CONTEXT]" in adapter.prompt
    assert "Emitted character budget: 700" in adapter.prompt
    assert adapter.prompt.count("No generic thriller beats.") < 10
