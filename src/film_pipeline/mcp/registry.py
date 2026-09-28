"""Tool registration entry point — wires every tool from every submodule."""

from __future__ import annotations

from film_pipeline.mcp.contract import ToolRegistry
from film_pipeline.mcp.tools.artifacts import (
    ARTIFACT_TOOLS,
)
from film_pipeline.mcp.tools.assembly import (
    approve_coverage_generation,
    assemble_final_cut,
    assemble_review_cut,
    export_delivery_package,
    inspect_coverage_group,
    list_coverage_groups,
    plan_coverage_group,
)
from film_pipeline.mcp.tools.audit import AUDIT_TOOLS
from film_pipeline.mcp.tools.bibles import BIBLE_TOOLS
from film_pipeline.mcp.tools.checkpoints import CHECKPOINT_TOOLS
from film_pipeline.mcp.tools.config import (
    approve_profile_change,
    get_runtime_mode,
    inspect_profile,
    list_profiles,
    propose_profile_change,
)
from film_pipeline.mcp.tools.generation import (
    GENERATION_DISPATCH_TOOLS,
    GENERATION_PLANNING_TOOLS,
    GENERATION_PROMOTE_TOOLS,
    GENERATION_STATUS_TOOLS,
)
from film_pipeline.mcp.tools.intake import approve_intake, get_intake_analysis, submit_idea
from film_pipeline.mcp.tools.kb import (
    KB_TOOLS,
)
from film_pipeline.mcp.tools.operator import add_operator_comment, list_operator_comments
from film_pipeline.mcp.tools.planning import generate_plan
from film_pipeline.mcp.tools.projects import PROJECT_TOOLS
from film_pipeline.mcp.tools.providers import (
    check_provider_health,
    list_providers,
    resolve_provider_block,
)
from film_pipeline.mcp.tools.reference_generation import generate_reference_images
from film_pipeline.mcp.tools.review import approve_phase, request_revision, review_phase_artifacts
from film_pipeline.mcp.tools.spec import ToolContract, ToolGroup, ToolHandler
from film_pipeline.mcp.tools.state import (
    STATE_TOOLS,
)
from film_pipeline.mcp.tools.validation import (
    RUN_VALIDATION,
    VALIDATION_TOOLS,
)


def _tool_contract(
    name: str,
    group: ToolGroup,
    *,
    mutates: bool = False,
    confirm: bool = False,
    active_project: bool = False,
    checkpoint: bool = False,
) -> ToolContract:
    """Return the standard contract declared for every tool."""
    return ToolContract(
        name=name,
        description=f"MCP tool: {name}",
        group=group,
        mutates_state=mutates,
        requires_confirmation=confirm,
        requires_active_project=active_project,
        creates_checkpoint=checkpoint,
    )


def _register(
    registry: ToolRegistry,
    name: str,
    group: ToolGroup,
    handler: ToolHandler,
    *,
    mutates: bool = False,
    confirm: bool = False,
    active_project: bool = False,
    checkpoint: bool = False,
) -> None:
    """Register ``handler`` under the standard contract for ``name``."""
    registry.register(
        _tool_contract(
            name,
            group,
            mutates=mutates,
            confirm=confirm,
            active_project=active_project,
            checkpoint=checkpoint,
        ),
        handler,
    )


