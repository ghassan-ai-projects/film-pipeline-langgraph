"""Graph node definitions — one per phase, plus approval/repair control nodes.

Split by pipeline stage; import everything from this package
(``film_pipeline.orchestration.nodes``) rather than from the submodules.
"""

from __future__ import annotations

from film_pipeline.orchestration.nodes._agent import (
    _propagate_side_effects,
    _record_handoff,
    _run_agent,
    _save_artifact,
)
from film_pipeline.orchestration.nodes._context import (
    _AGENT_PROFILE_MAP,
    _artifact_context_max_chars,
    _build_dependency_map,
    _build_phase_context,
    _get_template_registry,
    _infer_artifact_type,
    _inject_artifact_context,
    _inject_config_context,
    _model_overrides_for,
    _parse_ref,
)
from film_pipeline.orchestration.nodes._shared import (
    _apply_external_state,
    _coerce_user_runtime,
    _critical_context_issues,
    _extract_target_scene_count,
    _is_new_issue,
    _is_new_ref,
    _phase_gate_updates,
)
from film_pipeline.orchestration.nodes.approval import (
    approve_phase_node,
    await_approval_node,
    repair_phase_node,
    request_revision_node,
)
from film_pipeline.orchestration.nodes.generation import generation_node
from film_pipeline.orchestration.nodes.prep import (
    _attach_scope_contract,
    _development_scene_count,
    _withhold_auto_approval_on_blockers,
    constitution_node,
    development_node,
    intake_node,
    script_node,
)
from film_pipeline.orchestration.nodes.qc import _run_validators, qc_node
from film_pipeline.orchestration.nodes.visual import (
    _ensure_matrix_scene_coverage,
    gen_planning_node,
    shot_bible_node,
    visual_dev_node,
)
from film_pipeline.orchestration.nodes.wrapup import (
    consistency_check_node,
    delivery_node,
    post_node,
)

__all__ = [
    "_AGENT_PROFILE_MAP",
    "_apply_external_state",
    "_artifact_context_max_chars",
    "_attach_scope_contract",
    "_build_dependency_map",
    "_build_phase_context",
    "_coerce_user_runtime",
    "_critical_context_issues",
    "_development_scene_count",
    "_ensure_matrix_scene_coverage",
    "_extract_target_scene_count",
    "_get_template_registry",
    "_infer_artifact_type",
    "_inject_artifact_context",
    "_inject_config_context",
    "_is_new_issue",
    "_is_new_ref",
    "_model_overrides_for",
    "_parse_ref",
    "_phase_gate_updates",
    "_propagate_side_effects",
    "_record_handoff",
    "_run_agent",
    "_run_validators",
    "_save_artifact",
    "_withhold_auto_approval_on_blockers",
    "approve_phase_node",
    "await_approval_node",
    "consistency_check_node",
    "constitution_node",
    "delivery_node",
    "development_node",
    "gen_planning_node",
    "generation_node",
    "intake_node",
    "post_node",
    "qc_node",
    "repair_phase_node",
    "request_revision_node",
    "script_node",
    "shot_bible_node",
    "visual_dev_node",
]
