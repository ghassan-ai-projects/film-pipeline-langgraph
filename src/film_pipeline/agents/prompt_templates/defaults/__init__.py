"""Default prompt templates for all critical-path agents.

Every critical agent has a dedicated, versioned template. These replace the
generic RCTCO assembly that builds prompts from contract metadata.

Template versions are incremented when the template content changes.
"""

from __future__ import annotations

from typing import Protocol

from film_pipeline.agents._prompt_template import PromptTemplate
from film_pipeline.agents.prompt_templates.defaults.production import (
    _assembly_agent,
    _generation_planner,
    _orchestrator_review,
    _qc_synthesizer,
    _shot_bible_creator,
    _visual_development_creator,
)
from film_pipeline.agents.prompt_templates.defaults.spine import (
    _constitution_creator,
    _development_creator,
    _intake_classifier,
    _screenwriter,
    _structure_extractor,
)
from film_pipeline.agents.prompt_templates.defaults.validators import (
    _assembly_validator,
    _delivery_completeness_validator,
    _dialogue_voice_validator,
    _prompt_readiness_validator,
    _reference_usability_validator,
    _scene_continuity_validator,
    _script_structure_validator,
)


class _TemplateRegistrar(Protocol):
    def register(self, template: PromptTemplate) -> None: ...


__all__ = [
    "_assembly_agent",
    "_assembly_validator",
    "_constitution_creator",
    "_delivery_completeness_validator",
    "_development_creator",
    "_dialogue_voice_validator",
    "_generation_planner",
    "_intake_classifier",
    "_orchestrator_review",
    "_prompt_readiness_validator",
    "_qc_synthesizer",
    "_reference_usability_validator",
    "_scene_continuity_validator",
    "_screenwriter",
    "_script_structure_validator",
    "_shot_bible_creator",
    "_structure_extractor",
    "_visual_development_creator",
    "load_all",
    "load_validator_templates",
]


def load_all(reg: _TemplateRegistrar) -> None:
    """Register all critical-path agent templates."""
    reg.register(_intake_classifier())
    reg.register(_constitution_creator())
    reg.register(_development_creator())
    reg.register(_screenwriter())
    reg.register(_visual_development_creator())
    reg.register(_shot_bible_creator())
    reg.register(_generation_planner())
    reg.register(_qc_synthesizer())
    reg.register(_structure_extractor())
    reg.register(_assembly_agent())
    reg.register(_orchestrator_review())


def load_validator_templates(reg: _TemplateRegistrar) -> None:
    """Register all 7 validator prompt templates for LLM-based validation."""
    reg.register(_script_structure_validator())
    reg.register(_dialogue_voice_validator())
    reg.register(_prompt_readiness_validator())
    reg.register(_reference_usability_validator())
    reg.register(_scene_continuity_validator())
    reg.register(_assembly_validator())
    reg.register(_delivery_completeness_validator())
