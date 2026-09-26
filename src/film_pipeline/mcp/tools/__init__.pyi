"""Static types for the lazy MCP tool facade."""

from film_pipeline.mcp.registry import register_all_tools as register_all_tools
from film_pipeline.mcp.tools.artifacts import inspect_artifact as inspect_artifact
from film_pipeline.mcp.tools.artifacts import inspect_reference as inspect_reference
from film_pipeline.mcp.tools.artifacts import inspect_scene as inspect_scene
from film_pipeline.mcp.tools.artifacts import inspect_shot as inspect_shot
from film_pipeline.mcp.tools.artifacts import list_artifacts as list_artifacts
from film_pipeline.mcp.tools.artifacts import list_assets as list_assets
from film_pipeline.mcp.tools.artifacts import list_shots as list_shots
from film_pipeline.mcp.tools.assembly import (
    approve_coverage_generation as approve_coverage_generation,
)
from film_pipeline.mcp.tools.assembly import assemble_final_cut as assemble_final_cut
from film_pipeline.mcp.tools.assembly import assemble_review_cut as assemble_review_cut
from film_pipeline.mcp.tools.assembly import export_delivery_package as export_delivery_package
from film_pipeline.mcp.tools.assembly import inspect_coverage_group as inspect_coverage_group
from film_pipeline.mcp.tools.assembly import list_coverage_groups as list_coverage_groups
from film_pipeline.mcp.tools.assembly import plan_coverage_group as plan_coverage_group
from film_pipeline.mcp.tools.audit import explain_agent_routing as explain_agent_routing
from film_pipeline.mcp.tools.audit import explain_kb_context as explain_kb_context
from film_pipeline.mcp.tools.audit import explain_last_decision as explain_last_decision
from film_pipeline.mcp.tools.audit import get_audit_log as get_audit_log
from film_pipeline.mcp.tools.bibles import generate_camera_bible as generate_camera_bible
from film_pipeline.mcp.tools.bibles import generate_character_bible as generate_character_bible
from film_pipeline.mcp.tools.bibles import generate_environment_bible as generate_environment_bible
from film_pipeline.mcp.tools.bibles import generate_shot_bible as generate_shot_bible
from film_pipeline.mcp.tools.bibles import generate_style_bible as generate_style_bible
from film_pipeline.mcp.tools.checkpoints import compare_versions as compare_versions
from film_pipeline.mcp.tools.checkpoints import create_checkpoint as create_checkpoint
from film_pipeline.mcp.tools.checkpoints import get_checkpoint as get_checkpoint
from film_pipeline.mcp.tools.checkpoints import get_invalidation_report as get_invalidation_report
from film_pipeline.mcp.tools.checkpoints import list_artifact_versions as list_artifact_versions
from film_pipeline.mcp.tools.checkpoints import list_checkpoints as list_checkpoints
from film_pipeline.mcp.tools.checkpoints import rollback_artifact as rollback_artifact
from film_pipeline.mcp.tools.checkpoints import rollback_to_checkpoint as rollback_to_checkpoint
from film_pipeline.mcp.tools.config import approve_profile_change as approve_profile_change
from film_pipeline.mcp.tools.config import get_runtime_mode as get_runtime_mode
from film_pipeline.mcp.tools.config import inspect_profile as inspect_profile
from film_pipeline.mcp.tools.config import list_profiles as list_profiles
from film_pipeline.mcp.tools.config import propose_profile_change as propose_profile_change
from film_pipeline.mcp.tools.generation import (
    cancel_generation_request as cancel_generation_request,
)
from film_pipeline.mcp.tools.generation import get_generation_status as get_generation_status
from film_pipeline.mcp.tools.generation import list_active_generations as list_active_generations
from film_pipeline.mcp.tools.generation import plan_generation_batch as plan_generation_batch
from film_pipeline.mcp.tools.generation import (
    preview_generation_prompts as preview_generation_prompts,
)
from film_pipeline.mcp.tools.generation import (
    promote_test_to_production as promote_test_to_production,
)
from film_pipeline.mcp.tools.generation import (
    resume_generation_polling as resume_generation_polling,
)
from film_pipeline.mcp.tools.generation import start_generation_batch as start_generation_batch
from film_pipeline.mcp.tools.intake import approve_intake as approve_intake
from film_pipeline.mcp.tools.intake import get_intake_analysis as get_intake_analysis
from film_pipeline.mcp.tools.intake import submit_idea as submit_idea
from film_pipeline.mcp.tools.kb import kb_explain_context_choice as kb_explain_context_choice
from film_pipeline.mcp.tools.kb import kb_get_context_packet as kb_get_context_packet
from film_pipeline.mcp.tools.kb import kb_get_item as kb_get_item
from film_pipeline.mcp.tools.kb import kb_search as kb_search
from film_pipeline.mcp.tools.operator import add_operator_comment as add_operator_comment
from film_pipeline.mcp.tools.operator import list_operator_comments as list_operator_comments
from film_pipeline.mcp.tools.planning import generate_plan as generate_plan
from film_pipeline.mcp.tools.planning import initialize_budget as initialize_budget
from film_pipeline.mcp.tools.projects import create_film_project as create_film_project
from film_pipeline.mcp.tools.projects import find_project as find_project
from film_pipeline.mcp.tools.projects import get_active_project as get_active_project
from film_pipeline.mcp.tools.projects import get_project_summary as get_project_summary
from film_pipeline.mcp.tools.projects import list_projects as list_projects
from film_pipeline.mcp.tools.projects import set_active_project as set_active_project
from film_pipeline.mcp.tools.providers import check_provider_health as check_provider_health
from film_pipeline.mcp.tools.providers import list_providers as list_providers
from film_pipeline.mcp.tools.providers import resolve_provider_block as resolve_provider_block
from film_pipeline.mcp.tools.reference_generation import (
    generate_reference_images as generate_reference_images,
)
from film_pipeline.mcp.tools.review import approve_phase as approve_phase
from film_pipeline.mcp.tools.review import request_revision as request_revision
from film_pipeline.mcp.tools.review import review_phase_artifacts as review_phase_artifacts
from film_pipeline.mcp.tools.state import get_blockers as get_blockers
from film_pipeline.mcp.tools.state import get_current_phase as get_current_phase
from film_pipeline.mcp.tools.state import get_film_state as get_film_state
from film_pipeline.mcp.tools.state import get_next_actions as get_next_actions
from film_pipeline.mcp.tools.state import get_orchestrator_summary as get_orchestrator_summary
from film_pipeline.mcp.tools.validation import get_validation_report as get_validation_report
from film_pipeline.mcp.tools.validation import list_validation_issues as list_validation_issues
from film_pipeline.mcp.tools.validation import run_validation as run_validation
from film_pipeline.studio.runtime import get_runtime as get_runtime
