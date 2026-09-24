"""Tool registration entry point — wires every tool from every submodule."""

from __future__ import annotations

from film_pipeline.mcp.contract import (
    ToolContract,
    ToolGroup,
    ToolHandler,
    ToolRegistry,
)

from .artifacts import (
    inspect_artifact,
    inspect_reference,
    inspect_scene,
    inspect_shot,
    list_artifacts,
    list_assets,
    list_shots,
)
from .assembly import (
    approve_coverage_generation,
    assemble_final_cut,
    assemble_review_cut,
    export_delivery_package,
    inspect_coverage_group,
    list_coverage_groups,
    plan_coverage_group,
)
from .audit import (
    explain_agent_routing,
    explain_kb_context,
    explain_last_decision,
    get_audit_log,
)
from .bibles import (
    generate_camera_bible,
    generate_character_bible,
    generate_environment_bible,
    generate_shot_bible,
    generate_style_bible,
)
from .checkpoints import (
    compare_versions,
    create_checkpoint,
    get_checkpoint,
    get_invalidation_report,
    list_artifact_versions,
    list_checkpoints,
    rollback_artifact,
    rollback_to_checkpoint,
)
from .config import (
    approve_profile_change,
    get_runtime_mode,
    inspect_profile,
    list_profiles,
    propose_profile_change,
)
from .generation import (
    approve_generation_spend,
    cancel_generation_request,
    get_generation_status,
    list_active_generations,
    plan_generation_batch,
    preview_generation_prompts,
    promote_test_to_production,
    resume_generation_polling,
    start_generation_batch,
)
from .intake import approve_intake, get_intake_analysis, submit_idea
from .kb import (
    kb_explain_context_choice,
    kb_get_context_packet,
    kb_get_item,
    kb_search,
)
from .operator import add_operator_comment, list_operator_comments
from .planning import generate_plan, initialize_budget
from .projects import (
    create_film_project,
    find_project,
    get_active_project,
    get_project_summary,
    list_projects,
    set_active_project,
)
from .providers import check_provider_health, list_providers, resolve_provider_block
from .reference_generation import generate_reference_images
from .review import approve_phase, request_revision, review_phase_artifacts
from .state import (
    get_blockers,
    get_current_phase,
    get_film_state,
    get_next_actions,
    get_orchestrator_summary,
)
from .storage import storage_migrate
from .validation import get_validation_report, list_validation_issues, run_validation


def _tool_contract(
    name: str,
    group: ToolGroup,
    *,
    mutates: bool = False,
    confirm: bool = False,
    checkpoint: bool = False,
) -> ToolContract:
    """Return the standard contract declared for every tool."""
    return ToolContract(
        name=name,
        description=f"MCP tool: {name}",
        group=group,
        mutates_state=mutates,
        requires_confirmation=confirm,
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
    checkpoint: bool = False,
) -> None:
    """Register ``handler`` under the standard contract for ``name``."""
    registry.register(
        _tool_contract(name, group, mutates=mutates, confirm=confirm, checkpoint=checkpoint),
        handler,
    )


