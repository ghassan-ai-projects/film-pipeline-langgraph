"""Agent registry — register, lookup by id, capability, or family."""

from __future__ import annotations

from dataclasses import dataclass, field

from film_pipeline.schemas._base import AgentFamily, AgentRole
from film_pipeline.schemas.handoff import AgentRegistration


@dataclass
class AgentRegistry:
    """Discoverable agent catalog with capability-based lookups."""

    agents: dict[str, AgentRegistration] = field(default_factory=dict)

    def register(self, contract: AgentRegistration) -> None:
        """Register an agent. Raises ValueError on duplicate id."""
        if contract.agent_id in self.agents:
            raise ValueError(f"Agent '{contract.agent_id}' already registered.")
        self.agents[contract.agent_id] = contract

    def register_many(self, contracts: list[AgentRegistration]) -> None:
        for c in contracts:
            self.register(c)

    def lookup_by_id(self, agent_id: str) -> AgentRegistration | None:
        return self.agents.get(agent_id)

    def lookup_by_capability(self, capability: str) -> list[AgentRegistration]:
        return [a for a in self.agents.values() if capability in a.capabilities]

    def lookup_by_family(self, family: AgentFamily) -> list[AgentRegistration]:
        return [a for a in self.agents.values() if a.family == family]

    def lookup_by_role(self, role: AgentRole) -> list[AgentRegistration]:
        return [a for a in self.agents.values() if a.role == role]

    def __len__(self) -> int:
        return len(self.agents)

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self.agents
