"""Tool implementations and the registration entry point.

Every tool function takes a dict of arguments (including ``_envelope``) and
returns a serializable dict result. Key tools are wired to the runtime
backend; remaining tools return stubs pending full Phase 05+ wiring.

This package was split from a single monolithic module into per-concern
submodules. This file remains a thin facade so existing call sites
(``from film_pipeline.mcp.tools import register_all_tools``) keep working
unchanged.
"""

from __future__ import annotations

# NOTE: ``get_runtime`` must be bound on this package *before* importing
# ``registry`` (and transitively every tool submodule). Submodules import
# ``get_runtime`` back from this package (rather than directly from
# ``film_pipeline.app.runtime``) so that tests which do
# ``monkeypatch.setattr(film_pipeline.mcp.tools, "get_runtime", ...)``
# continue to affect every tool function, exactly as they did when all
# tools lived in this single module.
from film_pipeline.app.runtime import get_runtime

# Re-export every public tool function so ``from film_pipeline.mcp.tools
# import <tool_name>`` keeps working for callers/tests that import tools
# directly from the package, as they did before the split.
from film_pipeline.mcp.tools.artifacts import (
    inspect_artifact,
    inspect_reference,
    inspect_scene,
    inspect_shot,
    list_artifacts,
    list_shots,
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
from film_pipeline.mcp.tools.audit import (
    explain_agent_routing,
    explain_kb_context,
    explain_last_decision,
    get_audit_log,
)
from film_pipeline.mcp.tools.bibles import (
    generate_camera_bible,
    generate_character_bible,
    generate_environment_bible,
    generate_shot_bible,
    generate_style_bible,
)
from film_pipeline.mcp.tools.checkpoints import (
    compare_versions,
    create_checkpoint,
    get_checkpoint,
    get_invalidation_report,
    list_artifact_versions,
    list_checkpoints,
    rollback_artifact,
    rollback_to_checkpoint,
)
from film_pipeline.mcp.tools.config import get_runtime_mode, inspect_profile, list_profiles
from film_pipeline.mcp.tools.generation import (
    approve_generation_spend,
    cancel_generation_request,
    get_generation_status,
    list_active_generations,
    plan_generation_batch,
    promote_test_to_production,
    resume_generation_polling,
    start_generation_batch,
)
from film_pipeline.mcp.tools.intake import approve_intake, get_intake_analysis, submit_idea
from film_pipeline.mcp.tools.kb import (
    kb_explain_context_choice,
    kb_get_context_packet,
    kb_get_item,
    kb_search,
)
from film_pipeline.mcp.tools.planning import generate_plan, initialize_budget
from film_pipeline.mcp.tools.projects import (
    create_film_project,
    find_project,
    get_active_project,
    get_project_summary,
    list_projects,
    set_active_project,
)
from film_pipeline.mcp.tools.providers import (
    check_provider_health,
    list_providers,
    resolve_provider_block,
)
from film_pipeline.mcp.tools.reference_generation import generate_reference_images
from film_pipeline.mcp.tools.registry import register_all_tools
from film_pipeline.mcp.tools.review import approve_phase, request_revision, review_phase_artifacts
from film_pipeline.mcp.tools.state import (
    get_blockers,
    get_current_phase,
    get_film_state,
    get_next_actions,
    get_orchestrator_summary,
)
from film_pipeline.mcp.tools.validation import (
    get_validation_report,
    list_validation_issues,
    run_validation,
)

__all__ = [
    "approve_coverage_generation",
    "approve_generation_spend",
    "approve_intake",
    "approve_phase",
    "assemble_final_cut",
    "assemble_review_cut",
    "cancel_generation_request",
    "check_provider_health",
    "compare_versions",
    "create_checkpoint",
    "create_film_project",
    "explain_agent_routing",
    "explain_kb_context",
    "explain_last_decision",
    "export_delivery_package",
    "find_project",
    "generate_camera_bible",
    "generate_character_bible",
    "generate_environment_bible",
    "generate_plan",
    "generate_reference_images",
    "generate_shot_bible",
    "generate_style_bible",
    "get_active_project",
    "get_audit_log",
    "get_blockers",
    "get_checkpoint",
    "get_current_phase",
    "get_film_state",
    "get_generation_status",
    "get_intake_analysis",
    "get_invalidation_report",
    "get_next_actions",
    "get_orchestrator_summary",
    "get_project_summary",
    "get_runtime",
    "get_runtime_mode",
    "get_validation_report",
    "initialize_budget",
    "inspect_artifact",
    "inspect_coverage_group",
    "inspect_profile",
    "inspect_reference",
    "inspect_scene",
    "inspect_shot",
    "kb_explain_context_choice",
    "kb_get_context_packet",
    "kb_get_item",
    "kb_search",
    "list_active_generations",
    "list_artifact_versions",
    "list_artifacts",
    "list_checkpoints",
    "list_coverage_groups",
    "list_profiles",
    "list_projects",
    "list_providers",
    "list_shots",
    "list_validation_issues",
    "plan_coverage_group",
    "plan_generation_batch",
    "promote_test_to_production",
    "register_all_tools",
    "request_revision",
    "resolve_provider_block",
    "resume_generation_polling",
    "review_phase_artifacts",
    "rollback_artifact",
    "rollback_to_checkpoint",
    "run_validation",
    "set_active_project",
    "start_generation_batch",
    "submit_idea",
]
