"""Tool export facade with lazy handlers and the runtime injection hook.

Handlers are imported on first use so registration never imports a tool package
while that package is initializing. The public names and callable identities
stay the same as the original eager facade.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from film_pipeline.studio.runtime import get_runtime as get_runtime

_TOOL_MODULES: dict[str, str] = {
    "add_operator_comment": "film_pipeline.mcp.tools.operator",
    "approve_coverage_generation": "film_pipeline.mcp.tools.assembly",
    "approve_generation_spend": "film_pipeline.mcp.tools.generation",
    "approve_intake": "film_pipeline.mcp.tools.intake",
    "approve_phase": "film_pipeline.mcp.tools.review",
    "approve_profile_change": "film_pipeline.mcp.tools.config",
    "assemble_final_cut": "film_pipeline.mcp.tools.assembly",
    "assemble_review_cut": "film_pipeline.mcp.tools.assembly",
    "cancel_generation_request": "film_pipeline.mcp.tools.generation",
    "check_provider_health": "film_pipeline.mcp.tools.providers",
    "compare_versions": "film_pipeline.mcp.tools.checkpoints",
    "create_checkpoint": "film_pipeline.mcp.tools.checkpoints",
    "create_film_project": "film_pipeline.mcp.tools.projects",
    "explain_agent_routing": "film_pipeline.mcp.tools.audit",
    "explain_kb_context": "film_pipeline.mcp.tools.audit",
    "explain_last_decision": "film_pipeline.mcp.tools.audit",
    "export_delivery_package": "film_pipeline.mcp.tools.assembly",
    "find_project": "film_pipeline.mcp.tools.projects",
    "generate_camera_bible": "film_pipeline.mcp.tools.bibles",
    "generate_character_bible": "film_pipeline.mcp.tools.bibles",
    "generate_environment_bible": "film_pipeline.mcp.tools.bibles",
    "generate_plan": "film_pipeline.mcp.tools.planning",
    "generate_reference_images": "film_pipeline.mcp.tools.reference_generation",
    "generate_shot_bible": "film_pipeline.mcp.tools.bibles",
    "generate_style_bible": "film_pipeline.mcp.tools.bibles",
    "get_active_project": "film_pipeline.mcp.tools.projects",
    "get_audit_log": "film_pipeline.mcp.tools.audit",
    "get_blockers": "film_pipeline.mcp.tools.state",
    "get_checkpoint": "film_pipeline.mcp.tools.checkpoints",
    "get_current_phase": "film_pipeline.mcp.tools.state",
    "get_film_state": "film_pipeline.mcp.tools.state",
    "get_generation_status": "film_pipeline.mcp.tools.generation",
    "get_intake_analysis": "film_pipeline.mcp.tools.intake",
    "get_invalidation_report": "film_pipeline.mcp.tools.checkpoints",
    "get_next_actions": "film_pipeline.mcp.tools.state",
    "get_orchestrator_summary": "film_pipeline.mcp.tools.state",
    "get_project_summary": "film_pipeline.mcp.tools.projects",
    "get_runtime_mode": "film_pipeline.mcp.tools.config",
    "get_validation_report": "film_pipeline.mcp.tools.validation",
    "initialize_budget": "film_pipeline.mcp.tools.planning",
    "inspect_artifact": "film_pipeline.mcp.tools.artifacts",
    "inspect_coverage_group": "film_pipeline.mcp.tools.assembly",
    "inspect_profile": "film_pipeline.mcp.tools.config",
    "inspect_reference": "film_pipeline.mcp.tools.artifacts",
    "inspect_scene": "film_pipeline.mcp.tools.artifacts",
    "inspect_shot": "film_pipeline.mcp.tools.artifacts",
    "kb_explain_context_choice": "film_pipeline.mcp.tools.kb",
    "kb_get_context_packet": "film_pipeline.mcp.tools.kb",
    "kb_get_item": "film_pipeline.mcp.tools.kb",
    "kb_search": "film_pipeline.mcp.tools.kb",
    "list_active_generations": "film_pipeline.mcp.tools.generation",
    "list_artifact_versions": "film_pipeline.mcp.tools.checkpoints",
    "list_artifacts": "film_pipeline.mcp.tools.artifacts",
    "list_assets": "film_pipeline.mcp.tools.artifacts",
    "list_checkpoints": "film_pipeline.mcp.tools.checkpoints",
    "list_coverage_groups": "film_pipeline.mcp.tools.assembly",
    "list_operator_comments": "film_pipeline.mcp.tools.operator",
    "list_profiles": "film_pipeline.mcp.tools.config",
    "list_projects": "film_pipeline.mcp.tools.projects",
    "list_providers": "film_pipeline.mcp.tools.providers",
    "list_shots": "film_pipeline.mcp.tools.artifacts",
    "list_validation_issues": "film_pipeline.mcp.tools.validation",
    "plan_coverage_group": "film_pipeline.mcp.tools.assembly",
    "plan_generation_batch": "film_pipeline.mcp.tools.generation",
    "preview_generation_prompts": "film_pipeline.mcp.tools.generation",
    "promote_test_to_production": "film_pipeline.mcp.tools.generation",
    "propose_profile_change": "film_pipeline.mcp.tools.config",
    "register_all_tools": "film_pipeline.mcp.registry",
    "request_revision": "film_pipeline.mcp.tools.review",
    "resolve_provider_block": "film_pipeline.mcp.tools.providers",
    "resume_generation_polling": "film_pipeline.mcp.tools.generation",
    "review_phase_artifacts": "film_pipeline.mcp.tools.review",
    "rollback_artifact": "film_pipeline.mcp.tools.checkpoints",
    "rollback_to_checkpoint": "film_pipeline.mcp.tools.checkpoints",
    "run_validation": "film_pipeline.mcp.tools.validation",
    "set_active_project": "film_pipeline.mcp.tools.projects",
    "start_generation_batch": "film_pipeline.mcp.tools.generation",
    "submit_idea": "film_pipeline.mcp.tools.intake",
}


def __getattr__(name: str) -> Any:
    module_name = _TOOL_MODULES.get(name)
    if module_name is None:
        raise AttributeError(name)
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_TOOL_MODULES))


__all__ = sorted((*_TOOL_MODULES, "get_runtime"))
