"""Tool registration entry point — wires every tool from every submodule."""

from __future__ import annotations

from film_pipeline.mcp.contract import ToolContract, ToolGroup, ToolRegistry

from .artifacts import (
    inspect_artifact,
    inspect_reference,
    inspect_scene,
    inspect_shot,
    list_artifacts,
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
from .validation import get_validation_report, list_validation_issues, run_validation


def _make(
    name: str,
    group: ToolGroup,
    handler: object,
    *,
    mutates: bool = False,
    confirm: bool = False,
    checkpoint: bool = False,
) -> ToolContract:
    return ToolContract(
        name=name,
        description=f"MCP tool: {name}",
        group=group,
        mutates_state=mutates,
        requires_confirmation=confirm,
        creates_checkpoint=checkpoint,
    )


def register_all_tools(registry: ToolRegistry) -> None:
    # project
    registry.register(
        _make("create_film_project", ToolGroup.PROJECT, create_film_project, mutates=True),
        create_film_project,
    )
    registry.register(_make("list_projects", ToolGroup.PROJECT, list_projects), list_projects)
    registry.register(_make("find_project", ToolGroup.PROJECT, find_project), find_project)
    registry.register(
        _make("set_active_project", ToolGroup.PROJECT, set_active_project, mutates=True),
        set_active_project,
    )
    registry.register(
        _make("get_active_project", ToolGroup.PROJECT, get_active_project), get_active_project
    )
    registry.register(
        _make("get_project_summary", ToolGroup.PROJECT, get_project_summary), get_project_summary
    )

    # intake
    registry.register(
        _make("submit_idea", ToolGroup.INTAKE, submit_idea, mutates=True), submit_idea
    )
    registry.register(
        _make("get_intake_analysis", ToolGroup.INTAKE, get_intake_analysis), get_intake_analysis
    )
    registry.register(
        _make("approve_intake", ToolGroup.INTAKE, approve_intake, mutates=True, confirm=True),
        approve_intake,
    )

    # state
    registry.register(
        _make("get_current_phase", ToolGroup.STATE, get_current_phase), get_current_phase
    )
    registry.register(_make("get_film_state", ToolGroup.STATE, get_film_state), get_film_state)
    registry.register(
        _make("get_orchestrator_summary", ToolGroup.STATE, get_orchestrator_summary),
        get_orchestrator_summary,
    )
    registry.register(
        _make("get_next_actions", ToolGroup.STATE, get_next_actions), get_next_actions
    )
    registry.register(_make("get_blockers", ToolGroup.STATE, get_blockers), get_blockers)

    # review
    registry.register(
        _make("review_phase_artifacts", ToolGroup.REVIEW, review_phase_artifacts),
        review_phase_artifacts,
    )
    registry.register(
        _make(
            "approve_phase",
            ToolGroup.REVIEW,
            approve_phase,
            mutates=True,
            confirm=True,
            checkpoint=True,
        ),
        approve_phase,
    )
    registry.register(
        _make("request_revision", ToolGroup.REVIEW, request_revision, mutates=True, confirm=True),
        request_revision,
    )

    # artifact
    registry.register(_make("list_artifacts", ToolGroup.ARTIFACT, list_artifacts), list_artifacts)
    registry.register(
        _make("inspect_artifact", ToolGroup.ARTIFACT, inspect_artifact), inspect_artifact
    )
    registry.register(_make("list_shots", ToolGroup.ARTIFACT, list_shots), list_shots)
    registry.register(_make("inspect_shot", ToolGroup.ARTIFACT, inspect_shot), inspect_shot)
    registry.register(_make("inspect_scene", ToolGroup.ARTIFACT, inspect_scene), inspect_scene)
    registry.register(
        _make("inspect_reference", ToolGroup.ARTIFACT, inspect_reference), inspect_reference
    )

    # validation
    registry.register(
        _make("get_validation_report", ToolGroup.VALIDATION, get_validation_report),
        get_validation_report,
    )
    registry.register(
        _make("list_validation_issues", ToolGroup.VALIDATION, list_validation_issues),
        list_validation_issues,
    )

    # generation
    registry.register(
        _make("plan_generation_batch", ToolGroup.GENERATION, plan_generation_batch),
        plan_generation_batch,
    )
    registry.register(
        _make(
            "preview_generation_prompts",
            ToolGroup.GENERATION,
            preview_generation_prompts,
        ),
        preview_generation_prompts,
    )
    registry.register(
        _make(
            "generate_character_bible",
            ToolGroup.GENERATION,
            generate_character_bible,
            mutates=True,
        ),
        generate_character_bible,
    )
    registry.register(
        _make(
            "generate_environment_bible",
            ToolGroup.GENERATION,
            generate_environment_bible,
            mutates=True,
        ),
        generate_environment_bible,
    )
    registry.register(
        _make(
            "generate_camera_bible",
            ToolGroup.GENERATION,
            generate_camera_bible,
            mutates=True,
        ),
        generate_camera_bible,
    )
    registry.register(
        _make(
            "generate_style_bible",
            ToolGroup.GENERATION,
            generate_style_bible,
            mutates=True,
        ),
        generate_style_bible,
    )
    registry.register(
        _make(
            "generate_shot_bible",
            ToolGroup.GENERATION,
            generate_shot_bible,
            mutates=True,
        ),
        generate_shot_bible,
    )
    registry.register(
        _make(
            "initialize_budget",
            ToolGroup.GENERATION,
            initialize_budget,
            mutates=True,
        ),
        initialize_budget,
    )
    registry.register(
        _make(
            "generate_plan",
            ToolGroup.GENERATION,
            generate_plan,
            mutates=True,
        ),
        generate_plan,
    )
    registry.register(
        _make("run_validation", ToolGroup.VALIDATION, run_validation, mutates=True),
        run_validation,
    )
    registry.register(
        _make(
            "generate_reference_images",
            ToolGroup.GENERATION,
            generate_reference_images,
            mutates=True,
        ),
        generate_reference_images,
    )
    registry.register(
        _make(
            "approve_generation_spend",
            ToolGroup.GENERATION,
            approve_generation_spend,
            mutates=True,
            confirm=True,
        ),
        approve_generation_spend,
    )
    registry.register(
        _make("start_generation_batch", ToolGroup.GENERATION, start_generation_batch, mutates=True),
        start_generation_batch,
    )
    registry.register(
        _make("get_generation_status", ToolGroup.GENERATION, get_generation_status),
        get_generation_status,
    )
    registry.register(
        _make(
            "resume_generation_polling",
            ToolGroup.GENERATION,
            resume_generation_polling,
            mutates=True,
        ),
        resume_generation_polling,
    )
    registry.register(
        _make("list_active_generations", ToolGroup.GENERATION, list_active_generations),
        list_active_generations,
    )
    registry.register(
        _make(
            "cancel_generation_request",
            ToolGroup.GENERATION,
            cancel_generation_request,
            mutates=True,
        ),
        cancel_generation_request,
    )
    registry.register(
        _make(
            "promote_test_to_production",
            ToolGroup.GENERATION,
            promote_test_to_production,
            mutates=True,
            confirm=True,
        ),
        promote_test_to_production,
    )

    # kb
    registry.register(_make("kb_search", ToolGroup.KB, kb_search), kb_search)
    registry.register(_make("kb_get_item", ToolGroup.KB, kb_get_item), kb_get_item)
    registry.register(
        _make("kb_get_context_packet", ToolGroup.KB, kb_get_context_packet), kb_get_context_packet
    )
    registry.register(
        _make("kb_explain_context_choice", ToolGroup.KB, kb_explain_context_choice),
        kb_explain_context_choice,
    )

    # checkpoint
    registry.register(
        _make("list_checkpoints", ToolGroup.CHECKPOINT, list_checkpoints), list_checkpoints
    )
    registry.register(
        _make("create_checkpoint", ToolGroup.CHECKPOINT, create_checkpoint, mutates=True),
        create_checkpoint,
    )
    registry.register(_make("get_checkpoint", ToolGroup.CHECKPOINT, get_checkpoint), get_checkpoint)
    registry.register(
        _make("compare_versions", ToolGroup.CHECKPOINT, compare_versions), compare_versions
    )
    registry.register(
        _make("list_artifact_versions", ToolGroup.CHECKPOINT, list_artifact_versions),
        list_artifact_versions,
    )
    registry.register(
        _make(
            "rollback_artifact", ToolGroup.CHECKPOINT, rollback_artifact, mutates=True, confirm=True
        ),
        rollback_artifact,
    )
    registry.register(
        _make(
            "rollback_to_checkpoint",
            ToolGroup.CHECKPOINT,
            rollback_to_checkpoint,
            mutates=True,
            confirm=True,
        ),
        rollback_to_checkpoint,
    )
    registry.register(
        _make("get_invalidation_report", ToolGroup.CHECKPOINT, get_invalidation_report),
        get_invalidation_report,
    )

    # operator
    registry.register(
        _make("add_operator_comment", ToolGroup.OPERATOR, add_operator_comment, mutates=True),
        add_operator_comment,
    )
    registry.register(
        _make("list_operator_comments", ToolGroup.OPERATOR, list_operator_comments),
        list_operator_comments,
    )

    # audit
    registry.register(_make("get_audit_log", ToolGroup.AUDIT, get_audit_log), get_audit_log)
    registry.register(
        _make("explain_last_decision", ToolGroup.AUDIT, explain_last_decision),
        explain_last_decision,
    )
    registry.register(
        _make("explain_agent_routing", ToolGroup.AUDIT, explain_agent_routing),
        explain_agent_routing,
    )
    registry.register(
        _make("explain_kb_context", ToolGroup.AUDIT, explain_kb_context), explain_kb_context
    )

    # provider
    registry.register(
        _make("check_provider_health", ToolGroup.PROVIDER, check_provider_health),
        check_provider_health,
    )
    registry.register(
        _make("resolve_provider_block", ToolGroup.PROVIDER, resolve_provider_block, mutates=True),
        resolve_provider_block,
    )
    registry.register(_make("list_providers", ToolGroup.PROVIDER, list_providers), list_providers)

    # config / profile
    registry.register(_make("list_profiles", ToolGroup.CONFIG, list_profiles), list_profiles)
    registry.register(_make("inspect_profile", ToolGroup.CONFIG, inspect_profile), inspect_profile)
    registry.register(
        _make("get_runtime_mode", ToolGroup.CONFIG, get_runtime_mode), get_runtime_mode
    )
    registry.register(
        _make(
            "propose_profile_change",
            ToolGroup.CONFIG,
            propose_profile_change,
            mutates=True,
        ),
        propose_profile_change,
    )
    registry.register(
        _make(
            "approve_profile_change",
            ToolGroup.CONFIG,
            approve_profile_change,
            mutates=True,
            confirm=True,
        ),
        approve_profile_change,
    )

    # coverage
    registry.register(
        _make("plan_coverage_group", ToolGroup.COVERAGE, plan_coverage_group, mutates=True),
        plan_coverage_group,
    )
    registry.register(
        _make("list_coverage_groups", ToolGroup.COVERAGE, list_coverage_groups),
        list_coverage_groups,
    )
    registry.register(
        _make("inspect_coverage_group", ToolGroup.COVERAGE, inspect_coverage_group),
        inspect_coverage_group,
    )
    registry.register(
        _make(
            "approve_coverage_generation",
            ToolGroup.COVERAGE,
            approve_coverage_generation,
            mutates=True,
            confirm=True,
        ),
        approve_coverage_generation,
    )

    # assembly
    registry.register(
        _make("assemble_review_cut", ToolGroup.ASSEMBLY, assemble_review_cut, mutates=True),
        assemble_review_cut,
    )
    registry.register(
        _make("assemble_final_cut", ToolGroup.ASSEMBLY, assemble_final_cut, mutates=True),
        assemble_final_cut,
    )
    registry.register(
        _make(
            "export_delivery_package",
            ToolGroup.ASSEMBLY,
            export_delivery_package,
            mutates=True,
            confirm=True,
        ),
        export_delivery_package,
    )


__all__ = ["register_all_tools"]
