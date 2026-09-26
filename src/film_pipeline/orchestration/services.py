"""Graph services — runtime dependencies available to graph execution."""

from __future__ import annotations

import contextvars
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from film_pipeline.agents.model_adapter import ModelAdapter as ModelAdapter
from film_pipeline.agents.model_routing import ModelRouter as ModelRouter
from film_pipeline.agents.registry import AgentRegistry as AgentRegistry
from film_pipeline.agents.runner import PromptRunner as PromptRunner
from film_pipeline.schemas.kb import KBContextPacket as KBContextPacket
from film_pipeline.storage.storage import (
    PROFILE_PRODUCTION,
    PROFILE_SANDBOX,
)
from film_pipeline.storage.storage import (
    ensure_storage_root as ensure_storage_root,
)
from film_pipeline.storage.storage import resolve_storage_root as resolve_storage_root
from film_pipeline.storage.store import ArtifactStore as ArtifactStore

if TYPE_CHECKING:
    from film_pipeline.kb.packets import KBContextPacketBuilder


def _default_artifact_root() -> Path:
    """Pick a safe artifact root based on the persistence environment."""
    if os.getenv("FILM_PIPELINE_NO_PERSIST"):
        return Path(tempfile.gettempdir()) / f"film_pipeline_artifacts_{os.getpid()}"
    return resolve_storage_root()


def _mvp_agent_registry() -> AgentRegistry:
    """Register every MVP agent into a fresh registry."""
    from film_pipeline.agents.roster import MVP_AGENTS

    registry = AgentRegistry()
    registry.register_many(MVP_AGENTS)
    return registry


def _artifact_store(artifacts_root: str | Path | None) -> ArtifactStore:
    """Build an artifact store at ``artifacts_root`` or the environment default."""
    root = Path(artifacts_root) if artifacts_root is not None else _default_artifact_root()
    profile = PROFILE_SANDBOX if os.getenv("FILM_PIPELINE_NO_PERSIST") else PROFILE_PRODUCTION
    return ArtifactStore(root=ensure_storage_root(root, profile=profile))


@dataclass
class GraphServices:
    """Dependencies available to graph nodes during execution.

    Supplied by the runtime through graph execution context. Nodes read these
    services to invoke agents, persist artifacts, and run validators. Unit
    tests may still pass ``_services`` directly in state for focused helper
    coverage, but production graph checkpoints must not persist this object.
    """

    prompt_runner: PromptRunner = field(default_factory=PromptRunner)
    artifact_store: ArtifactStore = field(default_factory=lambda: _artifact_store(None))
    agent_registry: AgentRegistry | None = None
    validator_registry: Any = None  # ValidatorRegistry
    kb_builder: KBContextPacketBuilder | None = None

    @classmethod
    def for_mock_runtime(
        cls,
        artifacts_root: str | Path | None = None,
        *,
        mock_responses: Mapping[str, dict[str, Any]],
    ) -> GraphServices:
        """Create services wired for mock-mode execution.

        Populates the agent registry with all MVP agents, sets up a
        PromptRunner over the caller-supplied canned responses, and wires a
        ModelRouter. The responses are injected — not imported — so the graph
        package carries no fixture data; composition roots pass
        ``app.mock_responses.default_mock_responses()``.
        """
        runner = PromptRunner(
            mock_responses=dict(mock_responses),
            model_router=ModelRouter(),
        )
        return cls(
            prompt_runner=runner,
            artifact_store=_artifact_store(artifacts_root),
            agent_registry=_mvp_agent_registry(),
        )

    @classmethod
    def for_real_runtime(cls, artifacts_root: str | Path | None = None) -> GraphServices:
        """Create services wired for real model execution.

        This keeps the same agent registry and artifact store contract as mock
        mode, but removes canned prompt responses and enables the real model
        adapter path through the configured model profile and provider adapter.
        """
        runner = PromptRunner(
            model_adapter=ModelAdapter(),
            model_router=ModelRouter(),
        )
        return cls(
            prompt_runner=runner,
            artifact_store=_artifact_store(artifacts_root),
            agent_registry=_mvp_agent_registry(),
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

_SERVICES_CTX: contextvars.ContextVar[GraphServices | None] = contextvars.ContextVar(
    "_film_pipeline_services", default=None
)


def _get_services(state: dict[str, Any]) -> GraphServices | None:
    """Return graph services from state, falling back to runtime context.

    LangGraph may drop undeclared state keys between node boundaries. The
    context variable keeps runtime services available without checkpointing
    them into graph state.
    """
    svc = state.get(SERVICES_KEY)
    if svc is not None:
        return svc  # type: ignore[no-any-return]
    return _SERVICES_CTX.get()
