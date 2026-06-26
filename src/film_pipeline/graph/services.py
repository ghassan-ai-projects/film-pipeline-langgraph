"""Graph services — runtime dependencies available to graph execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from film_pipeline.agents.model_adapter import ModelAdapter
from film_pipeline.agents.model_routing import ModelRouter
from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.runner import PromptRunner
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.schemas.kb import KBContextPacket


@dataclass
class GraphServices:
    """Dependencies available to graph nodes during execution.

    Supplied by the runtime through graph execution context. Nodes read these
    services to invoke agents, persist artifacts, and run validators. Unit
    tests may still pass ``_services`` directly in state for focused helper
    coverage, but production graph checkpoints must not persist this object.
    """

    prompt_runner: PromptRunner = field(default_factory=PromptRunner)
    artifact_store: ArtifactStore = field(default_factory=ArtifactStore)
    agent_registry: AgentRegistry | None = None
    validator_registry: Any = None  # ValidatorRegistry
    kb_builder: Any = None  # KBContextPacketBuilder

    @classmethod
    def for_mock_runtime(cls, artifacts_root: str = "projects") -> GraphServices:
        """Create services wired for mock-mode execution.

        Populates the agent registry with all MVP agents, sets up a
        PromptRunner with canned mock responses for the core spine agents,
        and wires a ModelRouter.
        """
        from film_pipeline.agents.mvp import MVP_AGENTS
        from film_pipeline.testing.fixtures.mock_responses import default_mock_responses

        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)

        runner = PromptRunner(
            mock_responses=default_mock_responses(),
            model_router=ModelRouter(),
        )
        return cls(
            prompt_runner=runner,
            artifact_store=ArtifactStore(root=Path(artifacts_root)),
            agent_registry=registry,
        )

    @classmethod
    def for_real_runtime(cls, artifacts_root: str = "projects") -> GraphServices:
        """Create services wired for real model execution.

        This keeps the same agent registry and artifact store contract as mock
        mode, but removes canned prompt responses and enables the real model
        adapter path through OpenRouter.
        """
        from film_pipeline.agents.mvp import MVP_AGENTS

        registry = AgentRegistry()
        registry.register_many(MVP_AGENTS)

        runner = PromptRunner(
            model_adapter=ModelAdapter(),
            model_router=ModelRouter(),
        )
        return cls(
            prompt_runner=runner,
            artifact_store=ArtifactStore(root=Path(artifacts_root)),
            agent_registry=registry,
        )

    def kb_for(
        self,
        project_id: str,
        phase: str,
        agent_id: str,
        task: str,
    ) -> KBContextPacket:
        """Build a KB context packet, or a minimal one if no builder is set."""
        if self.kb_builder is not None:
            result = self.kb_builder.build(
                project_id=project_id,
                phase=phase,
                agent_id=agent_id,
                task=task,
            )
            if isinstance(result, KBContextPacket):
                return result
        return KBContextPacket(
            kb_context_id=f"kbctx:{project_id}:{phase}:{agent_id}:v1",
            project_id=project_id,
            phase=phase,
            agent_id=agent_id,
            task=task,
        )


SERVICES_KEY = "_services"
