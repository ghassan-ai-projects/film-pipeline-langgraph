"""Agent registry — register, lookup by id, capability, or family.

This module owns agent registration: the validated catalog (``AgentRegistry``)
*and* the binding from a registered agent id to the class that implements it
(``AGENT_CLASS_BY_ID``). It is deliberately the only place either lives, so a
roster row and its implementation cannot be declared in two modules that drift.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from film_pipeline.agents.base import BaseAgent
from film_pipeline.agents.impl.assembly_agent import AssemblyAgent
from film_pipeline.agents.impl.constitution_agent import ConstitutionAgent
from film_pipeline.agents.impl.development_agent import DevelopmentAgent
from film_pipeline.agents.impl.gen_planner_agent import GenPlannerAgent
from film_pipeline.agents.impl.intake_agent import IntakeAgent
from film_pipeline.agents.impl.orchestrator_agent import OrchestratorAgent
from film_pipeline.agents.impl.qc_synthesis_agent import QCSynthesisAgent
from film_pipeline.agents.impl.screenwriter_agent import ScreenwriterAgent
from film_pipeline.agents.impl.shot_bible_agent import ShotBibleAgent
from film_pipeline.agents.impl.structure_extractor_agent import StructureExtractorAgent
from film_pipeline.agents.impl.visual_dev_agent import VisualDevAgent
from film_pipeline.agents.model_routing import ModelRouter
from film_pipeline.schemas.base import AgentFamily, AgentRole
from film_pipeline.schemas.handoff import AgentRegistration

_logger = logging.getLogger(__name__)

# One key per ``MVP_AGENTS`` row: the roster owns which ids exist, and this
# table owns which class implements each. Nothing else may name an agent id
# that the roster does not, so there is no unreachable alias here.
AGENT_CLASS_BY_ID: dict[str, type[BaseAgent]] = {
    "intake-classifier-agent": IntakeAgent,
    "film-constitution-agent": ConstitutionAgent,
    "treatment-agent": DevelopmentAgent,
    "screenwriter-agent": ScreenwriterAgent,
    "structure-extractor-agent": StructureExtractorAgent,
    "shot-design-agent": ShotBibleAgent,
    "reference-strategy-planner": VisualDevAgent,
    "provider-planning-agent": GenPlannerAgent,
    "clip-validator": QCSynthesisAgent,
    "failure-handling-agent": AssemblyAgent,
    "orchestrator-agent": OrchestratorAgent,
}


def get_agent_class(agent_id: str) -> type[BaseAgent] | None:
    """Return the concrete implementation for a registered agent id."""
    return AGENT_CLASS_BY_ID.get(agent_id)


def _default_model_profiles() -> set[str]:
    """Return known model profile ids, including legacy contract aliases."""
    return {*ModelRouter().list_profiles(), "orchestrator"}


@dataclass
class AgentRegistry:
    """Discoverable agent catalog with capability-based lookups."""

    agents: dict[str, AgentRegistration] = field(default_factory=dict)
    known_model_profiles: set[str] = field(default_factory=_default_model_profiles)
    known_kb_domains: set[str] | None = None
    known_output_artifacts: set[str] | None = None

    def register(self, contract: AgentRegistration) -> None:
        """Register an agent after validating its static contract."""
        if contract.agent_id in self.agents:
            raise ValueError(f"Agent '{contract.agent_id}' already registered.")
        self._validate_contract(contract)
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

    def _validate_contract(self, contract: AgentRegistration) -> None:
        """Validate fields that otherwise fail much later in routing."""
        self._reject_empty_contract_fields(contract)
        self._reject_unknown_model_profile(contract)
        self._reject_blank_list_values(contract)
        self._reject_overlapping_kb_domains(contract)
        self._warn_about_unknown_kb_domains(contract)
        self._reject_unknown_output_artifacts(contract)

    def _reject_empty_contract_fields(self, contract: AgentRegistration) -> None:
        if not contract.agent_id.strip():
            raise ValueError("Agent id must be non-empty.")
        if not contract.capabilities:
            raise ValueError(f"Agent '{contract.agent_id}' must declare at least one capability.")
        if not contract.output_artifacts:
            raise ValueError(f"Agent '{contract.agent_id}' must declare output artifacts.")
        if not contract.default_model_profile.strip():
            raise ValueError(f"Agent '{contract.agent_id}' must declare a default model profile.")

    def _reject_unknown_model_profile(self, contract: AgentRegistration) -> None:
        if contract.default_model_profile not in self.known_model_profiles:
            raise ValueError(
                f"Agent '{contract.agent_id}' references unknown model profile "
                f"'{contract.default_model_profile}'."
            )

    def _reject_blank_list_values(self, contract: AgentRegistration) -> None:
        for field_name, values in (
            ("capabilities", contract.capabilities),
            ("input_artifacts", contract.input_artifacts),
            ("output_artifacts", contract.output_artifacts),
            ("allowed_kb_domains", contract.allowed_kb_domains),
            ("blocked_kb_domains", contract.blocked_kb_domains),
            ("reviewed_by", contract.reviewed_by),
            ("failure_modes", contract.failure_modes),
        ):
            self._reject_blank_values(contract.agent_id, field_name, values)

    def _reject_overlapping_kb_domains(self, contract: AgentRegistration) -> None:
        overlap = set(contract.allowed_kb_domains).intersection(contract.blocked_kb_domains)
        if overlap:
            raise ValueError(
                f"Agent '{contract.agent_id}' both allows and blocks KB domain(s): "
                f"{', '.join(sorted(overlap))}."
            )

    def _warn_about_unknown_kb_domains(self, contract: AgentRegistration) -> None:
        if self.known_kb_domains is None:
            return
        unknown_domains = (
            set(contract.allowed_kb_domains).union(contract.blocked_kb_domains)
            - self.known_kb_domains
        )
        if unknown_domains:
            _logger.warning(
                "Agent '%s' references unknown KB domain(s): %s",
                contract.agent_id,
                ", ".join(sorted(unknown_domains)),
            )

    def _reject_unknown_output_artifacts(self, contract: AgentRegistration) -> None:
        if self.known_output_artifacts is None:
            return
        unknown_outputs = set(contract.output_artifacts) - self.known_output_artifacts
        if unknown_outputs:
            raise ValueError(
                f"Agent '{contract.agent_id}' produces unknown artifact type(s): "
                f"{', '.join(sorted(unknown_outputs))}."
            )

    @staticmethod
    def _reject_blank_values(agent_id: str, field_name: str, values: list[str]) -> None:
        blanks = [value for value in values if not str(value).strip()]
        if blanks:
            raise ValueError(f"Agent '{agent_id}' has blank value(s) in {field_name}.")