def register_all_tools(registry: ToolRegistry) -> None:
    """Register every MCP tool contract with its handler on ``registry``."""
    # project
    for spec in PROJECT_TOOLS:
        registry.register_spec(spec)

    # intake
    _register(
        registry,
        "submit_idea",
        ToolGroup.INTAKE,
        submit_idea,
        mutates=True,
        active_project=True,
    )
    _register(
        registry,
        "get_intake_analysis",
        ToolGroup.INTAKE,
        get_intake_analysis,
        active_project=True,
    )
    _register(
        registry,
        "approve_intake",
        ToolGroup.INTAKE,
        approve_intake,
        mutates=True,
        confirm=True,
        active_project=True,
    )

    # state
    for spec in STATE_TOOLS:
        registry.register_spec(spec)

    # review
    _register(
        registry,
        "review_phase_artifacts",
        ToolGroup.REVIEW,
        review_phase_artifacts,
        active_project=True,
    )
    _register(
        registry,
        "approve_phase",
        ToolGroup.REVIEW,
        approve_phase,
        mutates=True,
        confirm=True,
        checkpoint=True,
    )
    _register(
        registry,
        "request_revision",
        ToolGroup.REVIEW,
        request_revision,
        mutates=True,
        confirm=True,
    )

    # artifact
    for spec in ARTIFACT_TOOLS:
        registry.register_spec(spec)

    # validation
    for spec in VALIDATION_TOOLS:
        registry.register_spec(spec)

    # generation
    for spec in GENERATION_PLANNING_TOOLS:
        registry.register_spec(spec)
    for spec in GENERATION_DISPATCH_TOOLS:
        registry.register_spec(spec)
    for spec in GENERATION_STATUS_TOOLS:
        registry.register_spec(spec)
    for spec in BIBLE_TOOLS:
        registry.register_spec(spec)
    _register(
        registry,
        "generate_plan",
        ToolGroup.GENERATION,
        generate_plan,
        mutates=True,
        active_project=True,
    )
    # Registered in its historical slot so per-group registration order is unchanged.
    registry.register_spec(RUN_VALIDATION)
    _register(
        registry,
        "generate_reference_images",
        ToolGroup.GENERATION,
        generate_reference_images,
        mutates=True,
    )
    for spec in GENERATION_PROMOTE_TOOLS:
        registry.register_spec(spec)
    # kb
    for spec in KB_TOOLS:
        registry.register_spec(spec)

    # checkpoint
    for spec in CHECKPOINT_TOOLS:
        registry.register_spec(spec)

    # operator
    _register(
        registry,
        "add_operator_comment",
        ToolGroup.OPERATOR,
        add_operator_comment,
        mutates=True,
        active_project=True,
    )
    _register(
        registry,
        "list_operator_comments",
        ToolGroup.OPERATOR,
        list_operator_comments,
        active_project=True,
    )

    # audit
    for spec in AUDIT_TOOLS:
        registry.register_spec(spec)

    # provider
    _register(registry, "check_provider_health", ToolGroup.PROVIDER, check_provider_health)
    _register(
        registry,
        "resolve_provider_block",
        ToolGroup.PROVIDER,
        resolve_provider_block,
        mutates=True,
    )
    _register(registry, "list_providers", ToolGroup.PROVIDER, list_providers)

    # config / profile
    _register(registry, "list_profiles", ToolGroup.CONFIG, list_profiles)
    _register(registry, "inspect_profile", ToolGroup.CONFIG, inspect_profile)
    _register(registry, "get_runtime_mode", ToolGroup.CONFIG, get_runtime_mode)
    _register(
        registry,
        "propose_profile_change",
        ToolGroup.CONFIG,
        propose_profile_change,
        mutates=True,
        active_project=True,
    )
    _register(
        registry,
        "approve_profile_change",
        ToolGroup.CONFIG,
        approve_profile_change,
        mutates=True,
        confirm=True,
        active_project=True,
    )

    # coverage
    _register(
        registry, "plan_coverage_group", ToolGroup.COVERAGE, plan_coverage_group, mutates=True
    )
    _register(registry, "list_coverage_groups", ToolGroup.COVERAGE, list_coverage_groups)
    _register(registry, "inspect_coverage_group", ToolGroup.COVERAGE, inspect_coverage_group)
    _register(
        registry,
        "approve_coverage_generation",
        ToolGroup.COVERAGE,
        approve_coverage_generation,
        mutates=True,
        confirm=True,
    )

    # assembly
    _register(
        registry,
        "assemble_review_cut",
        ToolGroup.ASSEMBLY,
        assemble_review_cut,
        mutates=True,
        active_project=True,
    )
    _register(registry, "assemble_final_cut", ToolGroup.ASSEMBLY, assemble_final_cut, mutates=True)
    _register(
        registry,
        "export_delivery_package",
        ToolGroup.ASSEMBLY,
        export_delivery_package,
        mutates=True,
        confirm=True,
        active_project=True,
    )


__all__ = ["register_all_tools"]
