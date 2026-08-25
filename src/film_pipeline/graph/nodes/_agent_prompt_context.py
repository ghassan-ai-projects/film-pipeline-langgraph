"""Prompt-context assembly: template defaults, upstream refs, and augmentation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from film_pipeline.constraints import render_constraints
from film_pipeline.graph.nodes._context import _build_phase_context
from film_pipeline.schemas.constraints import ProjectConstraints

if TYPE_CHECKING:
    from film_pipeline.graph.services import GraphServices
    from film_pipeline.schemas.kb import KBContextPacket


def _build_template_context(state: dict[str, Any], kb: KBContextPacket) -> dict[str, str]:
    """Seed template variables with defaults plus live provider pricing."""
    context_vars: dict[str, str] = {
        "project_id": str(state.get("project_id", "")),
        "idea": str(state.get("idea", state.get("input", ""))),
        "kb_refs": kb.kb_context_id,
        "constitution_ref": "",
        "constitution_content": "",
        "treatment_ref": "",
        "treatment_content": "",
        "scene_list_ref": "",
        "scene_list_content": "",
        "script_ref": "",
        "script_content": "",
        "story_bible_ref": "",
        "story_bible_content": "",
        "shot_matrix_ref": "",
        "shot_matrix_content": "",
        "visual_refs": "",
        "visual_refs_content": "",
        "execution_brief_ref": "",
        "execution_brief_content": "",
        "validator_issues": "",
        "target_runtime_seconds": "",
        "film_type": "",
        "pacing_style": "",
        "target_scene_count": "",
        "min_scene_count": "",
        "target_shot_count": "",
        "budget_cap": "",
        "preferred_providers": "",
        "provider_pricing": "",
        "constraints": "",
    }
    from film_pipeline.providers.pricing import pricing_prompt_block

    context_vars["provider_pricing"] = pricing_prompt_block()
    return context_vars


def _populate_state_fields(context_vars: dict[str, str], state: dict[str, Any]) -> None:
    """Copy truthy upstream refs and typed targets into prompt variables."""
    # Refs first, then numeric/typed fields (incl. Story Scope Contract targets)
    for key in (
        "constitution_ref",
        "treatment_ref",
        "scene_list_ref",
        "script_ref",
        "story_bible_ref",
        "shot_matrix_ref",
        "visual_refs",
        "execution_brief_ref",
        "target_runtime_seconds",
        "film_type",
        "pacing_style",
        "target_scene_count",
        "min_scene_count",
        "target_shot_count",
    ):
        val = state.get(key)
        if val:
            context_vars[key] = str(val)


def _render_constraint_block(context_vars: dict[str, str], state: dict[str, Any]) -> None:
    """Render user-intent constraints into the prompt block."""
    raw_constraints = state.get("constraints")
    if raw_constraints and isinstance(raw_constraints, (ProjectConstraints, dict)):
        context_vars["constraints"] = render_constraints(raw_constraints)


def _maybe_add_orchestrator_context(
    context_vars: dict[str, str],
    state: dict[str, Any],
    agent_id: str,
) -> None:
    """Inject orchestrator review context when this is the orchestrator agent."""
    if agent_id == "orchestrator-agent":
        context_vars.update(_build_phase_context(state))


def _attach_scoped_packet(
    context_vars: dict[str, str],
    state: dict[str, Any],
    services: GraphServices,
    phase: str,
) -> None:
    """Attach the phase's scoped context packet (Phase 6) when a builder exists.

    Replaces loading all artifacts into every prompt. ``suppress()`` must wrap
    only ``builder()`` so a failing packet degrades to empty scoped context.
    """
    from film_pipeline.graph.context_packets import PHASE_BUILDERS

    builder = PHASE_BUILDERS.get(phase)
    if builder is not None:
        from contextlib import suppress

        with suppress(Exception):
            context_vars["scoped_context"] = builder(state, services)


def _attach_validator_issues(context_vars: dict[str, str], state: dict[str, Any]) -> None:
    """Inject accumulated validator issues for QC synthesis."""
    issues_list: list[dict[str, Any]] = state.get("issues", [])
    if issues_list:
        context_vars["validator_issues"] = json.dumps(issues_list, indent=2)


def _set_script_scene_count(context_vars: dict[str, str]) -> None:
    """Derive script scene count from loaded script content (structure extractor)."""
    try:
        script_data = json.loads(context_vars["script_content"])
        scenes = script_data.get("scenes", [])
        context_vars["script_scene_count"] = str(len(scenes))
    except (json.JSONDecodeError, KeyError, TypeError):
        context_vars["script_scene_count"] = "0"


def _augment_phase_context(
    context_vars: dict[str, str],
    state: dict[str, Any],
    services: GraphServices,
    phase: str,
    agent_id: str,
) -> None:
    """Layer constraints, orchestrator, scoped-packet, and validator context."""
    _render_constraint_block(context_vars, state)
    _maybe_add_orchestrator_context(context_vars, state, agent_id)
    _attach_scoped_packet(context_vars, state, services, phase)
    _attach_validator_issues(context_vars, state)
    if agent_id == "structure-extractor-agent" and context_vars.get("script_content"):
        _set_script_scene_count(context_vars)