def register_all_tools(registry: ToolRegistry) -> None:
    """Register every MCP tool contract with its handler on ``registry``."""
    # project
    _register(registry, "create_film_project", ToolGroup.PROJECT, create_film_project, mutates=True)
    _register(registry, "list_projects", ToolGroup.PROJECT, list_projects)
    _register(registry, "find_project", ToolGroup.PROJECT, find_project)
    _register(registry, "set_active_project", ToolGroup.PROJECT, set_active_project, mutates=True)
    _register(registry, "get_active_project", ToolGroup.PROJECT, get_active_project)
    _register(registry, "get_project_summary", ToolGroup.PROJECT, get_project_summary)

    # intake
    _register(registry, "submit_idea", ToolGroup.INTAKE, submit_idea, mutates=True)
    _register(registry, "get_intake_analysis", ToolGroup.INTAKE, get_intake_analysis)
    _register(
        registry, "approve_intake", ToolGroup.INTAKE, approve_intake, mutates=True, confirm=True
    )

    # state
    _register(registry, "get_current_phase", ToolGroup.STATE, get_current_phase)
    _register(registry, "get_film_state", ToolGroup.STATE, get_film_state)
    _register(registry, "get_orchestrator_summary", ToolGroup.STATE, get_orchestrator_summary)
    _register(registry, "get_next_actions", ToolGroup.STATE, get_next_actions)
    _register(registry, "get_blockers", ToolGroup.STATE, get_blockers)

    # review
    _register(registry, "review_phase_artifacts", ToolGroup.REVIEW, review_phase_artifacts)
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
    _register(registry, "list_artifacts", ToolGroup.ARTIFACT, list_artifacts)
    _register(registry, "inspect_artifact", ToolGroup.ARTIFACT, inspect_artifact)
    _register(registry, "list_assets", ToolGroup.ARTIFACT, list_assets)
    _register(registry, "list_shots", ToolGroup.ARTIFACT, list_shots)
    _register(registry, "inspect_shot", ToolGroup.ARTIFACT, inspect_shot)
    _register(registry, "inspect_scene", ToolGroup.ARTIFACT, inspect_scene)
    _register(registry, "inspect_reference", ToolGroup.ARTIFACT, inspect_reference)

    # validation
    _register(registry, "get_validation_report", ToolGroup.VALIDATION, get_validation_report)
    _register(registry, "list_validation_issues", ToolGroup.VALIDATION, list_validation_issues)

    # generation
    _register(registry, "plan_generation_batch", ToolGroup.GENERATION, plan_generation_batch)
    _register(
        registry,
        "preview_generation_prompts",
        ToolGroup.GENERATION,
        preview_generation_prompts,
    )
    _register(
        registry,
        "generate_character_bible",
        ToolGroup.GENERATION,
        generate_character_bible,
        mutates=True,
    )
    _register(
        registry,
        "generate_environment_bible",
        ToolGroup.GENERATION,
        generate_environment_bible,
        mutates=True,
    )
    _register(
        registry,
        "generate_camera_bible",
        ToolGroup.GENERATION,
        generate_camera_bible,
        mutates=True,
    )
    _register(
        registry,
        "generate_style_bible",
        ToolGroup.GENERATION,
        generate_style_bible,
        mutates=True,
    )
    _register(
        registry,
        "generate_shot_bible",
        ToolGroup.GENERATION,
        generate_shot_bible,
        mutates=True,
    )
    _register(registry, "initialize_budget", ToolGroup.GENERATION, initialize_budget, mutates=True)
    _register(registry, "generate_plan", ToolGroup.GENERATION, generate_plan, mutates=True)
    # Registered in its historical slot so per-group registration order is unchanged.
    _register(registry, "run_validation", ToolGroup.VALIDATION, run_validation, mutates=True)
    _register(
        registry,
        "generate_reference_images",
        ToolGroup.GENERATION,
        generate_reference_images,
        mutates=True,
    )
    _register(
        registry,
        "approve_generation_spend",
        ToolGroup.GENERATION,
        approve_generation_spend,
        mutates=True,
        confirm=True,
    )
    _register(
        registry,
        "start_generation_batch",
        ToolGroup.GENERATION,
        start_generation_batch,
        mutates=True,
    )
    _register(registry, "get_generation_status", ToolGroup.GENERATION, get_generation_status)
    _register(
        registry,
        "resume_generation_polling",
        ToolGroup.GENERATION,
        resume_generation_polling,
        mutates=True,
    )
    _register(registry, "list_active_generations", ToolGroup.GENERATION, list_active_generations)
    _register(
        registry,
        "cancel_generation_request",
        ToolGroup.GENERATION,
        cancel_generation_request,
        mutates=True,
    )
    _register(
        registry,
        "promote_test_to_production",
        ToolGroup.GENERATION,
        promote_test_to_production,
        mutates=True,
        confirm=True,
    )

    # kb
    _register(registry, "kb_search", ToolGroup.KB, kb_search)
    _register(registry, "kb_get_item", ToolGroup.KB, kb_get_item)
    _register(registry, "kb_get_context_packet", ToolGroup.KB, kb_get_context_packet)
    _register(registry, "kb_explain_context_choice", ToolGroup.KB, kb_explain_context_choice)

    # checkpoint
    _register(registry, "list_checkpoints", ToolGroup.CHECKPOINT, list_checkpoints)
    _register(registry, "create_checkpoint", ToolGroup.CHECKPOINT, create_checkpoint, mutates=True)
    _register(registry, "get_checkpoint", ToolGroup.CHECKPOINT, get_checkpoint)
    _register(registry, "compare_versions", ToolGroup.CHECKPOINT, compare_versions)
    _register(registry, "list_artifact_versions", ToolGroup.CHECKPOINT, list_artifact_versions)
    _register(
        registry,
        "rollback_artifact",
        ToolGroup.CHECKPOINT,
        rollback_artifact,
        mutates=True,
        confirm=True,
    )
    _register(
        registry,
        "storage_migrate",
        ToolGroup.ARTIFACT,
        storage_migrate,
        mutates=True,
        confirm=True,
    )
    _register(
        registry,
        "rollback_to_checkpoint",
        ToolGroup.CHECKPOINT,
        rollback_to_checkpoint,
        mutates=True,
        confirm=True,
    )
    _register(registry, "get_invalidation_report", ToolGroup.CHECKPOINT, get_invalidation_report)

    # operator
    _register(
        registry, "add_operator_comment", ToolGroup.OPERATOR, add_operator_comment, mutates=True
    )
    _register(registry, "list_operator_comments", ToolGroup.OPERATOR, list_operator_comments)

    # audit
    _register(registry, "get_audit_log", ToolGroup.AUDIT, get_audit_log)
    _register(registry, "explain_last_decision", ToolGroup.AUDIT, explain_last_decision)
    _register(registry, "explain_agent_routing", ToolGroup.AUDIT, explain_agent_routing)
    _register(registry, "explain_kb_context", ToolGroup.AUDIT, explain_kb_context)

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
        registry, "propose_profile_change", ToolGroup.CONFIG, propose_profile_change, mutates=True
    )
    _register(
        registry,
        "approve_profile_change",
        ToolGroup.CONFIG,
        approve_profile_change,
        mutates=True,
        confirm=True,
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
        registry, "assemble_review_cut", ToolGroup.ASSEMBLY, assemble_review_cut, mutates=True
    )
    _register(registry, "assemble_final_cut", ToolGroup.ASSEMBLY, assemble_final_cut, mutates=True)
    _register(
        registry,
        "export_delivery_package",
        ToolGroup.ASSEMBLY,
        export_delivery_package,
        mutates=True,
        confirm=True,
    )


__all__ = ["register_all_tools"]
