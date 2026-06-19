"""Graph services — dependencies injected into graph state for execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from film_pipeline.agents.runner import PromptRunner
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.schemas.kb import KBContextPacket


@dataclass
class GraphServices:
    """Dependencies available to graph nodes during execution.

    Injected into state as ``_services`` by the runtime before each graph
    invocation. Nodes read from this to invoke agents, persist artifacts,
    and run validators.
    """

    prompt_runner: PromptRunner = field(default_factory=PromptRunner)
    artifact_store: ArtifactStore = field(default_factory=ArtifactStore)
    agent_registry: Any = None  # AgentRegistry
    validator_registry: Any = None  # ValidatorRegistry
    kb_builder: Any = None  # KBContextPacketBuilder

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
