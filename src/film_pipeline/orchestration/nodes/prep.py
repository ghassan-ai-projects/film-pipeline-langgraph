"""Prep phase nodes: intake, constitution, development, and script."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from film_pipeline.constraints import extract_constraints
from film_pipeline.orchestration.nodes._agent import (
    _propagate_side_effects,
    _run_agent,
    _save_artifact,
    produced_artifact,
)
from film_pipeline.orchestration.nodes._context import (
    _parse_ref,
)
from film_pipeline.orchestration.nodes._shared import (
    _coerce_user_runtime,
    _critical_context_issues,
    _extract_target_scene_count,
    _is_new_issue,
    _phase_gate_updates,
)
from film_pipeline.orchestration.services import _get_services
from film_pipeline.schemas.constraints import ProjectConstraints

_logger = logging.getLogger(__name__)


def _runtime_directive(user_runtime: int) -> str:
    """Authoritative-runtime instruction appended to the intake task."""
    if user_runtime > 0:
        return (
            f" The user REQUIRES a target runtime of {user_runtime} seconds — adopt it "
            "exactly as target_runtime_seconds; do not estimate your own."
        )
    return " Estimate a realistic runtime from the story's scope."


def _extract_intake_constraints(state: dict[str, Any]) -> ProjectConstraints:
    """Extract user-intent constraints before intake classification.

    This is deterministic/heuristic and runs offline so the intake agent and
    scope contract both see explicit creative requirements.
    """
    idea_text = str(state.get("idea", ""))
    constraints_hints = state.get("constraints_hints") or {}
    return extract_constraints(
        text=idea_text,
        project_id=str(state.get("project_id", "")),
        hints=constraints_hints if isinstance(constraints_hints, dict) else {},
    )


def _classify_film_idea(state: dict[str, Any], user_runtime: int) -> Any:
    """Run the intake classifier and return its project profile."""
    result = _run_agent(
        state,
        agent_id="intake-classifier-agent",
        phase="intake",
        task=(
            "Classify the user's film idea: determine genre, tone, audience, "
            "aspect ratio, and delivery format." + _runtime_directive(user_runtime) + " "
            "Identify risks and produce a structured project profile."
        ),
    )
    return produced_artifact(state, "intake-classifier-agent", result)


def _lock_profile_runtime(profile: Any, user_runtime: int) -> Any:
    """Authority override: lock the user's runtime onto the saved profile so
    the persisted artifact and downstream state agree."""
    if user_runtime > 0 and hasattr(profile, "model_copy"):
        return profile.model_copy(update={"target_runtime_seconds": user_runtime})
    return profile


def _profile_state_updates(profile: Any, user_runtime: int) -> dict[str, Any]:
    """State keys derived from the classified profile (runtime, film type)."""
    out: dict[str, Any] = {}
    if user_runtime > 0:
        out["target_runtime_seconds"] = user_runtime
    elif hasattr(profile, "target_runtime_seconds"):
        out["target_runtime_seconds"] = profile.target_runtime_seconds
    if hasattr(profile, "film_type"):
        out["film_type"] = str(profile.film_type)
    return out


def _merge_profile_into_constraints(
    constraints: ProjectConstraints,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Merge profile-derived values into constraints where they were not already
    supplied explicitly, so the artifact reflects the locked project config."""
    merged: dict[str, Any] = constraints.model_dump(mode="json", exclude_none=True)
    if updates.get("target_runtime_seconds") and not merged.get("target_runtime_seconds"):
        merged["target_runtime_seconds"] = updates["target_runtime_seconds"]
    if updates.get("film_type") and not merged.get("film_type"):
        merged["film_type"] = updates["film_type"]
    return merged


