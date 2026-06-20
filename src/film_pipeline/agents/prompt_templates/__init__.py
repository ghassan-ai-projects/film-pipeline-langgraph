"""Dedicated, versioned prompt templates for critical-path agents.

Each template is a frozen RCTCO prompt package with a version. Critical-path
agents MUST use these dedicated templates — generic RCTCO assembly from
contract metadata is forbidden for critical execution.
"""

from __future__ import annotations

from film_pipeline.agents.prompt_templates.registry import (
    PromptTemplate,
    PromptTemplateRegistry,
    get_registry,
)

__all__ = [
    "PromptTemplate",
    "PromptTemplateRegistry",
    "get_registry",
]
