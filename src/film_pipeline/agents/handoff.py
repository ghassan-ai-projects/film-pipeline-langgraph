"""Handoff manager — creates, tracks, and validates agent handoff records."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from film_pipeline.schemas.handoff import AgentHandoff, AgentRegistration
from film_pipeline.schemas.kb import KBContextPacket


@dataclass
class HandoffManager:
    """Manages agent-to-agent handoff records."""

    handoffs: list[AgentHandoff] = field(default_factory=list)

    def create(
        self,
        contract: AgentRegistration,
        project_id: str,
        task: str,
        kb_context: KBContextPacket,
        input_artifact_refs: list[str] | None = None,
        to_agent: str = "orchestrator-agent",
    ) -> AgentHandoff:
        """Create and record a handoff."""
        handoff = AgentHandoff(
            handoff_id=f"handoff:{contract.agent_id}:{uuid4().hex[:8]}",
            from_agent=contract.agent_id,
            to_agent=to_agent,
            project_id=project_id,
            input_artifact_refs=input_artifact_refs or [],
            kb_context_ref=kb_context.kb_context_id,
            task=task,
            expected_output_schema=(
                contract.output_artifacts[0] if contract.output_artifacts else "any"
            ),
            validation_required=contract.reviewed_by,
        )
        self.handoffs.append(handoff)
        return handoff

    def by_agent(self, agent_id: str) -> list[AgentHandoff]:
        return [h for h in self.handoffs if h.from_agent == agent_id]

    def by_project(self, project_id: str) -> list[AgentHandoff]:
        return [h for h in self.handoffs if h.project_id == project_id]

    def __len__(self) -> int:
        return len(self.handoffs)