def intake_node(state: dict[str, Any]) -> dict[str, Any]:
    """Intake: classify input, infer config, present for approval."""
    new_state = deepcopy(state)
    updates: dict[str, Any] = _phase_gate_updates(new_state, phase="intake", gate="config")
    new_refs: list[str] = []

    # User-supplied runtime (seeded before the graph ran) is authoritative.
    user_runtime = _coerce_user_runtime(new_state)
    constraints = _extract_intake_constraints(new_state)

    profile = _lock_profile_runtime(_classify_film_idea(new_state, user_runtime), user_runtime)
    if profile is not None:
        ref = _save_artifact(new_state, profile, "project_profile", "intake")
        if ref:
            updates["profile_ref"] = ref
            new_refs.append(ref)
        updates.update(_profile_state_updates(profile, user_runtime))

    merged_constraints = _merge_profile_into_constraints(constraints, updates)

    # scene count from explicit hints (or extraction) takes precedence over the
    # runtime-derived default; seed it so the scope contract honors it.
    if merged_constraints.get("target_scene_count"):
        updates["target_scene_count"] = merged_constraints["target_scene_count"]

    final_constraints = ProjectConstraints(**merged_constraints)
    constraints_ref = _save_artifact(new_state, final_constraints, "project_constraints", "intake")
    if constraints_ref:
        updates["constraints_ref"] = constraints_ref
        new_refs.append(constraints_ref)
    updates["constraints"] = final_constraints.model_dump(mode="json")

    # ── Derive the Story Scope Contract (deterministic, forward-looking) ──
    _attach_scope_contract(new_state, updates, new_refs)

    if new_refs:
        updates["artifact_refs"] = new_refs
    _propagate_side_effects(new_state, updates, state)
    return updates


def _attach_scope_contract(
    state: dict[str, Any],
    updates: dict[str, Any],
    new_refs: list[str],
) -> None:
    """Compute and persist the Story Scope Contract from runtime x film style.

    Uses the authoritative runtime (user value already locked into ``updates``),
    the classified film_type, and the profile's pacing. Stores concrete scene/
    shot targets in state so prep prompts and gates can enforce them.
    """
    from film_pipeline.governance.scope_contract import derive_scope_contract, pacing_from_config

    runtime = int(
        updates.get("target_runtime_seconds", state.get("target_runtime_seconds", 0)) or 0
    )
    if runtime <= 0:
        return
    film_type = str(updates.get("film_type", state.get("film_type", "narrative")) or "narrative")
    pacing = pacing_from_config(state.get("resolved_config"))
    user_scene_count = _extract_target_scene_count(state) or _extract_target_scene_count(updates)

    contract = derive_scope_contract(
        project_id=str(state.get("project_id", "")),
        target_runtime_seconds=runtime,
        film_type=film_type,
        pacing=pacing,
        user_scene_count=user_scene_count,
    )
    ref = _save_artifact(state, contract, "scope_contract", "intake")
    if ref:
        updates["scope_contract_ref"] = ref
        new_refs.append(ref)
    updates["pacing_style"] = contract.pacing_style
    updates["target_scene_count"] = contract.target_scene_count
    updates["min_scene_count"] = contract.min_scene_count
    updates["target_shot_count"] = contract.target_shot_count


# ── Constitution ─────────────────────────────────────────────────────────────


def constitution_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    updates: dict[str, Any] = _phase_gate_updates(
        new_state, phase="constitution", gate="constitution"
    )
    new_refs: list[str] = []

    result = _run_agent(
        new_state,
        agent_id="film-constitution-agent",
        phase="constitution",
        task=(
            "Define the film's creative constitution: theme, tone, emotional "
            "promise, visual language, camera philosophy, character truths, "
            "and quality standards. This governs every downstream decision."
        ),
    )
    constitution = produced_artifact(new_state, "film-constitution-agent", result)
    if constitution is not None:
        ref = _save_artifact(new_state, constitution, "film_constitution", "constitution")
        if ref:
            updates["constitution_ref"] = ref
            new_refs.append(ref)

    if new_refs:
        updates["artifact_refs"] = new_refs
    _propagate_side_effects(new_state, updates, state)
    return updates


# ── Development ──────────────────────────────────────────────────────────────


def development_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    updates: dict[str, Any] = _phase_gate_updates(new_state, phase="development", gate="treatment")
    new_refs: list[str] = []

    result = _run_agent(
        new_state,
        agent_id="treatment-agent",
        phase="development",
        task=(
            "Develop the film treatment: write treatment prose, identify "
            "themes, map the three-act structure, and break down every scene "
            "with dramatic function, emotional shift, conflict, and outcome."
        ),
    )
    # ``scene_list`` (and ``story_bible`` below) are secondary keys of the same
    # result, not the contract's ``produces`` key, so they stay literal here.
    treatment = produced_artifact(new_state, "treatment-agent", result)
    scene_list = result.get("scene_list")
    if treatment is not None:
        ref = _save_artifact(new_state, treatment, "treatment", "development")
        if ref:
            updates["treatment_ref"] = ref
            new_refs.append(ref)

    # ── Gate: surface context-blind runs (WS-I) ──────────────────────────
    node_issues: list[dict[str, Any]] = _critical_context_issues(new_state, "development")

    if scene_list is not None:
        ref = _save_artifact(new_state, scene_list, "scene_list", "development")
        if ref:
            updates["scene_list_ref"] = ref
            new_refs.append(ref)

        # ── Gate S: scene count must meet the Scope Contract floor ────────
        from film_pipeline.governance.validators import validate_scene_count

        scene_count = len(getattr(scene_list, "scenes", []) or [])
        node_issues += validate_scene_count(new_state, scene_count)

    _report_new_issues(state, updates, node_issues)

    if new_refs:
        updates["artifact_refs"] = new_refs
    _propagate_side_effects(new_state, updates, state)
    return updates


