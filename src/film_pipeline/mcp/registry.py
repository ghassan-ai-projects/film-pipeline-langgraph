"""Tool registration entry point — wires every tool from every submodule."""

from __future__ import annotations

from film_pipeline.mcp.contract import ToolRegistry
from film_pipeline.mcp.tools._profile_change import PROFILE_CHANGE_TOOLS
from film_pipeline.mcp.tools.artifacts import (
    ARTIFACT_TOOLS,
)
from film_pipeline.mcp.tools.assembly import (
    ASSEMBLY_TOOLS,
    COVERAGE_TOOLS,
)
from film_pipeline.mcp.tools.audit import AUDIT_TOOLS
from film_pipeline.mcp.tools.bibles import BIBLE_TOOLS
from film_pipeline.mcp.tools.checkpoints import CHECKPOINT_TOOLS
from film_pipeline.mcp.tools.config import (
    CONFIG_TOOLS,
)
from film_pipeline.mcp.tools.generation import (
    GENERATION_DISPATCH_TOOLS,
    GENERATION_PLANNING_TOOLS,
    GENERATION_PROMOTE_TOOLS,
    GENERATION_STATUS_TOOLS,
)
from film_pipeline.mcp.tools.intake import (
    INTAKE_TOOLS,
)
from film_pipeline.mcp.tools.kb import (
    KB_TOOLS,
)
from film_pipeline.mcp.tools.operator import (
    OPERATOR_TOOLS,
)
from film_pipeline.mcp.tools.planning import GENERATE_PLAN
from film_pipeline.mcp.tools.projects import PROJECT_TOOLS
from film_pipeline.mcp.tools.providers import (
    PROVIDER_TOOLS,
)
from film_pipeline.mcp.tools.reference_generation import (
    GENERATE_REFERENCE_IMAGES,
)
from film_pipeline.mcp.tools.review import (
    REVIEW_TOOLS,
)
from film_pipeline.mcp.tools.state import (
    STATE_TOOLS,
)
from film_pipeline.mcp.tools.validation import (
    RUN_VALIDATION,
    VALIDATION_TOOLS,
)


def register_all_tools(registry: ToolRegistry) -> None:
    """Register every MCP tool contract with its handler on ``registry``."""
    # project
    for spec in PROJECT_TOOLS:
        registry.register_spec(spec)

    # intake
    for spec in INTAKE_TOOLS:
        registry.register_spec(spec)

    # state
    for spec in STATE_TOOLS:
        registry.register_spec(spec)

    # review
    for spec in REVIEW_TOOLS:
        registry.register_spec(spec)

    # artifact
    for spec in ARTIFACT_TOOLS:
        registry.register_spec(spec)

    # validation
    for spec in VALIDATION_TOOLS:
        registry.register_spec(spec)

    # generation
    for spec in GENERATION_PLANNING_TOOLS:
        registry.register_spec(spec)
    registry.register_spec(RUN_VALIDATION)
    registry.register_spec(GENERATE_PLAN)
    registry.register_spec(GENERATE_REFERENCE_IMAGES)
    for spec in GENERATION_DISPATCH_TOOLS:
        registry.register_spec(spec)
    for spec in GENERATION_STATUS_TOOLS:
        registry.register_spec(spec)
    for spec in BIBLE_TOOLS:
        registry.register_spec(spec)
    for spec in GENERATION_PROMOTE_TOOLS:
        registry.register_spec(spec)

    # kb
    for spec in KB_TOOLS:
        registry.register_spec(spec)

    # checkpoint
    for spec in CHECKPOINT_TOOLS:
        registry.register_spec(spec)

    # operator
    for spec in OPERATOR_TOOLS:
        registry.register_spec(spec)

    # audit
    for spec in AUDIT_TOOLS:
        registry.register_spec(spec)

    # provider
    for spec in PROVIDER_TOOLS:
        registry.register_spec(spec)

    # config / profile
    for spec in CONFIG_TOOLS:
        registry.register_spec(spec)
    for spec in PROFILE_CHANGE_TOOLS:
        registry.register_spec(spec)

    # coverage
    for spec in COVERAGE_TOOLS:
        registry.register_spec(spec)

    # assembly
    for spec in ASSEMBLY_TOOLS:
        registry.register_spec(spec)
