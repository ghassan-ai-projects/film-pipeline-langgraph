"""Dedicated, versioned prompt templates for critical-path agents.

Each template is a frozen RCTCO prompt package with a version. Critical-path
agents MUST use these dedicated templates — generic RCTCO assembly from
contract metadata is forbidden for critical execution.

## Why the wiring lives here

`get_registry()` returns a registry with the shipped defaults already
registered. That load is wired in *this* module rather than inside `registry`,
because a package's `__init__` may import its children but a child must not reach
back up: `registry -> defaults` plus `prompt_templates -> registry` is a cycle
(`defaults` is a child of `prompt_templates`). Keeping the wiring at the root
makes the dependency flow one way and the registry content-free.
"""

from __future__ import annotations

from film_pipeline.agents.prompt_templates.registry import (
    PromptTemplateRegistry,
)
from film_pipeline.agents.prompt_templates.registry import (
    get_registry as _empty_registry,
)
from film_pipeline.agents.prompt_templates.template import PromptTemplate

__all__ = [
    "PromptTemplate",
    "PromptTemplateRegistry",
    "get_registry",
]


def get_registry() -> PromptTemplateRegistry:
    """Return the session-scoped registry with the shipped templates loaded.

    This is the entry point consumers want. `registry.get_registry` returns the
    same object but does not load anything, which is what keeps the submodule
    independent of its sibling `defaults`.
    """
    from film_pipeline.agents.prompt_templates.defaults import (
        load_all,
        load_validator_templates,
    )

    registry = _empty_registry()
    if not registry.templates:
        load_all(registry)
        load_validator_templates(registry)
    return registry