# ── Script ───────────────────────────────────────────────────────────────────


def script_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    updates: dict[str, Any] = _phase_gate_updates(new_state, phase="script", gate="script")
    new_refs: list[str] = []

    result = _run_agent(
        new_state,
        agent_id="screenwriter-agent",
        phase="script",
        task=(
            "Write the complete screenplay: logline, premise, story bible "
            "with scene-by-scene breakdown, dialogue, action lines, and "
            "setup-payoff mapping across all three acts."
        ),
    )
    story_bible = result.get("story_bible")
    script = produced_artifact(new_state, "screenwriter-agent", result)
    if story_bible is not None:
        ref = _save_artifact(new_state, story_bible, "story_bible", "script")
        if ref:
            updates["story_bible_ref"] = ref
            new_refs.append(ref)

    # ── Gate: surface context-blind runs (WS-I) ──────────────────────────
    node_issues: list[dict[str, Any]] = _critical_context_issues(new_state, "script")

    if script is not None:
        ref = _save_artifact(new_state, script, "script", "script")
        if ref:
            updates["script_ref"] = ref
            new_refs.append(ref)

        # ── Gate S: script must preserve development scenes and meet floor ─
        from film_pipeline.governance.validators import (
            validate_script_scene_preservation,
        )

        script_scene_count = len(getattr(script, "scenes", []) or [])
        dev_scene_count = _development_scene_count(new_state)
        node_issues += validate_script_scene_preservation(
            new_state, script_scene_count, dev_scene_count
        )

    _report_new_issues(state, updates, node_issues)

    if new_refs:
        updates["artifact_refs"] = new_refs
    _propagate_side_effects(new_state, updates, state)
    return updates


def _report_new_issues(
    state: dict[str, Any],
    updates: dict[str, Any],
    node_issues: list[dict[str, Any]],
) -> None:
    """Report this node's gate issues that original state does not already list.

    Issues with an issue_id absent from ``state`` are copied into
    ``updates["issues"]``; when any of them is blocking, the phase's
    pre-approved gate is cancelled (see
    ``_withhold_auto_approval_on_blockers``).
    """
    fresh_issues = [i for i in node_issues if _is_new_issue(i, state)]
    if fresh_issues:
        updates["issues"] = fresh_issues
        _withhold_auto_approval_on_blockers(updates, fresh_issues)


def _withhold_auto_approval_on_blockers(
    updates: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    """In auto/headless mode, do not auto-approve a phase that has blocking issues.

    Only applies when the phase gate pre-approved itself (``approved=True`` from
    auto mode). Without this, a blocking gate issue is ignored in headless runs
    because the phase auto-approves and ``await_approval`` short-circuits.
    Setting ``approved=False`` routes the phase into the bounded repair loop
    instead; ``await_approval``/``after_approval`` terminate the run cleanly on
    stall rather than pausing on a human interrupt.
    """
    if not updates.get("approved"):
        return
    if any(i.get("severity") == "blocking" for i in issues):
        updates["approved"] = False
        updates["human_approval_required"] = False


def _development_scene_count(state: dict[str, Any]) -> int:
    """Count scenes in the approved development scene list (0 if unavailable)."""
    services = _get_services(state)
    ref = str(state.get("scene_list_ref", "") or "")
    if services is None or not ref:
        return 0
    try:
        from film_pipeline.schemas.base import FilmPhase

        parsed = _parse_ref(ref)
        data = services.artifact_store.load(
            str(state.get("project_id", "")),
            FilmPhase("development"),
            parsed.artifact_id,
            parsed.version,
        )
    except (FileNotFoundError, ValueError, KeyError) as exc:
        _logger.warning("Could not load development scene list for scene-count gate: %s", exc)
        return 0
    if isinstance(data, dict):
        scenes = data.get("scenes", [])
        if isinstance(scenes, list):
            return len(scenes)
    return 0
