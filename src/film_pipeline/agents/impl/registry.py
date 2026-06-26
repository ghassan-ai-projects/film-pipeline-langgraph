"""Concrete agent implementation registry."""

from __future__ import annotations

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

AGENT_CLASS_BY_ID: dict[str, type[BaseAgent]] = {
    "intake-classifier-agent": IntakeAgent,
    "film-constitution-agent": ConstitutionAgent,
    "treatment-agent": DevelopmentAgent,
    "screenwriter-agent": ScreenwriterAgent,
    "structure-extractor-agent": StructureExtractorAgent,
    "shot-design-agent": ShotBibleAgent,
    "reference-strategy-planner": VisualDevAgent,
    "visual-dev-agent": VisualDevAgent,
    "provider-planning-agent": GenPlannerAgent,
    "clip-validator": QCSynthesisAgent,
    "failure-handling-agent": AssemblyAgent,
    "orchestrator-agent": OrchestratorAgent,
}


def get_agent_class(agent_id: str) -> type[BaseAgent] | None:
    """Return the concrete implementation for a registered agent id."""
    return AGENT_CLASS_BY_ID.get(agent_id)
