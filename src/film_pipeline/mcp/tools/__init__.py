"""Tool implementations and the registration entry point.

Every tool function takes a dict of arguments (including ``_envelope``) and
returns a serializable dict result. This phase ships *stubs* — Phase 05+
wires them to the orchestrator and artifact store.
"""

from __future__ import annotations

from film_pipeline.mcp.contract import ToolContract, ToolGroup, ToolRegistry


def _stub(handler_name: str, **extra: object) -> dict[str, object]:
    """Build a stub response that callers can detect before Phase 05."""
    return {
        "stub": True,
        "handler": handler_name,
        "message": "Not yet wired to orchestrator (post Phase 05).",
        **extra,
    }


# --- Project tools -------------------------------------------------------


async def create_film_project(args: dict[str, object]) -> dict[str, object]:
    """Create a new film project (stub)."""
    envelope = args.get("_envelope")
    return _stub(
        "create_film_project",
        project_id=args.get("project_id"),
        slug=args.get("slug"),
        title=args.get("title"),
        envelope_request_id=getattr(envelope, "request_id", None),
    )


async def list_projects(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_projects")


async def find_project(args: dict[str, object]) -> dict[str, object]:
    return _stub("find_project", ref=args.get("ref"))


async def set_active_project(args: dict[str, object]) -> dict[str, object]:
    return _stub("set_active_project", project_ref=args.get("project_ref"))


async def get_active_project(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_active_project")


async def get_project_summary(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_project_summary", project_ref=args.get("project_ref"))


# --- Intake tools --------------------------------------------------------


async def submit_idea(args: dict[str, object]) -> dict[str, object]:
    return _stub("submit_idea", project_ref=args.get("project_ref"))


async def get_intake_analysis(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_intake_analysis")


async def approve_intake(args: dict[str, object]) -> dict[str, object]:
    return _stub("approve_intake")


# --- State tools ---------------------------------------------------------


async def get_current_phase(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_current_phase")


async def get_film_state(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_film_state")


async def get_orchestrator_summary(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_orchestrator_summary")


async def get_next_actions(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_next_actions")


async def get_blockers(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_blockers")


# --- Review tools --------------------------------------------------------


async def review_phase_artifacts(args: dict[str, object]) -> dict[str, object]:
    return _stub("review_phase_artifacts", phase=args.get("phase"))


async def approve_phase(args: dict[str, object]) -> dict[str, object]:
    return _stub("approve_phase", phase=args.get("phase"))


async def request_revision(args: dict[str, object]) -> dict[str, object]:
    return _stub("request_revision", phase=args.get("phase"))


# --- Artifact tools ------------------------------------------------------


async def list_artifacts(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_artifacts")


async def inspect_artifact(args: dict[str, object]) -> dict[str, object]:
    return _stub("inspect_artifact", artifact_id=args.get("artifact_id"))


async def list_shots(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_shots")


async def inspect_shot(args: dict[str, object]) -> dict[str, object]:
    return _stub("inspect_shot", shot_id=args.get("shot_id"))


async def inspect_scene(args: dict[str, object]) -> dict[str, object]:
    return _stub("inspect_scene", scene_id=args.get("scene_id"))


async def inspect_reference(args: dict[str, object]) -> dict[str, object]:
    return _stub("inspect_reference", reference_id=args.get("reference_id"))


# --- Validation tools ----------------------------------------------------


async def get_validation_report(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_validation_report")


async def list_validation_issues(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_validation_issues")


# --- Generation tools ----------------------------------------------------


async def plan_generation_batch(args: dict[str, object]) -> dict[str, object]:
    return _stub("plan_generation_batch")


async def approve_generation_spend(args: dict[str, object]) -> dict[str, object]:
    return _stub("approve_generation_spend")


async def start_generation_batch(args: dict[str, object]) -> dict[str, object]:
    return _stub("start_generation_batch")


async def get_generation_status(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_generation_status")


async def resume_generation_polling(args: dict[str, object]) -> dict[str, object]:
    return _stub("resume_generation_polling")


async def list_active_generations(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_active_generations")


async def cancel_generation_request(args: dict[str, object]) -> dict[str, object]:
    return _stub("cancel_generation_request")


async def promote_test_to_production(args: dict[str, object]) -> dict[str, object]:
    return _stub("promote_test_to_production")


# --- KB tools ------------------------------------------------------------


async def kb_search(args: dict[str, object]) -> dict[str, object]:
    return _stub("kb_search", query=args.get("query"))


async def kb_get_item(args: dict[str, object]) -> dict[str, object]:
    return _stub("kb_get_item", item_id=args.get("item_id"))


async def kb_get_context_packet(args: dict[str, object]) -> dict[str, object]:
    return _stub("kb_get_context_packet")


async def kb_explain_context_choice(args: dict[str, object]) -> dict[str, object]:
    return _stub("kb_explain_context_choice")


# --- Checkpoint tools ----------------------------------------------------


async def list_checkpoints(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_checkpoints")


async def create_checkpoint(args: dict[str, object]) -> dict[str, object]:
    return _stub("create_checkpoint")


async def get_checkpoint(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_checkpoint")


async def compare_versions(args: dict[str, object]) -> dict[str, object]:
    return _stub("compare_versions")


async def list_artifact_versions(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_artifact_versions")


async def rollback_artifact(args: dict[str, object]) -> dict[str, object]:
    return _stub("rollback_artifact")


async def rollback_to_checkpoint(args: dict[str, object]) -> dict[str, object]:
    return _stub("rollback_to_checkpoint")


async def get_invalidation_report(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_invalidation_report")


# --- Audit tools ---------------------------------------------------------


async def get_audit_log(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_audit_log")


async def explain_last_decision(args: dict[str, object]) -> dict[str, object]:
    return _stub("explain_last_decision")


async def explain_agent_routing(args: dict[str, object]) -> dict[str, object]:
    return _stub("explain_agent_routing")


async def explain_kb_context(args: dict[str, object]) -> dict[str, object]:
    return _stub("explain_kb_context")


# --- Provider tools ------------------------------------------------------


async def check_provider_health(args: dict[str, object]) -> dict[str, object]:
    return _stub("check_provider_health")


async def resolve_provider_block(args: dict[str, object]) -> dict[str, object]:
    return _stub("resolve_provider_block")


async def list_providers(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_providers")


# --- Coverage tools ------------------------------------------------------


async def plan_coverage_group(args: dict[str, object]) -> dict[str, object]:
    return _stub("plan_coverage_group")


async def list_coverage_groups(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_coverage_groups")


async def inspect_coverage_group(args: dict[str, object]) -> dict[str, object]:
    return _stub("inspect_coverage_group")


async def approve_coverage_generation(args: dict[str, object]) -> dict[str, object]:
    return _stub("approve_coverage_generation")


# --- Assembly tools ------------------------------------------------------


async def assemble_review_cut(args: dict[str, object]) -> dict[str, object]:
    return _stub("assemble_review_cut")


async def assemble_final_cut(args: dict[str, object]) -> dict[str, object]:
    return _stub("assemble_final_cut")


async def export_delivery_package(args: dict[str, object]) -> dict[str, object]:
    return _stub("export_delivery_package")


# --- Registration --------------------------------------------------------


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
