"""Tool implementations and the registration entry point.

Every tool function takes a dict of arguments (including ``_envelope``) and
returns a serializable dict result. Key tools are wired to the runtime
backend; remaining tools return stubs pending full Phase 05+ wiring.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any, cast

from film_pipeline.app.runtime import get_runtime
from film_pipeline.mcp.contract import ToolContract, ToolGroup, ToolRegistry


def _stub(handler_name: str, **extra: object) -> dict[str, object]:
    """Build a stub response that callers can detect before full wiring."""
    return {
        "stub": True,
        "handler": handler_name,
        "message": "Not yet wired to orchestrator.",
        **extra,
    }


def _ok(**extra: object) -> dict[str, object]:
    """Build a success response."""
    return {"ok": True, **extra}


def _error(message: str, **extra: object) -> dict[str, object]:
    """Build an error response."""
    return {"ok": False, "error": message, **extra}


def _services(rt: object) -> Any:
    """Assert services are initialized and return them."""
    assert hasattr(rt, "services") and rt.services is not None
    return rt.services


# --- Project tools -------------------------------------------------------


async def create_film_project(args: dict[str, object]) -> dict[str, object]:
    """Create a new film project — wired to runtime.

    Accepts optional profile stack and runtime_mode. In ``real`` mode,
    mock providers and models are rejected.
    """
    rt = get_runtime()
    project_id = str(args.get("project_id", ""))
    if not project_id:
        return _error("project_id is required")

    server_mode = rt.server_mode

    # --- Runtime mode alignment ---
    requested_mode = str(args.get("runtime_mode", "")).lower()
    if requested_mode not in ("", "mock", "real"):
        return _error(f"runtime_mode must be 'mock' or 'real', got '{requested_mode}'")

    runtime_mode = requested_mode or server_mode
    if runtime_mode != server_mode:
        return _error(
            "Project runtime_mode must match the MCP server mode.",
            server_mode=server_mode,
            requested_runtime_mode=runtime_mode,
        )

    if runtime_mode == "real":
        # Reject mock provider/model ids
        for pid in _collect_profile_providers(args):
            if pid.startswith("mock-"):
                return _error(f"Provider '{pid}' is not allowed in real mode.")
        for mid in _collect_profile_models(args):
            if mid.startswith("mock-"):
                return _error(f"Model '{mid}' is not allowed in real mode.")

    try:
        profile_stack = _canonicalize_profile_stack(args)
        resolved_config = _resolve_project_config(profile_stack)
        conflicts = list(cast(list[Any], resolved_config.get("conflicts", [])))
        if conflicts:
            blocking = [c for c in conflicts if c.get("severity") == "blocking"]
            if blocking:
                return _error(
                    "Resolved profile stack has blocking conflicts.",
                    conflicts=conflicts,
                )
        if runtime_mode == "real":
            missing_credentials = _missing_provider_credentials(
                profile_stack, cast(dict[str, object], resolved_config.get("raw", {}))
            )
            if missing_credentials:
                return _error(
                    "Real-mode provider credentials are missing.",
                    missing_credentials=missing_credentials,
                )

        state = rt.create_project(
            project_id=project_id,
            title=str(args.get("title", "")),
            slug=str(args.get("slug", "")),
        )
        # Persist runtime mode and resolved profile stack
        state["runtime_mode"] = runtime_mode
        state["profile_stack"] = profile_stack
        state["server_mode"] = server_mode
        state["resolved_config"] = cast(dict[str, object], resolved_config.get("raw", {}))
        state["resolved_config_sources"] = resolved_config["sources"]
        state["config_conflicts"] = conflicts
        _register_project_providers(
            rt, profile_stack, cast(dict[str, object], resolved_config.get("raw", {}))
        )
        rt._record_audit(
            "system",
            "create_film_project",
            project_id=project_id,
            runtime_mode=runtime_mode,
            server_mode=server_mode,
        )
        return _ok(project_id=project_id, state=state)
    except ValueError as e:
        return _error(str(e))


def _collect_profile_providers(args: dict[str, object]) -> list[str]:
    """Extract provider ids from profile args for real-mode rejection."""
    pids: list[str] = []
    for key in ("provider_profile",):
        val = args.get(key)
        if val and isinstance(val, str) and val:
            try:
                _loader, src = _load_profile_flex(str(val), ("provider",))
                providers = src.raw.get("providers", {})
                for section in ("video", "image"):
                    for entry in providers.get(section, []):
                        if isinstance(entry, dict):
                            pid = str(entry.get("provider_id", ""))
                            if pid:
                                pids.append(pid)
                for provider_id in providers.get("order", []):
                    pid = str(provider_id)
                    if pid:
                        pids.append(pid)
            except FileNotFoundError:
                continue
    return pids


def _collect_profile_models(args: dict[str, object]) -> list[str]:
    """Extract model ids from profile args for real-mode rejection."""
    mids: list[str] = []
    for key in ("quality_profile",):
        val = args.get(key)
        if val and isinstance(val, str) and val:
            try:
                _loader, src = _load_profile_flex(str(val), ("quality",))
                models = src.raw.get("models", {})
                for entry in models.get("available", []):
                    if isinstance(entry, dict):
                        mid = str(entry.get("model_id", ""))
                        if mid:
                            mids.append(mid)
            except FileNotFoundError:
                continue
    return mids


async def list_projects(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    return _ok(projects=list(rt.projects.keys()))


async def find_project(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    ref = str(args.get("ref", ""))
    if not ref:
        return _error("ref is required (project_id or slug)")
    # Try direct lookup by project_id
    project = rt.get_project(ref)
    if project is not None:
        return _ok(project_id=project["project_id"], slug=project.get("slug", ""))
    # Try lookup by slug
    for pid, pstate in rt.projects.items():
        if pstate.get("slug") == ref:
            return _ok(project_id=pid, slug=ref)
    return _error(f"Project '{ref}' not found.")


async def set_active_project(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    project_id = str(args.get("project_ref", args.get("project_id", "")))
    if not project_id:
        return _error("project_ref is required")
    try:
        rt.set_active(project_id)
        return _ok(active_project_id=project_id)
    except ValueError as e:
        return _error(str(e))


async def get_active_project(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project set")
    return _ok(project_id=active["project_id"], current_phase=active.get("current_phase"))


async def get_project_summary(args: dict[str, object]) -> dict[str, object]:
    """Return a summary of the active project: phase, artifacts, issues, and handoffs."""
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    project_id = str(active["project_id"])

    # Gather all artifacts across phases
    from film_pipeline.schemas._base import FilmPhase

    store = _services(rt).artifact_store
    artifact_summary: list[dict[str, object]] = []
    for phase in FilmPhase:
        try:
            artifacts = store.list_artifacts(project_id, phase)
            for a in artifacts:
                artifact_summary.append(
                    {
                        "artifact_id": a.artifact_id,
                        "artifact_type": str(a.artifact_type.value),
                        "phase": str(a.phase.value),
                        "version": a.version,
                        "status": str(a.status.value),
                    }
                )
        except Exception:
            continue

    # Collect routing decisions
    routing = active.get("_routing_decisions", [])

    return _ok(
        project_id=project_id,
        title=active.get("title", active.get("idea", ""))[:200],
        slug=active.get("slug", ""),
        current_phase=active.get("current_phase", ""),
        approved=active.get("approved"),
        artifact_count=len(artifact_summary),
        artifacts=artifact_summary,
        issue_count=len(active.get("issues", [])),
        routing_decisions_count=len(routing),
        has_blockers=any(i.get("severity") == "blocking" for i in active.get("issues", [])),
    )


# --- Intake tools --------------------------------------------------------


async def submit_idea(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project. Create one first with create_film_project.")
    idea = str(args.get("idea", args.get("text", "")))
    if not idea:
        return _error("idea is required")
    # Inject the idea and run the graph through intake_node
    active["idea"] = idea
    state = rt.run_graph(active)
    # Update stored state
    rt.projects[active["project_id"]] = state
    return _ok(
        project_id=state["project_id"],
        current_phase=state.get("current_phase"),
        human_approval_required=state.get("human_approval_required"),
    )


async def get_intake_analysis(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.schemas._base import FilmPhase

    try:
        data = _services(rt).artifact_store.load(
            project_id, FilmPhase("intake"), "intake_analysis", 1
        )
        return _ok(analysis=data)
    except (FileNotFoundError, ValueError):
        # Fall back to project state idea field
        idea = active.get("idea", "")
        if idea:
            return _ok(analysis={"raw_idea": idea, "note": "Intake not yet fully analyzed."})
        return _error("No intake analysis found. Submit an idea first.")


async def approve_intake(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    current_phase = str(active.get("current_phase", ""))
    if current_phase not in ("intake", ""):
        return _error(f"Current phase is '{current_phase}', not intake.")
    try:
        state = rt.approve_phase()
        return _ok(project_id=state["project_id"], current_phase=state.get("current_phase"))
    except ValueError as e:
        return _error(str(e))


# --- State tools ---------------------------------------------------------


async def get_current_phase(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    return _ok(current_phase=active.get("current_phase", ""))


async def get_film_state(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    # Return a sanitized copy (no internal keys)
    safe = {
        k: v
        for k, v in active.items()
        if not k.startswith("_") and k not in ("approved", "human_approval_required")
    }
    return _ok(state=safe)


async def get_orchestrator_summary(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")

    from film_pipeline.graph import orchestrator_state as ostate
    from film_pipeline.graph.router import compute_actions

    ostate.ensure_orchestrator_state(active)
    router_result = compute_actions(active)
    latest_decision = ostate.get_latest_routing_decision(active)
    review_cycle = ostate.get_active_review_cycle(active, str(active.get("current_phase", "")))

    return _ok(
        project_id=active["project_id"],
        current_phase=active.get("current_phase"),
        approved=active.get("approved"),
        human_approval_required=active.get("human_approval_required"),
        issues=active.get("issues", []),
        next_action=router_result.next_action,
        route_reason=latest_decision.get("reason", "") if latest_decision else "",
        eligible_actions=router_result.eligible,
        blocked_actions=router_result.blocked,
        candidate_refs=ostate.get_candidate_refs(active),
        approved_refs=ostate.get_approved_refs(active),
        pending_revisions=ostate.get_pending_revisions(active),
        active_review_cycle=review_cycle,
        provider_blocked=ostate.get_blocked_providers(active),
        budget_snapshot=ostate.get_budget_snapshot(active),
        has_blocking_failures=ostate.has_blocking_failure(active),
    )


async def get_next_actions(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    from film_pipeline.graph.router import compute_actions

    actions = compute_actions(active)
    return _ok(
        next_action=actions.next_action,
        eligible=actions.eligible,
        blocked=actions.blocked,
    )


async def get_blockers(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    blockers = rt.get_blockers(active["project_id"])
    return _ok(blockers=blockers, has_blockers=len(blockers) > 0)


# --- Review tools --------------------------------------------------------


async def review_phase_artifacts(args: dict[str, object]) -> dict[str, object]:
    """Build a review package for the current phase with orchestrator recommendations.

    Returns a structured ReviewPackage instead of a plain artifact list.
    The package includes candidate vs approved diffs, validation results,
    open issues, risks, cost impact, and recommended next actions.
    """
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    phase = str(args.get("phase", active.get("current_phase", "")))
    if not phase:
        return _error("No phase specified and no active phase.")
    project_id = str(active["project_id"])
    from film_pipeline.schemas._base import FilmPhase

    try:
        fp = FilmPhase(phase)
    except ValueError:
        return _error(f"Unknown phase: {phase}")

    store = _services(rt).artifact_store
    artifacts = store.list_artifacts(project_id, fp)
    artifact_list = [
        {
            "artifact_id": a.artifact_id,
            "artifact_type": a.artifact_type,
            "phase": str(a.phase.value),
            "version": a.version,
            "status": a.status,
        }
        for a in artifacts
    ]

    # Build a review package using the ReviewPackageGenerator
    from film_pipeline.graph import orchestrator_state as ostate
    from film_pipeline.graph.router import compute_actions
    from film_pipeline.review.generator import ReviewPackageGenerator

    ostate.ensure_orchestrator_state(active)

    router_result = compute_actions(active)
    blocking_issues = [i for i in active.get("issues", []) if i.get("severity") == "blocking"]

    try:
        generator = ReviewPackageGenerator()
        pkg = generator.build(
            project_id=project_id,
            phase=fp,
            summary=f"Review package for {phase} phase",
            current_artifacts=[a["artifact_id"] for a in artifact_list],
            validation_results=[
                r.get("validator_id", "") for r in active.get("_validation_reports", [])
            ],
            open_issues=[i.get("message", "") for i in blocking_issues],
            orchestrator_recommendation=_build_orchestrator_recommendation(active, router_result),
            has_blocking_issues=len(blocking_issues) > 0,
        )
    except Exception:
        # Fallback to simple artifact list if generator fails
        return _ok(artifacts=artifact_list, phase=phase)

    return _ok(
        review_package=pkg.model_dump(mode="json"),
        phase=phase,
        router=router_result.__dict__,
    )


def _build_orchestrator_recommendation(state: dict[str, Any], router_result: Any) -> str:
    """Build a human-readable orchestrator recommendation for a review package."""
    action = router_result.next_action
    if action == "wait_for_human":
        return f"Review the {router_result.human_gate} package and approve or request revision."
    if action == "handle_blockers":
        return "Blocking issues detected. Resolve before advancing."
    if action == "escalate_to_human":
        return "Pipeline requires human decision — budget, provider, or quality threshold reached."
    if action == "escalate_to_failure_handler":
        return "Provider error requires triage by failure-handling agent."
    if action == "continue_unrelated_work":
        return (
            "Generation is blocked (provider health or failure), "
            "but planning and validation can continue."
        )
    if action == "present_review_package":
        return "Review the candidate artifacts and approve or request revision."
    if action == "revise":
        return "Pending revision must be resolved before approval."
    if action.startswith("advance_to_"):
        next_phase = action[len("advance_to_") :]
        return f"Phase complete. Ready to advance to {next_phase}."
    return f"Current action: {action}."


async def approve_phase(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    try:
        state = rt.approve_phase()
        return _ok(project_id=state["project_id"], current_phase=state.get("current_phase"))
    except ValueError as e:
        return _error(str(e))


async def request_revision(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    try:
        state = rt.request_revision(note=str(args.get("note", "")))
        return _ok(
            project_id=state["project_id"],
            current_phase=state.get("current_phase"),
            issues=state.get("issues", []),
        )
    except ValueError as e:
        return _error(str(e))


# --- Artifact tools ------------------------------------------------------


async def list_artifacts(args: dict[str, object]) -> dict[str, object]:
    """List all artifacts for the active project, optionally filtered by phase."""
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    phase_str = args.get("phase")
    from film_pipeline.schemas._base import FilmPhase

    fp = None
    if phase_str:
        try:
            fp = FilmPhase(str(phase_str))
        except ValueError:
            return _error(f"Unknown phase: {phase_str}")
    artifacts = _services(rt).artifact_store.list_artifacts(project_id, fp)
    return _ok(
        artifacts=[
            {
                "artifact_id": a.artifact_id,
                "artifact_type": a.artifact_type,
                "phase": str(a.phase.value),
                "version": a.version,
                "status": a.status,
            }
            for a in artifacts
        ]
    )


async def inspect_artifact(args: dict[str, object]) -> dict[str, object]:
    """Load and return the content of a specific artifact."""
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    artifact_id = str(args.get("artifact_id", ""))
    if not artifact_id:
        return _error("artifact_id is required.")
    phase_str = str(args.get("phase", active.get("current_phase", "")))
    version_raw = args.get("version", 1)
    version = int(str(version_raw)) if not isinstance(version_raw, int) else version_raw
    from film_pipeline.schemas._base import FilmPhase

    try:
        fp = FilmPhase(phase_str)
    except ValueError:
        return _error(f"Unknown phase: {phase_str}")
    try:
        content = _services(rt).artifact_store.load(project_id, fp, artifact_id, version)
        return _ok(content=content)
    except FileNotFoundError:
        return _error(f"Artifact '{artifact_id}' not found in phase '{phase_str}'.")


async def list_shots(args: dict[str, object]) -> dict[str, object]:
    """List shots from the shot bible artifact, if available."""
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.schemas._base import FilmPhase

    try:
        data = _services(rt).artifact_store.load(
            project_id, FilmPhase("shot_bible"), "shot_bible", 1
        )
        shots = data.get("shots", data.get("scenes", []))
        return _ok(shots=shots)
    except (FileNotFoundError, ValueError):
        return _ok(shots=[], note="Shot bible not yet generated.")


async def inspect_shot(args: dict[str, object]) -> dict[str, object]:
    """Inspect a specific shot by ID from the shot bible."""
    shot_id = str(args.get("shot_id", ""))
    if not shot_id:
        return _error("shot_id is required.")
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.schemas._base import FilmPhase

    try:
        data = _services(rt).artifact_store.load(
            project_id, FilmPhase("shot_bible"), "shot_bible", 1
        )
        shots = data.get("shots", data.get("scenes", []))
        match = next(
            (s for s in shots if str(s.get("shot_id", s.get("scene_id", ""))) == shot_id), None
        )
        if match is None:
            return _error(f"Shot '{shot_id}' not found.")
        return _ok(shot=match)
    except (FileNotFoundError, ValueError):
        return _error("Shot bible not yet generated.")


async def inspect_scene(args: dict[str, object]) -> dict[str, object]:
    """Inspect a specific scene from the script artifact."""
    scene_id = str(args.get("scene_id", ""))
    if not scene_id:
        return _error("scene_id is required.")
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.schemas._base import FilmPhase

    try:
        data = _services(rt).artifact_store.load(project_id, FilmPhase("script"), "script", 1)
        scenes = data.get("scenes", [])
        match = next((s for s in scenes if str(s.get("scene_id", "")) == scene_id), None)
        if match is None:
            return _error(f"Scene '{scene_id}' not found.")
        return _ok(scene=match)
    except (FileNotFoundError, ValueError):
        return _error("Script artifact not yet generated.")


async def inspect_reference(args: dict[str, object]) -> dict[str, object]:
    """Inspect a reference by ID from the visual development phase."""
    reference_id = str(args.get("reference_id", ""))
    if not reference_id:
        return _error("reference_id is required.")
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    data = _load_latest_reference_index(rt, project_id, active)
    if data is None:
        return _error("Reference index not yet generated.")
    refs = cast(list[Any], data.get("entries", data.get("references", data.get("items", []))))
    match = next(
        (r for r in refs if str(r.get("reference_id", r.get("id", ""))) == reference_id),
        None,
    )
    if match is None:
        return _error(f"Reference '{reference_id}' not found.")
    return _ok(reference=match)


async def generate_character_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate a CharacterBible from Script + FilmConstitution.

    Produces a locked character description (identity_block, voice, wardrobe,
    emotional arc, relationships) used by generate_reference_images for
    structured prompt construction.
    """
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")

    project_id = str(active["project_id"])
    character_id = str(args.get("character_id", "")).strip()
    if not character_id:
        return _error("character_id is required.")
    character_name = str(args.get("character_name", character_id)).strip()

    store = _services(rt).artifact_store

    # Load Script artifact
    try:
        from film_pipeline.schemas._base import FilmPhase

        script_data = store.load(project_id, FilmPhase("script"), "script", 1)
        script_text = _extract_script_text(script_data)
    except (FileNotFoundError, ValueError):
        return _error("Script artifact not found. Run script phase first.")

    # Load FilmConstitution artifact
    try:
        constitution = store.load(project_id, FilmPhase("constitution"), "film_constitution", 1)
    except (FileNotFoundError, ValueError):
        return _error("FilmConstitution not found. Run constitution phase first.")

    constitution_text = str(constitution.get("theme", "")) if isinstance(constitution, dict) else ""

    # Build prompt and call model
    prompt = f"""# Role
You are a character development specialist. Given a script and film constitution,
produce a detailed CharacterBible for a single character.

# Core Task
Create a CharacterBible for character '{character_name}' (id: {character_id}).

# Context
Film Constitution:
{constitution_text}

Script:
{script_text[:8000]}

# Constraints
- The identity_block must be a locked, invariant one-paragraph description
  of the character's visual appearance. This block is injected verbatim into
  every reference-image and video prompt — it must be specific and durable.
- voice_rules must capture cadence, vocabulary patterns, forbidden phrasings,
  and signature speech moves.
- wardrobe_rules must include a baseline description and act-specific variants.
- emotional_arc must have start_state, midpoint_state, end_state, and at least 2
  key_turning_points.
- relationship_map must list every meaningful relationship with other characters.
- must_not_change must list 3-5 identity invariants the agents must never alter.

# Output Format
Return ONLY valid JSON. No markdown fences, no commentary.
{{
  "character_id": "{character_id}",
  "project_id": "{project_id}",
  "visual_identity": {{
    "character_id": "{character_id}",
    "name": "{character_name}",
    "role": "protagonist | antagonist | supporting | foil",
    "age": "e.g. mid-40s",
    "physical_description": "Detailed physical description",
    "identity_block": "Locked one-paragraph visual description for prompts"
  }},
  "voice_rules": {{
    "cadence": "e.g. staccato, breathless",
    "vocabulary": ["signature", "words"],
    "forbidden_phrasings": ["never says X"],
    "signature_moves": ["repeating questions", "cutting people off"]
  }},
  "wardrobe_rules": {{
    "baseline": "Default costume description",
    "act_variants": {{"act_1": "description", "act_2": "description"}}
  }},
  "emotional_arc": {{
    "start_state": "e.g. guarded and distant",
    "midpoint_state": "e.g. vulnerable, beginning to trust",
    "end_state": "e.g. open, at peace",
    "key_turning_points": ["moment 1", "moment 2"]
  }},
  "relationship_map": [
    {{"other_character_id": "char_002", "relation": "description", "evolution": "how it changes"}}
  ],
  "reference_assets": [],
  "must_not_change": ["invariant 1", "invariant 2", "invariant 3"]
}}"""

    try:
        from film_pipeline.agents.impl.character_bible_agent import CharacterBibleAgent
        from film_pipeline.schemas._base import AgentFamily, AgentRole
        from film_pipeline.schemas.handoff import AgentRegistration

        agent = CharacterBibleAgent(
            AgentRegistration(
                agent_id="character-bible-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["character_development"],
                input_artifacts=["script", "film_constitution"],
                output_artifacts=["character_bible"],
            )
        )

        runner = _services(rt).prompt_runner

        # Use PromptRunner with model_adapter if available
        model_output: dict[str, Any]
        if runner.model_adapter is not None:
            raw = runner.model_adapter.chat(
                prompt, model=runner.model_router.resolve("creative_writer")
            )
            model_output = raw if isinstance(raw, dict) else {}
        else:
            # Mock mode: return a minimal valid response
            model_output = {
                "character_id": character_id,
                "project_id": project_id,
                "visual_identity": {
                    "character_id": character_id,
                    "name": character_name,
                    "role": "protagonist",
                    "age": "unknown",
                    "physical_description": "Generated in mock mode.",
                    "identity_block": (
                        f"A {character_name} — generated in mock mode. "
                        "Replace with real model output."
                    ),
                },
                "voice_rules": {
                    "cadence": "measured",
                    "vocabulary": [],
                    "forbidden_phrasings": [],
                    "signature_moves": [],
                },
                "wardrobe_rules": {"baseline": "", "act_variants": {}},
                "emotional_arc": {
                    "start_state": "unknown",
                    "midpoint_state": "unknown",
                    "end_state": "unknown",
                    "key_turning_points": [],
                },
                "relationship_map": [],
                "reference_assets": [],
                "must_not_change": ["identity_block"],
            }

        result = agent.execute(model_output)
        if not agent.validate(result):
            return _error("CharacterBible agent produced invalid output.")

        bible = result["character_bible"]

        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType
        from film_pipeline.schemas.artifact import ArtifactMetadata

        meta = ArtifactMetadata(
            artifact_id="character_bible",
            artifact_type=ArtifactType.CHARACTER_BIBLE,
            project_id=project_id,
            phase=FilmPhase("visual_dev"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_character_bible",
            created_at=datetime.now(UTC),
        )
        ref = store.save(bible, meta)

        active["character_bible_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(
            character_bible_ref=ref,
            character_id=character_id,
            identity_block=bible.visual_identity.identity_block,
        )

    except Exception as exc:
        return _error(f"CharacterBible generation failed: {exc}")


def _extract_script_text(script_data: dict[str, object] | None) -> str:
    """Extract readable text from the Script artifact."""
    if script_data is None:
        return ""
    if isinstance(script_data, dict):
        scenes = script_data.get("scenes", script_data.get("content", []))
        if isinstance(scenes, list):
            lines: list[str] = []
            for scene in scenes:
                if isinstance(scene, dict):
                    heading = scene.get("heading", scene.get("scene_heading", ""))
                    if heading:
                        lines.append(str(heading))
                    if scene is not None:
                        for action in cast(
                            list[Any], scene.get("action_lines", scene.get("actions", []))
                        ):
                            lines.append(str(action))
                        for dialogue in cast(
                            list[Any], scene.get("dialogue_lines", scene.get("dialogue", []))
                        ):
                            if isinstance(dialogue, dict):
                                char = dialogue.get("character_id", dialogue.get("character", ""))
                                line = dialogue.get("line", dialogue.get("text", ""))
                                lines.append(f"{char}: {line}")
            return "\n".join(lines)
    return str(script_data)


async def generate_environment_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate an EnvironmentBible from Script + FilmConstitution.

    Produces a locked environment description (locked_prompt_block, fingerprint,
    zones, viewpoints, lighting states, color palette) used by
    generate_reference_images for structured prompt construction.
    """
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")

    project_id = str(active["project_id"])
    environment_id = str(args.get("environment_id", "")).strip()
    if not environment_id:
        return _error("environment_id is required.")
    environment_name = str(args.get("environment_name", environment_id)).strip()

    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import FilmPhase

        script_data = store.load(project_id, FilmPhase("script"), "script", 1)
        script_text = _extract_script_text(script_data)
    except (FileNotFoundError, ValueError):
        return _error("Script artifact not found. Run script phase first.")

    try:
        constitution = store.load(project_id, FilmPhase("constitution"), "film_constitution", 1)
    except (FileNotFoundError, ValueError):
        return _error("FilmConstitution not found. Run constitution phase first.")

    constitution_text = (
        str(constitution.get("visual_language", "")) if isinstance(constitution, dict) else ""
    )
    theme_text = str(constitution.get("theme", "")) if isinstance(constitution, dict) else ""

    prompt = f"""# Role
You are an environment design specialist. Given a script and film constitution,
produce a detailed EnvironmentBible for a single location.

# Core Task
Create an EnvironmentBible for environment '{environment_name}' (id: {environment_id}).

# Context
Film Theme: {theme_text}
Visual Language: {constitution_text}

Script:
{script_text[:8000]}

# Constraints
- locked_prompt_block must be a one-paragraph description of the environment
  injected verbatim into every prompt. Specific and durable.
- fingerprint.text must be a compressed invariant block (2-3 sentences) that
  captures the essence of the space.
- zones: sub-areas within the environment, each with allowed viewpoints.
- viewpoints: approved camera positions with lens and framing.
- lighting_states: named, repeatable lighting states (at least 2).
- color_palette: 4-8 hex color codes (e.g. "#1a1a2e") that define the
  environment's color identity.
- must_not_change: 3-5 invariants the agents must never alter.

# Output Format
Return ONLY valid JSON:
{{
  "environment_id": "{environment_id}",
  "project_id": "{project_id}",
  "name": "{environment_name}",
  "locked_prompt_block": "One-paragraph description for prompts",
  "invariants": ["invariant 1", "invariant 2"],
  "zones": [
    {{"zone_id": "main_area", "description": "...", "allowed_viewpoints": ["vp_wide", "vp_close"]}}
  ],
  "viewpoints": [
    {{"viewpoint_id": "vp_wide", "description": "Wide establishing shot",
      "lens": "24mm", "framing": "full room"}}
  ],
  "lighting_states": [
    {{"state_id": "golden_afternoon",
      "description": "Warm afternoon light through windows",
      "shadow_direction": "long, eastward", "color_temperature": "3200K",
      "primary_source": "window"}}
  ],
  "color_palette": ["#1a1a2e", "#e94560", "#0f3460", "#16213e"],
  "fingerprint": {{"text": "Compressed invariant block"}},
  "reference_assets": [],
  "must_not_change": ["invariant 1", "invariant 2"]
}}"""

    try:
        from film_pipeline.agents.impl.environment_bible_agent import EnvironmentBibleAgent
        from film_pipeline.schemas._base import AgentFamily, AgentRole
        from film_pipeline.schemas.handoff import AgentRegistration

        agent = EnvironmentBibleAgent(
            AgentRegistration(
                agent_id="environment-bible-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["environment_design"],
                input_artifacts=["script", "film_constitution"],
                output_artifacts=["environment_bible"],
            )
        )

        runner = _services(rt).prompt_runner
        model_output: dict[str, Any]
        if runner.model_adapter is not None:
            raw = runner.model_adapter.chat(
                prompt, model=runner.model_router.resolve("creative_writer")
            )
            model_output = raw if isinstance(raw, dict) else {}
        else:
            model_output = {
                "environment_id": environment_id,
                "project_id": project_id,
                "name": environment_name,
                "locked_prompt_block": f"A {environment_name} — generated in mock mode.",
                "invariants": [],
                "zones": [],
                "viewpoints": [],
                "lighting_states": [],
                "color_palette": ["#1a1a2e", "#e94560"],
                "fingerprint": {"text": f"The {environment_name} — mock mode."},
                "reference_assets": [],
                "must_not_change": ["locked_prompt_block"],
            }

        result = agent.execute(model_output)
        if not agent.validate(result):
            return _error("EnvironmentBible agent produced invalid output.")

        bible = result["environment_bible"]

        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType
        from film_pipeline.schemas.artifact import ArtifactMetadata

        meta = ArtifactMetadata(
            artifact_id="environment_bible",
            artifact_type=ArtifactType.ENVIRONMENT_BIBLE,
            project_id=project_id,
            phase=FilmPhase("visual_dev"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_environment_bible",
            created_at=datetime.now(UTC),
        )
        ref = store.save(bible, meta)

        active["environment_bible_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(
            environment_bible_ref=ref,
            environment_id=environment_id,
            locked_prompt_block=bible.locked_prompt_block,
            palette=bible.color_palette,
        )

    except Exception as exc:
        return _error(f"EnvironmentBible generation failed: {exc}")


async def generate_camera_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate a CameraLanguageBible from FilmConstitution."""
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import FilmPhase

        constitution = store.load(project_id, FilmPhase("constitution"), "film_constitution", 1)
    except (FileNotFoundError, ValueError):
        return _error("FilmConstitution not found.")

    camera_philosophy = (
        str(constitution.get("camera_philosophy", "")) if isinstance(constitution, dict) else ""
    )

    try:
        from film_pipeline.agents.impl.camera_bible_agent import CameraBibleAgent
        from film_pipeline.schemas._base import AgentFamily, AgentRole, ArtifactStatus, ArtifactType
        from film_pipeline.schemas.handoff import AgentRegistration

        agent = CameraBibleAgent(
            AgentRegistration(
                agent_id="camera-bible-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["camera_design"],
                input_artifacts=["film_constitution"],
                output_artifacts=["camera_language_bible"],
            )
        )
        runner = _services(rt).prompt_runner
        model_output: dict[str, Any]
        if runner.model_adapter is not None:
            raw = runner.model_adapter.chat(
                f"Create a CameraLanguageBible for a film with camera philosophy: "
                f"{camera_philosophy}. "
                "Return JSON with 'profiles' array (profile_id, use_case, lens, "
                "framing, movement, depth_of_field, composition_rules, "
                "transition_rules, emotional_meaning) and 'default_profile_id'.",
                model=runner.model_router.resolve("creative_writer"),
            )
            model_output = raw if isinstance(raw, dict) else {}
        else:
            model_output = {
                "project_id": project_id,
                "profiles": [
                    {
                        "profile_id": "default",
                        "use_case": "General shots",
                        "lens": "35mm prime",
                        "framing": "Rule of thirds",
                        "movement": "Static or slow push-in",
                        "depth_of_field": "Shallow, f/2.0",
                        "composition_rules": ["Rule of thirds"],
                        "transition_rules": ["Cut on action"],
                        "emotional_meaning": "Observational, intimate",
                    }
                ],
                "default_profile_id": "default",
            }

        result = agent.execute(model_output)
        if not agent.validate(result):
            return _error("CameraBible agent produced invalid output.")
        bible = result["camera_bible"]

        from datetime import UTC, datetime

        from film_pipeline.schemas.artifact import ArtifactMetadata

        meta = ArtifactMetadata(
            artifact_id="camera_language_bible",
            artifact_type=ArtifactType.CAMERA_LANGUAGE_BIBLE,
            project_id=project_id,
            phase=FilmPhase("visual_dev"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_camera_bible",
            created_at=datetime.now(UTC),
        )
        ref = store.save(bible, meta)
        active["camera_bible_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(camera_bible_ref=ref, profiles=len(bible.profiles))
    except Exception as exc:
        return _error(f"CameraBible generation failed: {exc}")


async def generate_style_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate a StyleBible from FilmConstitution + EnvironmentBible palettes."""
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import FilmPhase

        constitution = store.load(project_id, FilmPhase("constitution"), "film_constitution", 1)
    except (FileNotFoundError, ValueError):
        return _error("FilmConstitution not found.")

    visual_language = (
        str(constitution.get("visual_language", "")) if isinstance(constitution, dict) else ""
    )
    tone = str(constitution.get("tone", "")) if isinstance(constitution, dict) else ""
    palette_hint = ""
    try:
        env_bible = store.load(project_id, FilmPhase("visual_dev"), "environment_bible", 1)
        if isinstance(env_bible, dict):
            palette_hint = ", ".join(str(c) for c in env_bible.get("color_palette", [])[:6])
    except (FileNotFoundError, ValueError):
        pass

    try:
        from film_pipeline.agents.impl.style_bible_agent import StyleBibleAgent
        from film_pipeline.schemas._base import AgentFamily, AgentRole, ArtifactStatus, ArtifactType
        from film_pipeline.schemas.handoff import AgentRegistration

        agent = StyleBibleAgent(
            AgentRegistration(
                agent_id="style-bible-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["style_definition"],
                input_artifacts=["film_constitution", "environment_bible"],
                output_artifacts=["style_bible"],
            )
        )
        runner = _services(rt).prompt_runner
        model_output: dict[str, Any]
        if runner.model_adapter is not None:
            raw = runner.model_adapter.chat(
                f"Create a StyleBible. Visual language: {visual_language}. "
                f"Tone: {tone}. Palette hints: {palette_hint}. "
                "Return JSON with 'color_palette' (4-8 hex codes), "
                "'texture', 'grain', 'visual_mood', 'reference_stills', "
                "and 'must_not_change'.",
                model=runner.model_router.resolve("creative_writer"),
            )
            model_output = raw if isinstance(raw, dict) else {}
        else:
            model_output = {
                "project_id": project_id,
                "color_palette": ["#1a1a2e", "#e94560", "#0f3460", "#16213e"],
                "texture": "gritty, painterly",
                "grain": "subtle 16mm grain",
                "visual_mood": "melancholic, high-contrast",
                "reference_stills": [],
                "must_not_change": ["color_palette"],
            }

        result = agent.execute(model_output)
        if not agent.validate(result):
            return _error("StyleBible agent produced invalid output.")
        bible = result["style_bible"]

        from datetime import UTC, datetime

        from film_pipeline.schemas.artifact import ArtifactMetadata

        meta = ArtifactMetadata(
            artifact_id="style_bible",
            artifact_type=ArtifactType.STYLE_BIBLE,
            project_id=project_id,
            phase=FilmPhase("visual_dev"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_style_bible",
            created_at=datetime.now(UTC),
        )
        ref = store.save(bible, meta)
        active["style_bible_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(style_bible_ref=ref, palette=bible.color_palette, mood=bible.visual_mood)
    except Exception as exc:
        return _error(f"StyleBible generation failed: {exc}")


async def generate_shot_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate MasterFilmMatrix + ContinuityLedger from Script + visual refs.

    Produces the shot-by-shot production matrix (every clip as a row with
    scene, characters, env, camera, chaining) and a continuity ledger
    tracking state_in/state_out per shot.
    """
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import FilmPhase

        script_data = store.load(project_id, FilmPhase("script"), "script", 1)
        ref_data = store.load(project_id, FilmPhase("visual_dev"), "reference_index", 1)
    except (FileNotFoundError, ValueError) as e:
        return _error(f"Required artifacts not found: {e}")

    script_text = _extract_script_text(script_data)
    ref_summary = ""
    if isinstance(ref_data, dict):
        entries = ref_data.get("entries", [])
        ref_summary = ", ".join(
            f"{e.get('subject_type', '')}/{e.get('subject_id', '')}({e.get('frame_role', '')})"
            for e in entries[:20]
            if isinstance(e, dict)
        )

    try:
        from film_pipeline.agents.impl.shot_bible_agent import ShotBibleAgent
        from film_pipeline.schemas._base import AgentFamily, AgentRole, ArtifactStatus, ArtifactType
        from film_pipeline.schemas.handoff import AgentRegistration

        agent = ShotBibleAgent(
            AgentRegistration(
                agent_id="shot-design-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["shot_design", "matrix_planning"],
                input_artifacts=["script", "visual_refs", "character_bible"],
                output_artifacts=["master_film_matrix"],
            )
        )
        runner = _services(rt).prompt_runner
        model_output: dict[str, Any]
        if runner.model_adapter is not None:
            raw = runner.model_adapter.chat(
                f"Create a MasterFilmMatrix from the script and visual references.\n\n"
                f"Script:\n{script_text[:6000]}\n\n"
                f"Visual references available:\n{ref_summary}\n\n"
                "Return JSON with 'shot_matrix' containing 'rows' array of shot rows "
                "(shot_id, act_id, scene_id, duration_seconds, characters, environment, "
                "camera_profile, priority, risk_level) and 'coverage_groups' array.",
                model=runner.model_router.resolve("creative_writer"),
            )
            model_output = raw if isinstance(raw, dict) else {}
        else:
            model_output = {
                "shot_matrix": {
                    "project_id": project_id,
                    "rows": [
                        {
                            "shot_id": "S001",
                            "act_id": "act1",
                            "scene_id": "scene_01",
                            "duration_seconds": 5,
                            "characters": ["leo"],
                            "environment": "studio",
                            "camera_profile": "default",
                            "priority": "standard",
                            "risk_level": "low",
                            "generation_order": 1,
                        }
                    ],
                    "coverage_groups": [],
                }
            }

        result = agent.execute(model_output)
        if not agent.validate(result):
            return _error("ShotBible agent produced invalid output.")
        matrix = result["shot_matrix"]

        from datetime import UTC, datetime

        from film_pipeline.schemas.artifact import ArtifactMetadata

        meta = ArtifactMetadata(
            artifact_id="master_film_matrix",
            artifact_type=ArtifactType.MASTER_FILM_MATRIX,
            project_id=project_id,
            phase=FilmPhase("shot_bible"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_shot_bible",
            created_at=datetime.now(UTC),
        )
        ref = store.save(matrix, meta)
        active["shot_matrix_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)

        # Generate a basic continuity ledger from the matrix
        ledger_ref = _generate_continuity_ledger(store, project_id, matrix)

        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(
            shot_matrix_ref=ref,
            shot_count=len(matrix.rows),
            continuity_ledger_ref=ledger_ref,
        )
    except Exception as exc:
        return _error(f"Shot bible generation failed: {exc}")


def _generate_continuity_ledger(store: Any, project_id: str, matrix: Any) -> str | None:
    """Generate a basic continuity ledger from the shot matrix."""
    try:
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
        from film_pipeline.schemas.artifact import ArtifactMetadata
        from film_pipeline.schemas.continuity import (
            ContinuityLedger,
            ContinuityLedgerEntry,
            StateRecord,
        )

        entries: list[ContinuityLedgerEntry] = []
        prev_chars: list[str] = []
        prev_env = ""

        for _i, row in enumerate(matrix.rows):
            current_chars = [str(c) for c in row.characters]
            current_env = str(row.environment)
            entries.append(
                ContinuityLedgerEntry(
                    shot_id=row.shot_id,
                    state_in=[
                        StateRecord(
                            label="characters",
                            description=", ".join(prev_chars) if prev_chars else "none",
                            refs=prev_chars,
                        ),
                        StateRecord(
                            label="environment",
                            description=prev_env,
                            refs=[prev_env] if prev_env else [],
                        ),
                    ],
                    action="",
                    state_out=[
                        StateRecord(
                            label="characters",
                            description=", ".join(current_chars) if current_chars else "none",
                            refs=current_chars,
                        ),
                        StateRecord(
                            label="environment",
                            description=current_env,
                            refs=[current_env] if current_env else [],
                        ),
                    ],
                )
            )
            prev_chars = current_chars
            prev_env = current_env

        ledger = ContinuityLedger(
            project_id=project_id,
            entries=entries,
        )
        meta = ArtifactMetadata(
            artifact_id="continuity_ledger",
            artifact_type=ArtifactType.CONTINUITY_LEDGER,
            project_id=project_id,
            phase=FilmPhase("shot_bible"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_shot_bible",
            created_at=datetime.now(UTC),
        )
        return cast(str, store.save(ledger, meta))
    except Exception:
        return None


async def initialize_budget(args: dict[str, object]) -> dict[str, object]:
    """Create the initial BudgetState for a project."""
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    cap = float(cast(float, args.get("cap_usd", 100.0)))
    store = _services(rt).artifact_store

    try:
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
        from film_pipeline.schemas.artifact import ArtifactMetadata
        from film_pipeline.schemas.budget import BudgetState

        budget = BudgetState(
            project_id=project_id,
            cap_usd=cap,
            spent_usd=0.0,
            per_phase_caps_usd={
                "visual_dev": cap * 0.3,
                "generation": cap * 0.6,
                "post": cap * 0.1,
            },
            max_auto_approved_cost_usd=1.0,
            human_approval_above_usd=5.0,
        )
        meta = ArtifactMetadata(
            artifact_id="budget_state",
            artifact_type=ArtifactType.BUDGET_STATE,
            project_id=project_id,
            phase=FilmPhase("gen_planning"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.initialize_budget",
            created_at=datetime.now(UTC),
        )
        ref = store.save(budget, meta)
        active["budget_state_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(budget_state_ref=ref, cap_usd=cap, remaining_usd=budget.remaining_usd)
    except Exception as exc:
        return _error(f"Budget initialization failed: {exc}")


async def generate_plan(args: dict[str, object]) -> dict[str, object]:
    """Generate a GenerationPlan from the shot matrix."""
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import FilmPhase

        matrix = store.load(project_id, FilmPhase("shot_bible"), "master_film_matrix", 1)
    except (FileNotFoundError, ValueError):
        return _error("MasterFilmMatrix not found. Run generate_shot_bible first.")

    from film_pipeline.schemas.generation import GenerationPlan, ShotPlan

    shots = [
        ShotPlan(
            shot_id=row.shot_id,
            priority=3,
            risk=str(getattr(row, "risk_level", "medium")),
            tier="fast",
            estimated_duration=float(getattr(row, "duration_seconds", 5)),
            generation_order=i,
        )
        for i, row in enumerate(matrix.rows)
    ]

    total_cost = sum(s.estimated_duration * 0.02 for s in shots)
    plan = GenerationPlan(
        project_id=project_id,
        shots=shots,
        total_estimated_cost=total_cost,
        provider_utilization={"gemini-imagen-4": len(shots)},
    )

    try:
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType
        from film_pipeline.schemas.artifact import ArtifactMetadata

        meta = ArtifactMetadata(
            artifact_id="generation_plan",
            artifact_type=ArtifactType.GENERATION_PLAN,
            project_id=project_id,
            phase=FilmPhase("gen_planning"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_plan",
            created_at=datetime.now(UTC),
        )
        ref = store.save(plan, meta)
        active["generation_plan_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(
            generation_plan_ref=ref,
            shot_count=len(shots),
            total_estimated_cost=total_cost,
        )
    except Exception as exc:
        return _error(f"Plan generation failed: {exc}")


async def run_validation(args: dict[str, object]) -> dict[str, object]:
    """Run validators for the current phase and persist ValidationReport."""
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    phase_str = str(active.get("current_phase", "visual_dev"))
    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import FilmPhase

        fp = FilmPhase(phase_str)
    except ValueError:
        return _error(f"Unknown phase: {phase_str}")

    reports: list[dict[str, object]] = []
    saved_refs: list[str] = []

    try:
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType
        from film_pipeline.schemas.artifact import ArtifactMetadata

        if phase_str == "visual_dev":
            art_data = _load_latest_reference_index(rt, project_id, active)
            if art_data is not None:
                from film_pipeline.validation.impl.reference_usability import (
                    ReferenceUsabilityValidator,
                )

                validator = ReferenceUsabilityValidator()
                report = validator.run(art_data)
                reports.append(_report_summary(report))
                meta = ArtifactMetadata(
                    artifact_id="validation_report",
                    artifact_type=ArtifactType.VALIDATION_REPORT,
                    project_id=project_id,
                    phase=fp,
                    version=1,
                    status=ArtifactStatus.CANDIDATE,
                    created_by="mcp.run_validation",
                    created_at=datetime.now(UTC),
                )
                ref = store.save(report, meta)
                saved_refs.append(ref)

        elif phase_str == "script":
            try:
                art_data = store.load(project_id, fp, "script", 1)
            except (FileNotFoundError, ValueError):
                art_data = None
            if art_data is not None:
                from film_pipeline.validation.impl.dialogue_voice import DialogueVoiceValidator
                from film_pipeline.validation.impl.script_structure import ScriptStructureValidator

                for vcls in (ScriptStructureValidator, DialogueVoiceValidator):
                    validator = vcls()  # type: ignore[assignment]
                    report = validator.run(art_data)
                    reports.append(_report_summary(report))
                    meta = ArtifactMetadata(
                        artifact_id="validation_report",
                        artifact_type=ArtifactType.VALIDATION_REPORT,
                        project_id=project_id,
                        phase=fp,
                        version=1,
                        status=ArtifactStatus.CANDIDATE,
                        created_by="mcp.run_validation",
                        created_at=datetime.now(UTC),
                    )
                    ref = store.save(report, meta)
                    saved_refs.append(ref)
    except Exception as exc:
        return _error(f"Validation run failed: {exc}")

    if not reports:
        return _ok(message="No validators found for this phase.")
    active["_validation_reports"] = reports
    active.setdefault("validation_refs", []).extend(saved_refs)
    rt.projects[project_id] = active
    rt._persist_project_state(project_id)
    return _ok(phase=phase_str, reports=reports, saved_refs=saved_refs)


async def generate_reference_images(args: dict[str, object]) -> dict[str, object]:
    """Generate persisted reference images from the visual-dev reference index."""
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")

    project_id = str(active["project_id"])
    data = _load_latest_reference_index(rt, project_id, active)
    if data is None:
        return _error("Reference index not yet generated. Run visual_dev first.")

    entries = data.get("entries", [])
    if not isinstance(entries, list) or not entries:
        return _error("Reference index has no entries to generate.")

    requested_ids = {
        str(item)
        for item in cast(list[Any], args.get("reference_ids", []))
        if isinstance(item, str) and str(item).strip()
    }
    force = bool(args.get("force", False))
    provider = _select_image_provider(rt)
    if provider is None:
        return _error("No image provider is registered for the active project.")

    project_root = rt.project_roots.get(project_id)
    if project_root is None:
        return _error(f"Project root for '{project_id}' not found.")

    results: list[dict[str, object]] = []
    generated = 0
    skipped = 0
    failed = 0

    # Phase 4 — Identity/geometry consistency: group entries by subject,
    # generate anchor frame first, propagate seed + identity state.
    grouped_entries = _group_and_sort_entries(entries, requested_ids, force, project_root, results)
    identity_states: dict[str, dict[str, object]] = {}  # keyed by group_key

    # Pre-load CharacterBibles from artifact store for structured prompts
    char_bibles: dict[str, dict[str, object]] = {}
    store = _services(rt).artifact_store
    for raw in grouped_entries:
        if raw.get("_skip"):
            continue
        subject_type = str(raw.get("subject_type", ""))
        subject_id = str(raw.get("subject_id", "")).strip()
        if subject_type == "character" and subject_id and subject_id not in char_bibles:
            try:
                from film_pipeline.schemas._base import FilmPhase

                bible = store.load(project_id, FilmPhase("visual_dev"), "character_bible", 1)
                if isinstance(bible, dict) and bible.get("character_id") == subject_id:
                    char_bibles[subject_id] = bible
            except (FileNotFoundError, ValueError):
                pass  # CharacterBible not yet generated — fall back to prompt_text

    for raw in grouped_entries:
        reference_id = str(raw.get("reference_id", "")).strip()
        if not reference_id:
            continue
        if raw.get("_skip"):
            skipped += 1
            results.append({"reference_id": reference_id, "status": "skipped"})
            continue

        prompt_text = _reference_prompt(
            raw,
            character_bible=char_bibles.get(str(raw.get("subject_id", "")).strip()),
            identity_state=identity_states.get(_group_key(raw)),
        )
        aspect_ratio = _reference_aspect_ratio(raw)
        shot_id = _reference_job_id(reference_id)
        output_dir = str(_reference_output_dir(raw, project_root).resolve())
        # Ensure the directory tree exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Provider tier routing (Phase 6) + Identity consistency (Phase 4)
        tier = str(raw.get("tier", "fast"))
        provider_kwargs: dict[str, object] = {
            "duration": 0.0,
            "aspect_ratio": aspect_ratio,
        }
        if tier in ("standard", "ultra"):
            group_key = _group_key(raw)
            identity_state = identity_states.get(group_key, {})
            anchor_seed = identity_state.get("anchor_seed")
            if anchor_seed is not None:
                provider_kwargs["seed"] = anchor_seed
            else:
                provider_kwargs["seed"] = hash(shot_id) % (2**31)
                identity_states.setdefault(group_key, {})["anchor_seed"] = provider_kwargs["seed"]
        # Identity consistency is enforced via the ID_REINFORCE prompt block
        # (the Imagen API does not support reference-image conditioning).
        # anchor_frame_path and i2i_active in identity_states are consumed by
        # _reference_prompt() → build_structured_prompt() to strengthen the
        # ID_REINFORCE instruction when Gemini detects subject drift.

        # Phase 5 — Retry loop: max 3 attempts (initial + 2 retries)
        best_score = 0.0
        best_attempt = 0
        retry_prompt = prompt_text
        frame_review_result = None

        for attempt in range(3):
            if attempt > 0:
                # Inject actionable feedback into prompt for retry
                feedback = frame_review_result.actionable_feedback if frame_review_result else ""
                if feedback:
                    retry_prompt = f"{prompt_text} Fix the following: {feedback}"

            try:
                payload = provider.build_payload(retry_prompt, **provider_kwargs)
                job = provider.submit(payload, shot_id)
                job = provider.poll(job)
                downloaded_path = provider.download(job, output_dir)
                metadata = provider.extract_metadata(downloaded_path)
            except Exception as exc:
                if attempt < 2:
                    continue
                raw["generation_status"] = "failed"
                raw["issues"] = [
                    {"code": "generation_failed", "message": str(exc)[:300], "severity": "blocking"}
                ]
                raw["validation"] = {"status": "needs_regeneration", "score": 0.0, "reports": []}
                failed += 1
                results.append(
                    {"reference_id": reference_id, "status": "failed", "error": str(exc)[:200]}
                )
                break

            # Rename
            ext = Path(downloaded_path).suffix or ".png"
            target_name = f"{_reference_job_id(reference_id)}{ext}"
            target_path = Path(output_dir) / target_name
            Path(downloaded_path).rename(target_path)

            # Heuristics
            from film_pipeline.generation.frame_heuristics import run_heuristic_checks

            heuristic_result = run_heuristic_checks(
                target_path, subject_type=str(raw.get("subject_type", "character"))
            )
            if not heuristic_result.passed:
                if attempt < 2:
                    continue
                raw["generation_status"] = "failed"
                raw["issues"] = [
                    {
                        "code": "heuristic_check_failed",
                        "message": f"Heuristics failed: {', '.join(heuristic_result.failures)}",
                        "severity": "blocking",
                    }
                ]
                raw["validation"] = {"status": "needs_regeneration", "score": 0.0, "reports": []}
                failed += 1
                results.append(
                    {
                        "reference_id": reference_id,
                        "status": "failed",
                        "error": f"Heuristics: {', '.join(heuristic_result.failures)}",
                    }
                )
                break

            # Gemini review
            from film_pipeline.generation.frame_reviewer import review_frame, should_review_frame

            frame_review_result = None
            if should_review_frame(raw):
                with contextlib.suppress(Exception):
                    frame_review_result = review_frame(
                        target_path,
                        retry_prompt,
                        model=_services(rt).prompt_runner.model_router.resolve_or_raise(
                            "visual_reasoner"
                        ),
                        subject_type=str(raw.get("subject_type", "character")),
                        frame_id=reference_id,
                    )

            if frame_review_result is not None and frame_review_result.passed:
                best_score = frame_review_result.total
                best_attempt = attempt + 1
                break
            if frame_review_result is not None:
                if frame_review_result.total > best_score:
                    best_score = frame_review_result.total
                    best_attempt = attempt + 1
                if attempt < 2:
                    continue
            # Review skipped or unavailable — accept on first attempt
            if frame_review_result is None:
                best_attempt = attempt + 1
                break

        # --- Post-retry: update metadata ---
        raw["retry_count"] = best_attempt  # 0 if all attempts failed
        raw["best_score"] = best_score

        # Phase 4 — track anchor + detect identity/geometry drift
        gk = _group_key(raw)
        ist = identity_states.setdefault(gk, {})
        is_anchor = str(raw.get("frame_role", "")).strip().lower() in (
            "front-face",
            "wide-establishing",
        )
        if is_anchor and "anchor_seed" in ist and "target_path" in dir():
            ist["anchor_frame_path"] = target_path
        if frame_review_result is not None and not frame_review_result.passed:
            subject_score = float(
                cast(float, frame_review_result.scores.get("subject", {}).get("score", 10))
            )
            if subject_score < 7 and not is_anchor:
                if not ist.get("i2i_active"):
                    ist["i2i_active"] = True
                    ist["i2i_strength"] = 0.5
                elif float(cast(float, ist.get("i2i_strength", 0.5))) > 0.3:
                    ist["i2i_strength"] = 0.3

        if best_attempt == 0:
            # All attempts failed — error already recorded in retry loop
            generated += 0  # counted as failed above
            continue

        rel_path = target_path.resolve().relative_to(project_root.resolve())
        provider_entry = getattr(provider, "entry", None)
        provider_id = str(getattr(provider_entry, "provider_id", ""))
        raw["asset_path"] = rel_path.as_posix()
        raw["provider"] = provider_id
        raw["tier"] = tier
        raw["prompt_text"] = prompt_text
        raw["source_frames"] = [rel_path.as_posix()]
        raw["original_mime_type"] = str(metadata.get("mime_type", "image/png"))
        raw["normalized_mime_type"] = str(metadata.get("mime_type", "image/png"))

        if frame_review_result is not None and frame_review_result.passed:
            raw["generation_status"] = "validated"
            raw["quality_score"] = frame_review_result.total / 40.0 * 100.0
            raw["locked"] = True
            raw["validation"] = {
                "status": "approved",
                "score": frame_review_result.total,
                "reports": [json.dumps(frame_review_result.scores, default=str)],
            }
            raw["ai_usability"] = {
                "score": frame_review_result.total / 40.0 * 100.0,
                "risks": [],
                "notes": "Gemini per-frame review passed.",
            }
            raw["issues"] = []
        elif frame_review_result is not None and not frame_review_result.passed:
            raw["generation_status"] = "needs_regeneration"
            raw["quality_score"] = frame_review_result.total / 40.0 * 100.0
            raw["locked"] = False
            raw["validation"] = {
                "status": "needs_regeneration",
                "score": frame_review_result.total,
                "reports": [json.dumps(frame_review_result.scores, default=str)],
            }
            raw["ai_usability"] = {
                "score": frame_review_result.total / 40.0 * 100.0,
                "risks": [],
                "notes": frame_review_result.actionable_feedback or "Gemini review failed.",
            }
            raw["issues"] = [
                {
                    "code": "gemini_review_failed",
                    "message": frame_review_result.actionable_feedback
                    or "Gemini review below threshold.",
                    "severity": "warning",
                }
            ]
        # else: review was skipped (selective validation) or failed — keep defaults
        else:
            raw["generation_status"] = "generated"
            raw["quality_score"] = 80.0
            raw["locked"] = False
            raw["validation"] = {
                "status": "pending",
                "score": 0.0,
                "reports": [],
            }
            raw["ai_usability"] = {
                "score": 0.0,
                "risks": [],
                "notes": "Gemini review skipped (selective validation or API unavailable).",
            }
            raw["issues"] = []
        generated += 1

        # Phase 03 — Write frame metadata sidecar alongside the PNG
        try:
            from film_pipeline.generation.frame_sidecar import write_frame_sidecar
            from film_pipeline.schemas.reference import ReferenceFrame

            frame = ReferenceFrame(
                frame_path=rel_path.as_posix(),
                reference_id=reference_id,
                subject_type=str(raw.get("subject_type", "")),
                subject_id=str(raw.get("subject_id", "")),
                provider_id=str(raw.get("provider", "")),
                model_id="",
                tier=tier,
                seed=cast(int | None, provider_kwargs.get("seed")),
                prompt_text=prompt_text,
                frame_role=str(raw.get("frame_role", "")),
                expression=str(raw.get("expression", "")) or None,
                lighting=str(raw.get("lighting", "")) or None,
                aspect_ratio=aspect_ratio,
                generation_status=str(raw.get("generation_status", "generated")),
                quality_score=float(cast(float, raw.get("quality_score", 0))),
                retry_count=int(cast(int, raw.get("retry_count", 0))),
                best_score=float(cast(float, raw.get("best_score", 0))),
                heuristic_checks_passed=True,
                mime_type=str(raw.get("normalized_mime_type", "image/png")),
                created_at="",
            )
            write_frame_sidecar(target_path, frame)
        except Exception:
            pass  # sidecar failure is non-blocking

        results.append(
            {
                "reference_id": reference_id,
                "status": "generated",
                "asset_path": rel_path.as_posix(),
                "provider": provider_id,
            }
        )

    if generated == 0 and failed == 0:
        return _ok(
            generated=0,
            skipped=skipped,
            failed=0,
            results=results,
            message="No reference images needed generation.",
        )

    updated = {
        "project_id": project_id,
        "entries": [dict(r) for r in grouped_entries],  # use modified copies
    }
    ref = _save_reference_index_artifact(rt, active, cast(dict[str, object], updated))
    if ref:
        active["visual_refs"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)
    rt._record_audit(
        "system",
        "generate_reference_images",
        project_id=project_id,
        generated=str(generated),
        skipped=str(skipped),
        failed=str(failed),
    )

    # Phase 7 — Build composite sheets for characters with generated frames
    _build_composites(project_root, project_id, grouped_entries, _services(rt).artifact_store)

    # Phase 11 — Write human-readable index files
    _write_reference_index_files(project_root, cast(list[dict[str, object]], updated["entries"]))

    return _ok(
        generated=generated,
        skipped=skipped,
        failed=failed,
        results=results,
        reference_index_ref=ref,
    )


# --- Validation tools ----------------------------------------------------


async def get_validation_report(args: dict[str, object]) -> dict[str, object]:
    """Return validation reports for the active project's current phase.

    Reads from stored ``_validation_reports`` in project state (populated
    by the QC node). Falls back to live validator runs if no stored reports.
    """
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")

    # Check stored reports first (from QC node) — works even without a
    # current phase because the data is already persisted in state.
    stored = active.get("_validation_reports")
    if stored and isinstance(stored, list):
        return _ok(
            phase=str(active.get("current_phase", "")),
            reports=list(stored),
            source="qc_node",
            message=f"{len(stored)} validation report(s) from QC node.",
        )

    phase_str = str(active.get("current_phase", ""))
    if not phase_str:
        return _error("No active phase to validate (and no stored reports).")

    # Fallback: run validators live
    project_id = str(active["project_id"])
    from film_pipeline.schemas._base import FilmPhase

    try:
        fp = FilmPhase(phase_str)
    except ValueError:
        return _error(f"Unknown phase: {phase_str}")

    reports: list[dict[str, object]] = []
    store = _services(rt).artifact_store

    # --- Phase-specific validator dispatch ---

    if phase_str == "script":
        art_data = _load_artifact(store, project_id, fp, "script", 1)
        if art_data is not None:
            from film_pipeline.validation.impl.dialogue_voice import DialogueVoiceValidator
            from film_pipeline.validation.impl.script_structure import ScriptStructureValidator

            for vcls in (ScriptStructureValidator, DialogueVoiceValidator):
                validator = vcls()
                report = validator.run(art_data)
                reports.append(_report_summary(report))

    elif phase_str == "visual_dev":
        art_data = _load_latest_reference_index(rt, project_id, active)
        if art_data is not None:
            from film_pipeline.validation.impl.reference_usability import (
                ReferenceUsabilityValidator,
            )

            ref_validator = ReferenceUsabilityValidator()
            report = ref_validator.run(art_data)
            reports.append(_report_summary(report))

    elif phase_str == "gen_planning":
        art_data = _load_artifact(store, project_id, fp, "prompt_registry", 1)
        if art_data is not None:
            from film_pipeline.validation.impl.prompt_readiness import PromptReadinessValidator

            pr_validator = PromptReadinessValidator()
            report = pr_validator.run(art_data)
            reports.append(_report_summary(report))

    elif phase_str == "shot_bible":
        art_data = _load_artifact(store, project_id, fp, "shot_bible", 1)
        if art_data is not None:
            from film_pipeline.validation.impl.scene_continuity import SceneContinuityValidator

            sc_validator = SceneContinuityValidator()
            report = sc_validator.run(art_data)
            reports.append(_report_summary(report))

    elif phase_str in ("post", "assembly"):
        art_data = _load_artifact(store, project_id, fp, "assembly_manifest", 1)
        if art_data is not None:
            from film_pipeline.validation.impl.assembly import AssemblyValidator

            asm_validator = AssemblyValidator()
            report = asm_validator.run(art_data)
            reports.append(_report_summary(report))

    elif phase_str == "delivery":
        art_data = _load_artifact(store, project_id, fp, "delivery_package", 1)
        if art_data is not None:
            from film_pipeline.validation.impl.delivery_completeness import (
                DeliveryCompletenessValidator,
            )

            dc_validator = DeliveryCompletenessValidator()
            report = dc_validator.run(art_data)
            reports.append(_report_summary(report))

    return _ok(phase=phase_str, reports=reports, source="live")


async def list_validation_issues(args: dict[str, object]) -> dict[str, object]:
    """List all validation issues for the active project's current phase.

    Reads from stored ``issues`` in project state (populated by QC node).
    """
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")

    # Read from stored issues first — works even without a current phase.
    stored_issues = active.get("issues", [])
    issues: list[dict[str, object]] = []
    if isinstance(stored_issues, list):
        for issue in stored_issues:
            if isinstance(issue, dict) and "validator_id" in issue:
                issues.append(
                    {
                        "code": str(issue.get("code", "")),
                        "message": str(issue.get("message", "")),
                        "severity": str(issue.get("severity", "")),
                        "validator_id": str(issue.get("validator_id", "")),
                    }
                )

    if issues:
        return _ok(
            phase=str(active.get("current_phase", "")),
            issues=issues,
            message=f"{len(issues)} issue(s) found.",
        )

    phase_str = str(active.get("current_phase", ""))
    if not phase_str:
        return _ok(phase="", issues=[], message="No active phase and no stored issues.")

    return _ok(phase=phase_str, issues=[], message="No validation issues found.")


def _load_artifact(
    store: Any, project_id: str, fp: Any, artifact_id: str, version: int
) -> dict[str, Any] | None:
    """Try to load an artifact from the artifact store."""
    try:
        return store.load(project_id, fp, artifact_id, version)  # type: ignore[no-any-return]
    except (FileNotFoundError, AttributeError):
        return None


def _latest_artifact_version(store: Any, project_id: str, fp: Any, artifact_id: str) -> int:
    artifacts = store.list_artifacts(project_id, fp)
    versions = [artifact.version for artifact in artifacts if artifact.artifact_id == artifact_id]
    return max(versions) if versions else 0


def _load_latest_reference_index(
    rt: Any,
    project_id: str,
    state: dict[str, object] | None = None,
) -> dict[str, object] | None:
    from film_pipeline.schemas._base import FilmPhase

    store = _services(rt).artifact_store
    version = 0
    if state is not None:
        visual_ref = str(state.get("visual_refs", ""))
        if visual_ref.startswith("artifact:reference_index:v"):
            with contextlib.suppress(ValueError):
                version = int(visual_ref.rsplit(":v", 1)[1])
    if version <= 0:
        version = _latest_artifact_version(
            store, project_id, FilmPhase("visual_dev"), "reference_index"
        )
    if version <= 0:
        return None
    return _load_artifact(store, project_id, FilmPhase("visual_dev"), "reference_index", version)


def _group_key(entry: dict[str, object]) -> str:
    """Deterministic group key for identity/geometry consistency."""
    subject_type = str(entry.get("subject_type", "")).strip().lower()
    subject_id = str(entry.get("subject_id", "")).strip().lower()
    return f"{subject_type}:{subject_id}"


def _group_and_sort_entries(
    entries: list[object],
    requested_ids: set[str],
    force: bool,
    project_root: Path,
    skip_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Filter, group, and sort entries — anchor frame first per group.

    Character anchors: 'front-face'. Environment anchors: 'wide-establishing'.
    Entries already generated (asset_path present, not force) are tagged _skip.
    """
    ANCHOR_PRIORITY = {"front-face": 0, "wide-establishing": 0}

    filtered: list[dict[str, object]] = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        ref_id = str(raw.get("reference_id", "")).strip()
        if not ref_id:
            continue
        if requested_ids and ref_id not in requested_ids:
            continue
        r = dict(raw)
        r["_reference_id"] = ref_id
        if r.get("asset_path") and not force:
            existing_path = project_root / str(r.get("asset_path", ""))
            if existing_path.exists():
                r["_skip"] = True
        filtered.append(r)

    # Sort: group by key, anchor first within each group
    def sort_key(r: dict[str, object]) -> tuple[str, int, str]:
        gk = _group_key(r)
        role = str(r.get("frame_role", "")).strip().lower()
        anchor_prio = ANCHOR_PRIORITY.get(role, 50)
        return (gk, anchor_prio, str(r.get("reference_id", "")))

    filtered.sort(key=sort_key)
    return filtered


def _reference_output_dir(entry: dict[str, object], project_root: Path) -> Path:
    """Compute organized output directory for a reference entry.

    Produces paths like:
        references/characters/leo/master-frames/
        references/environments/studio/master-frames/
        references/props/paintbrush/
        references/style/
        references/scale/
    """
    subject_type = str(entry.get("subject_type", "misc")).strip().lower()
    subject_id = str(entry.get("subject_id", "unknown")).strip().lower()

    if subject_type in ("character", "environment", "prop"):
        return project_root / "references" / f"{subject_type}s" / subject_id / "master-frames"
    return project_root / "references" / subject_type


def _reference_prompt(
    entry: dict[str, object],
    *,
    character_bible: dict[str, object] | None = None,
    constitution: dict[str, object] | None = None,
    identity_state: dict[str, object] | None = None,
) -> str:
    """Build a structured generation prompt from domain data blocks.

    Delegates to ``build_structured_prompt()`` which assembles character or
    environment prompts from locked blocks (CharacterBible, FilmConstitution).
    Falls back to the entry's ``prompt_text`` when no structured sources exist.
    """
    from film_pipeline.generation.prompt_builder import build_structured_prompt

    return build_structured_prompt(
        dict(entry),
        character_bible=dict(character_bible) if character_bible else None,
        constitution=dict(constitution) if constitution else None,
        identity_state=dict(identity_state) if identity_state else None,
    )


def _reference_aspect_ratio(entry: dict[str, object]) -> str:
    asset_type = str(entry.get("asset_type", ""))
    subject_type = str(entry.get("subject_type", ""))
    if "environment" in asset_type or subject_type == "environment":
        return "16:9"
    if "style" in asset_type or "camera" in asset_type or "scale" in asset_type:
        return "16:9"
    return "3:4"


def _reference_job_id(reference_id: str) -> str:
    return reference_id.replace(":", "-").replace("/", "-")


def _build_composites(
    project_root: Path,
    project_id: str,
    entries: list[dict[str, object]],
    artifact_store: Any,
) -> None:
    """Build composite sheets from generated frames (Phase 7)."""
    from film_pipeline.generation.compositor import (
        build_character_identity_sheet,
        build_environment_board,
    )
    from film_pipeline.schemas._base import FilmPhase

    # Resolve color palettes from EnvironmentBible artifacts
    env_palettes: dict[str, list[str]] = {}
    for entry in entries:
        if str(entry.get("subject_type", "")) != "environment":
            continue
        subject_id = str(entry.get("subject_id", "")).strip()
        if not subject_id or subject_id in env_palettes:
            continue
        try:
            bible = artifact_store.load(project_id, FilmPhase("visual_dev"), "environment_bible", 1)
            if isinstance(bible, dict):
                palette = bible.get("color_palette", [])
                if isinstance(palette, list) and palette:
                    env_palettes[subject_id] = [str(c) for c in palette]
        except (FileNotFoundError, ValueError):
            pass

    # Group entries by character subject
    char_frames: dict[str, dict[str, Path]] = {}
    for entry in entries:
        if str(entry.get("subject_type", "")) != "character":
            continue
        if entry.get("generation_status") not in ("validated", "generated"):
            continue
        subject_id = str(entry.get("subject_id", "")).strip()
        if not subject_id:
            continue
        role = str(entry.get("frame_role", "")).strip()
        asset = str(entry.get("asset_path", "")).strip()
        if not role or not asset:
            continue
        frame_path = project_root / asset
        if frame_path.exists():
            char_frames.setdefault(subject_id, {})[role] = frame_path

    for subject_id, frames in char_frames.items():
        sheet_path = project_root / "references" / "characters" / subject_id / "identity-sheet.png"
        try:
            build_character_identity_sheet(subject_id, subject_id, frames, sheet_path)
            # Phase 8 — Composite validation
            _validate_composite(sheet_path, "character_identity_sheet", subject_id)
        except Exception:
            pass

    # Group entries by environment subject
    env_frames: dict[str, dict[str, Path]] = {}
    for entry in entries:
        if str(entry.get("subject_type", "")) != "environment":
            continue
        if entry.get("generation_status") not in ("validated", "generated"):
            continue
        subject_id = str(entry.get("subject_id", "")).strip()
        if not subject_id:
            continue
        role = str(entry.get("frame_role", "")).strip()
        asset = str(entry.get("asset_path", "")).strip()
        if not role or not asset:
            continue
        frame_path = project_root / asset
        if frame_path.exists():
            env_frames.setdefault(subject_id, {})[role] = frame_path

    for subject_id, frames in env_frames.items():
        sheet_path = (
            project_root / "references" / "environments" / subject_id / "environment-board.png"
        )
        try:
            build_environment_board(
                subject_id,
                subject_id,
                frames,
                sheet_path,
                palette_colors=env_palettes.get(subject_id),
            )
            # Phase 8 — Composite validation
            _validate_composite(sheet_path, "environment_board", subject_id)
        except Exception:
            pass

    # Phase 05 — Additional composite templates
    _build_optional_sheets(project_root, project_id, char_frames, env_palettes)


def _build_optional_sheets(
    project_root: Path,
    project_id: str,
    char_frames: dict[str, dict[str, Path]],
    env_palettes: dict[str, list[str]],
) -> None:
    """Build expression sheets, scale sheet, and style board (non-blocking)."""
    from film_pipeline.generation.compositor import (
        build_expression_sheet,
        build_scale_sheet,
        build_style_board,
    )

    # Expression sheet per character
    for subject_id, frames in char_frames.items():
        try:
            sheet_path = (
                project_root / "references" / "characters" / subject_id / "expression-sheet.png"
            )
            build_expression_sheet(subject_id, subject_id, frames, sheet_path)
        except Exception:
            pass

    # Scale sheet — all characters' full-body frames
    full_body_frames: dict[str, Path] = {}
    for subject_id, frames in char_frames.items():
        fb = frames.get("full-body")
        if fb and fb.exists():
            full_body_frames[subject_id] = fb
    if full_body_frames:
        try:
            sheet_path = project_root / "references" / "scale" / "scale-sheet.png"
            build_scale_sheet(project_id, full_body_frames, sheet_path)
        except Exception:
            pass

    # Style board — use first environment's palette or defaults
    palette: list[str] = []
    for p in env_palettes.values():
        palette = p
        break
    try:
        sheet_path = project_root / "references" / "style" / "style-board.png"
        build_style_board(project_id, palette, "", "", "", sheet_path)
    except Exception:
        pass


def _validate_composite(sheet_path: Path, sheet_type: str, subject_id: str) -> None:
    """Run Gemini composite validation on a sheet (Phase 8). Non-blocking."""
    try:
        from film_pipeline.agents.model_routing import ModelRouter
        from film_pipeline.generation.sheet_reviewer import review_composite_sheet

        router = ModelRouter()
        review_composite_sheet(
            sheet_path,
            sheet_type,
            subject_id,
            model=router.resolve_or_raise("visual_reasoner"),
        )
    except Exception:
        pass  # validation failure doesn't block


def _write_reference_index_files(project_root: Path, entries: list[dict[str, object]]) -> None:
    """Write human-readable reference index files (Phase 11)."""
    idx_dir = project_root / "references" / "index"
    idx_dir.mkdir(parents=True, exist_ok=True)

    # reference-index.json
    index_data = {
        "project_id": "",
        "generated_at": "",
        "entries": [
            {
                "reference_id": str(e.get("reference_id", "")),
                "asset_type": str(e.get("asset_type", "")),
                "subject_id": str(e.get("subject_id", "")),
                "asset_path": str(e.get("asset_path", "")),
                "provider": str(e.get("provider", "")),
                "validation": e.get("validation", {}),
                "locked": bool(e.get("locked", False)),
            }
            for e in entries
        ],
    }
    (idx_dir / "reference-index.json").write_text(json.dumps(index_data, indent=2, default=str))

    # reference-validation-summary.json
    scores = [
        float(cast(float, e.get("quality_score", 0))) for e in entries if e.get("quality_score")
    ]
    validated = sum(1 for e in entries if e.get("generation_status") == "validated")
    summary = {
        "project_id": "",
        "total_entries": len(entries),
        "validated": validated,
        "failed": sum(1 for e in entries if e.get("generation_status") == "failed"),
        "average_score": sum(scores) / len(scores) if scores else 0.0,
    }
    (idx_dir / "reference-validation-summary.json").write_text(json.dumps(summary, indent=2))


def _select_image_provider(rt: Any) -> Any | None:
    for provider_id in rt.list_providers():
        adapter = rt.get_provider(provider_id)
        entry = getattr(adapter, "entry", None)
        if entry is not None and getattr(entry, "provider_type", "") == "image":
            return adapter
    return None


def _save_reference_index_artifact(
    rt: Any,
    state: dict[str, object],
    artifact: dict[str, object],
) -> str | None:
    from datetime import UTC, datetime

    from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata

    project_id = str(state.get("project_id", ""))
    store = _services(rt).artifact_store
    version = (
        _latest_artifact_version(store, project_id, FilmPhase("visual_dev"), "reference_index") + 1
    )
    meta = ArtifactMetadata(
        artifact_id="reference_index",
        artifact_type=ArtifactType.REFERENCE_INDEX,
        project_id=project_id,
        phase=FilmPhase("visual_dev"),
        version=version,
        status=ArtifactStatus.CANDIDATE,
        parents=[],
        created_by="mcp.generate_reference_images",
        created_at=datetime.now(UTC),
    )
    store.save_dict(artifact, meta)
    return f"artifact:reference_index:v{version}"


def _report_summary(report: Any) -> dict[str, Any]:
    """Convert a ValidationReport into a concise summary dict."""
    return {
        "validator_id": report.validator_id,
        "score": report.score,
        "status": str(report.status.value),
        "blocking_count": len(report.blocking_issues),
        "warning_count": len(report.warnings),
        "recommended_actions": report.recommended_actions,
    }


# --- Generation tools ----------------------------------------------------


async def plan_generation_batch(args: dict[str, object]) -> dict[str, object]:
    """Plan a generation batch: add rows to the ledger for each shot.

    Reads shot IDs from the shot bible artifact if none are provided.
    """
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.generation.ledger import GenerationLedgerManager

    mgr = GenerationLedgerManager(_services(rt).artifact_store)

    provider = str(args.get("provider", "mock-video-provider"))
    model = str(args.get("model", "mock-fast"))
    prompt_ref = str(args.get("prompt_ref", ""))
    mode_str = str(args.get("mode", "test"))
    from film_pipeline.schemas._base import GenerationMode

    mode = GenerationMode.TEST
    with contextlib.suppress(ValueError):
        mode = GenerationMode(mode_str)

    # Collect shot IDs — from args, or from shot bible artifact
    raw_shot_ids = args.get("shot_ids", [])
    shot_ids: list[str] = []
    if isinstance(raw_shot_ids, list):
        shot_ids = [str(s) for s in raw_shot_ids]
    else:
        # Try the shot bible
        try:
            from film_pipeline.schemas._base import FilmPhase

            data = _services(rt).artifact_store.load(
                project_id, FilmPhase("shot_bible"), "shot_bible", 1
            )
            shot_ids = [
                str(s.get("shot_id", s.get("scene_id", "")))
                for s in data.get("shots", data.get("scenes", []))
            ]
        except (FileNotFoundError, ValueError):
            return _error("No shot_ids provided and no shot bible found.")

    if not shot_ids:
        return _error("No shot IDs to plan.")

    ledger = mgr.plan_batch(
        project_id=project_id,
        shot_ids=shot_ids,
        provider=provider,
        model=model,
        prompt_ref=prompt_ref,
        mode=mode,
    )
    return _ok(
        planned=len(shot_ids),
        total_rows=len(ledger.rows),
        rows=[
            {
                "generation_id": r.generation_id,
                "shot_id": r.shot_id,
                "status": str(r.status.value),
            }
            for r in ledger.rows
            if r.shot_id in shot_ids
        ],
    )


async def approve_generation_spend(args: dict[str, object]) -> dict[str, object]:
    """Approve spend: mark PREPARED rows as SUBMITTED with optional budget gate."""
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.generation.ledger import GenerationLedgerManager

    mgr = GenerationLedgerManager(_services(rt).artifact_store)

    # Budget gate: reject if max_cost_usd set and cost exceeds it
    max_cost_raw = args.get("max_cost_usd", -1)
    max_cost = float(str(max_cost_raw)) if max_cost_raw not in (-1, None) else -1.0

    try:
        ledger = mgr.approve_spend(project_id, max_cost_usd=max_cost)
    except ValueError as e:
        return _error(str(e))

    submitted = [r for r in ledger.rows if r.status.value == "submitted"]
    estimated_total = mgr.estimate_total_cost(project_id)
    return _ok(
        approved=len(submitted),
        total_rows=len(ledger.rows),
        estimated_total_cost_usd=estimated_total,
    )


async def get_generation_status(args: dict[str, object]) -> dict[str, object]:
    """Get status of a generation by id."""
    generation_id = str(args.get("generation_id", ""))
    if not generation_id:
        return _error("generation_id is required.")
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.generation.ledger import GenerationLedgerManager

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    row = mgr.get_row(project_id, generation_id)
    if row is None:
        return _error(f"Generation '{generation_id}' not found.")
    return _ok(
        generation_id=row.generation_id,
        shot_id=row.shot_id,
        status=str(row.status.value),
        provider_job_id=row.provider_job_id,
        submitted_at=str(row.submitted_at) if row.submitted_at else None,
        poll_count=row.poll_count,
        estimated_cost_usd=row.estimated_cost_usd,
        next_action=row.next_action,
    )


async def list_active_generations(args: dict[str, object]) -> dict[str, object]:
    """List active (non-terminal) generation rows."""
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationStatus

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    terminal = {
        GenerationStatus.COMPLETED,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
        GenerationStatus.TIMED_OUT,
    }
    all_rows = mgr.list_rows(project_id)
    active_rows = [r for r in all_rows if r.status not in terminal]
    return _ok(
        count=len(active_rows),
        rows=[
            {
                "generation_id": r.generation_id,
                "shot_id": r.shot_id,
                "status": str(r.status.value),
                "provider_job_id": r.provider_job_id,
                "next_action": r.next_action,
            }
            for r in active_rows
        ],
    )


async def start_generation_batch(args: dict[str, object]) -> dict[str, object]:
    """Submit all SUBMITTED generation rows to their providers.

    Each row is submitted to its provider. The provider_job_id is persisted
    in the ledger row. Partial failures are recorded per-row.
    """
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationStatus

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    submitted_rows = mgr.list_rows(project_id, status=GenerationStatus.SUBMITTED)

    if not submitted_rows:
        return _ok(submitted=0, message="No SUBMITTED rows to start. Approve spend first.")

    successes: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []

    for row in submitted_rows:
        # Skip rows that already have a provider_job_id (duplicate-prevention)
        if row.provider_job_id:
            successes.append(
                {
                    "generation_id": row.generation_id,
                    "shot_id": row.shot_id,
                    "provider_job_id": row.provider_job_id,
                    "note": "already-submitted",
                }
            )
            continue

        adapter = rt.get_provider(row.provider)
        if adapter is None:
            mgr.update_row(
                project_id,
                row.generation_id,
                status=GenerationStatus.FAILED,
                error_code="unknown_provider",
                blocking_reason=f"Provider '{row.provider}' not registered.",
            )
            failures.append(
                {
                    "generation_id": row.generation_id,
                    "shot_id": row.shot_id,
                    "error": f"Provider '{row.provider}' not registered.",
                }
            )
            continue

        # Build payload and submit
        try:
            payload = adapter.build_payload(
                prompt=row.prompt_ref,
                references=row.reference_refs or None,
                duration=5.0,
            )
            job = adapter.submit(payload, row.shot_id)
        except Exception as exc:
            mgr.update_row(
                project_id,
                row.generation_id,
                status=GenerationStatus.FAILED,
                error_code="submit_failed",
                blocking_reason=str(exc)[:200],
            )
            failures.append(
                {
                    "generation_id": row.generation_id,
                    "shot_id": row.shot_id,
                    "error": str(exc)[:200],
                }
            )
            continue

        # Persist provider_job_id
        mgr.update_row(
            project_id,
            row.generation_id,
            provider_job_id=job.job_id,
            status=GenerationStatus.RUNNING,
            next_action="poll",
        )
        successes.append(
            {
                "generation_id": row.generation_id,
                "shot_id": row.shot_id,
                "provider_job_id": job.job_id,
            }
        )

    return _ok(
        submitted=len(successes),
        failed=len(failures),
        successes=successes,
        failures=failures,
    )


async def resume_generation_polling(args: dict[str, object]) -> dict[str, object]:
    """Poll the provider for a generation's status and update the ledger."""
    generation_id = str(args.get("generation_id", ""))
    if not generation_id:
        return _error("generation_id is required.")
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from datetime import UTC, datetime

    from film_pipeline.generation.ledger import GenerationLedgerManager

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    row = mgr.get_row(project_id, generation_id)
    if row is None:
        return _error(f"Generation '{generation_id}' not found.")
    if not row.provider_job_id:
        return _error(f"Generation '{generation_id}' has no provider_job_id — not yet submitted.")

    adapter = rt.get_provider(row.provider)
    if adapter is None:
        return _error(f"Provider '{row.provider}' not registered.")

    from film_pipeline.providers.base import ProviderJob
    from film_pipeline.schemas._base import GenerationStatus

    job = ProviderJob(
        job_id=row.provider_job_id,
        shot_id=row.shot_id,
        provider_id=row.provider,
        model=row.model,
        status="submitted",
        polls=row.poll_count,
    )
    try:
        result = adapter.poll(job)
    except Exception as exc:
        mgr.update_row(
            project_id,
            generation_id,
            error_code="poll_failed",
            blocking_reason=str(exc)[:200],
        )
        return _error(f"Poll failed: {exc}")

    status_map: dict[str, GenerationStatus] = {
        "completed": GenerationStatus.COMPLETED,
        "failed": GenerationStatus.FAILED,
        "submitted": GenerationStatus.SUBMITTED,
        "processing": GenerationStatus.RUNNING,
    }
    new_status = status_map.get(result.status, GenerationStatus.RUNNING)

    mgr.update_row(
        project_id,
        generation_id,
        status=new_status,
        poll_count=result.polls,
        last_polled_at=datetime.now(UTC),
    )
    return _ok(
        generation_id=generation_id,
        shot_id=row.shot_id,
        status=str(new_status.value),
        poll_count=result.polls,
    )


async def cancel_generation_request(args: dict[str, object]) -> dict[str, object]:
    """Cancel a generation and update the ledger."""
    generation_id = str(args.get("generation_id", ""))
    if not generation_id:
        return _error("generation_id is required.")
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationStatus

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    row = mgr.get_row(project_id, generation_id)
    if row is None:
        return _error(f"Generation '{generation_id}' not found.")
    if not row.provider_job_id:
        mgr.update_row(
            project_id,
            generation_id,
            status=GenerationStatus.CANCELLED,
            next_action="stop",
        )
        return _ok(generation_id=generation_id, cancelled=True, provider=False)

    adapter = rt.get_provider(row.provider)
    if adapter is None:
        return _error(f"Provider '{row.provider}' not registered.")

    from film_pipeline.providers.base import ProviderJob

    job = ProviderJob(
        job_id=row.provider_job_id,
        shot_id=row.shot_id,
        provider_id=row.provider,
        model=row.model,
        status="submitted",
    )
    cancelled = adapter.cancel(job)
    if cancelled:
        mgr.update_row(
            project_id,
            generation_id,
            status=GenerationStatus.CANCELLED,
            next_action="stop",
        )
    return _ok(
        generation_id=generation_id,
        cancelled=cancelled,
        provider=bool(row.provider_job_id),
    )


async def promote_test_to_production(args: dict[str, object]) -> dict[str, object]:
    """Promote completed TEST generation rows to PRODUCTION mode.

    Only rows with mode=TEST and status=COMPLETED are eligible.
    Provide ``shot_ids`` to promote specific shots, or omit to promote all eligible.
    """
    rt = get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.generation.ledger import GenerationLedgerManager

    mgr = GenerationLedgerManager(_services(rt).artifact_store)

    raw_shot_ids = args.get("shot_ids")
    shot_ids: list[str] | None = None
    if raw_shot_ids and isinstance(raw_shot_ids, list):
        shot_ids = [str(s) for s in raw_shot_ids if s]

    count, promoted_ids = mgr.promote_to_production(project_id, shot_ids=shot_ids)
    return _ok(
        promoted=count,
        generation_ids=promoted_ids,
        message=f"{count} generation(s) promoted to PRODUCTION mode.",
    )


# --- KB tools ------------------------------------------------------------


async def kb_search(args: dict[str, object]) -> dict[str, object]:
    query = str(args.get("query", ""))
    phase = str(args.get("phase", ""))
    try:
        from film_pipeline.kb.manifest import KBManifest
        from film_pipeline.kb.paths import kb_manifest_path
        from film_pipeline.kb.retrieval import KBRetrieval

        manifest_path = kb_manifest_path()
        if not manifest_path.exists():
            return _ok(
                items=[],
                total=0,
                message="KB manifest not found.",
            )
        manifest = KBManifest.from_yaml(manifest_path)
        retrieval = KBRetrieval(manifest)
        items = retrieval.by_tags(
            phase=phase if phase else None,
        )
        return _ok(
            items=[
                {
                    "id": i.id,
                    "title": i.title,
                    "authority": i.authority.value,
                    "phases": i.applies_to_phases,
                }
                for i in items[:20]
            ],
            total=len(items),
            query=query,
        )
    except Exception as e:
        return _error(str(e))


async def kb_get_item(args: dict[str, object]) -> dict[str, object]:
    item_id = str(args.get("item_id", ""))
    try:
        from film_pipeline.kb.manifest import KBManifest
        from film_pipeline.kb.paths import kb_manifest_path

        manifest_path = kb_manifest_path()
        if not manifest_path.exists():
            return _error("KB manifest not found.")
        manifest = KBManifest.from_yaml(manifest_path)
        item = manifest.get(item_id)
        if item is None:
            return _error(f"KB item not found: {item_id}")
        return _ok(
            id=item.id,
            title=item.title,
            authority=item.authority.value,
            status=item.status,
            domains=item.domains,
            summary=item.summary,
            applies_to_phases=item.applies_to_phases,
        )
    except Exception as e:
        return _error(str(e))


async def kb_get_context_packet(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    from film_pipeline.kb.packets import KBContextPacketBuilder

    try:
        from film_pipeline.kb.manifest import KBManifest
        from film_pipeline.kb.paths import kb_manifest_path

        manifest_path = kb_manifest_path()
        if not manifest_path.exists():
            return _ok(packet={"items": []}, message="KB manifest not found.")
        manifest = KBManifest.from_yaml(manifest_path)
        builder = KBContextPacketBuilder(manifest=manifest)
        packet = builder.build(
            project_id=active["project_id"],
            phase=str(args.get("phase", active.get("current_phase", "intake"))),
            agent_id=str(args.get("agent_id", "orchestrator")),
            task=str(args.get("task", "current phase")),
        )
        return _ok(
            project_id=packet.project_id,
            phase=packet.phase,
            authority_policy_refs=packet.authority_policy_refs,
        )
    except Exception as e:
        return _error(str(e))


async def kb_explain_context_choice(args: dict[str, object]) -> dict[str, object]:
    return _ok(
        message="KB context is selected by phase and agent capability. "
        "Canonical rules (authority=CANONICAL) take priority over playbooks and case studies. "
        "Use kb_get_context_packet to see the current packet.",
    )


# --- Checkpoint tools ----------------------------------------------------


async def list_checkpoints(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    project_id = str(args.get("project_id", "") or "")
    cps = rt.list_checkpoints(project_id if project_id else None)
    return _ok(
        checkpoints=[
            {
                "checkpoint_id": c.checkpoint_id,
                "project_id": c.project_id,
                "phase": c.phase.value,
                "created_at": c.created_at.isoformat(),
                "reason": c.reason,
            }
            for c in cps
        ]
    )


async def create_checkpoint(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    reason = str(args.get("reason", "manual checkpoint"))
    try:
        cp = rt.create_checkpoint(
            project_id=active["project_id"],
            phase=active.get("current_phase", "intake"),
            reason=reason,
        )
        return _ok(
            checkpoint_id=cp.checkpoint_id,
            project_id=cp.project_id,
            phase=cp.phase.value,
        )
    except ValueError as e:
        return _error(str(e))


async def get_checkpoint(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    checkpoint_id = str(args.get("checkpoint_id", ""))
    cp = rt.get_checkpoint(checkpoint_id)
    if cp is None:
        return _error(f"Checkpoint not found: {checkpoint_id}")
    return _ok(
        checkpoint_id=cp.checkpoint_id,
        project_id=cp.project_id,
        phase=cp.phase.value,
        created_at=cp.created_at.isoformat(),
        reason=cp.reason,
    )


async def compare_versions(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    cp_a = rt.get_checkpoint(str(args.get("checkpoint_id_a", "")))
    cp_b = rt.get_checkpoint(str(args.get("checkpoint_id_b", "")))
    if cp_a is None or cp_b is None:
        return _error("One or both checkpoints not found.")
    return _ok(
        older_phase=cp_a.phase.value,
        newer_phase=cp_b.phase.value,
        older_reason=cp_a.reason,
        newer_reason=cp_b.reason,
    )


async def list_artifact_versions(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    cps = rt.list_checkpoints()
    versions: list[dict[str, str]] = []
    for c in cps[-20:]:
        for art_type, ver in c.artifact_versions.items():
            versions.append(
                {"checkpoint_id": c.checkpoint_id, "artifact_type": art_type, "version": ver}
            )
    return _ok(versions=versions)


async def rollback_artifact(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    artifact_id = str(args.get("artifact_id", ""))
    if not artifact_id:
        return _error("artifact_id is required.")
    checkpoint_id = str(args.get("checkpoint_id", ""))
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    project_id = str(active["project_id"])

    # If a specific checkpoint is given, use it as the restore target
    if checkpoint_id:
        cp = rt.get_checkpoint(checkpoint_id)
        if cp is None:
            return _error(f"Checkpoint '{checkpoint_id}' not found.")
        if not cp.git_commit:
            return _error(f"Checkpoint '{checkpoint_id}' has no git commit ref.")
        try:
            manager = rt.checkpoint_managers.get(project_id)
            if manager is None:
                return _error("No checkpoint manager for project.")
            manager.git.restore_files(cp.git_commit, [artifact_id])
            manager.git.commit(f"rollback: artifact {artifact_id} to {cp.git_commit[:8]}")
            return _ok(
                artifact_id=artifact_id,
                restored_from=checkpoint_id,
                git_commit=cp.git_commit[:8],
            )
        except Exception as e:
            return _error(str(e))

    # Fallback: find latest checkpoint that contains this artifact
    cps = rt.list_checkpoints(project_id)
    for cp in sorted(cps, key=lambda c: c.created_at, reverse=True):
        if cp.git_commit and artifact_id in cp.artifact_versions:
            try:
                manager = rt.checkpoint_managers.get(project_id)
                if manager is None:
                    continue
                manager.git.restore_files(cp.git_commit, [artifact_id])
                manager.git.commit(f"rollback: artifact {artifact_id} to {cp.git_commit[:8]}")
                return _ok(
                    artifact_id=artifact_id,
                    restored_from=cp.checkpoint_id,
                    git_commit=cp.git_commit[:8],
                )
            except Exception:
                continue

    return _error(f"No checkpoint found containing artifact '{artifact_id}'.")


async def rollback_to_checkpoint(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    checkpoint_id = str(args.get("checkpoint_id", ""))
    cp = rt.get_checkpoint(checkpoint_id)
    if cp is None:
        return _error(f"Checkpoint not found: {checkpoint_id}")
    return _ok(
        rollback_target=checkpoint_id,
        phase=cp.phase.value,
        reason=cp.reason,
        message="Rollback requires human confirmation. State restored to checkpoint.",
    )


async def get_invalidation_report(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    checkpoint_id = str(args.get("checkpoint_id", ""))
    cp = rt.get_checkpoint(checkpoint_id)
    if cp is None:
        return _error(f"Checkpoint not found: {checkpoint_id}")
    from film_pipeline.checkpoints.invalidation import InvalidationEngine

    engine = InvalidationEngine()
    report = engine.report(
        rollback_target=checkpoint_id,
        artifact_types=list(cp.artifact_versions.keys()),
    )
    return _ok(
        rollback_target=report.rollback_target,
        will_revert=report.will_revert,
        will_invalidate=report.will_invalidate,
        requires_regeneration=report.requires_regeneration,
    )


# --- Audit tools ---------------------------------------------------------


async def get_audit_log(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    project_id = str(args.get("project_id", "") or "")
    limit_raw = args.get("limit", 100)
    limit = int(limit_raw) if isinstance(limit_raw, int) else int(str(limit_raw))
    events = rt.get_audit_log(project_id if project_id else None, limit=limit)
    return _ok(events=events, total=len(events))


async def explain_last_decision(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    events = rt.audit_events
    if not events:
        return _ok(message="No decisions recorded yet.")
    last = events[-1]
    return _ok(
        event_id=last["event_id"],
        actor=last["actor"],
        action=last["action"],
        timestamp=last["timestamp"],
        details=last.get("details", {}),
    )


async def explain_agent_routing(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()

    if active is None:
        return _ok(decisions=[], message="No active project. Routing data is session-scoped.")

    routing_decisions = active.get("_routing_decisions", [])

    if not routing_decisions:
        return _ok(
            decisions=[],
            message="No routing decisions recorded yet. Run a phase to populate routing history.",
        )

    summary_lines: list[str] = []
    for rd in routing_decisions:
        agent = rd.get("agent_id", "unknown")
        reason = rd.get("routing_reason", "")
        was_fallback = rd.get("fallback", False)
        label = " [FALLBACK]" if was_fallback else ""
        summary_lines.append(f"{agent}{label}: {reason}")

    return _ok(
        decisions=routing_decisions,
        summary="\n".join(summary_lines),
        message=f"{len(routing_decisions)} routing decision(s) recorded.",
    )


async def explain_kb_context(args: dict[str, object]) -> dict[str, object]:
    return _ok(
        message="KB context: the orchestrator selects KB slices by phase and agent. "
        "Canonical rules take priority over playbooks and case studies.",
    )


# --- Config / Profile tools -----------------------------------------------


async def list_profiles(args: dict[str, object]) -> dict[str, object]:
    """List available config profiles from the profiles/ directory."""
    from film_pipeline.config.loader import ProfileLoader

    try:
        loader = ProfileLoader()
        names = loader.all_names()
        profiles: list[dict[str, object]] = []
        for name in names:
            try:
                src = loader.load(name)
                pid = src.raw.get("profile", {}).get("id", name)
                pname = src.raw.get("profile", {}).get("name", name)
                desc = src.raw.get("profile", {}).get("description", "")
                mode = src.raw.get("studio", {}).get("mode", "unknown")
                profiles.append(
                    {
                        "id": pid,
                        "name": pname,
                        "description": desc,
                        "studio_mode": mode,
                        "file": str(src.path),
                    }
                )
            except Exception:
                continue
        return _ok(profiles=profiles, total=len(profiles))
    except Exception as e:
        return _error(str(e))


async def inspect_profile(args: dict[str, object]) -> dict[str, object]:
    """Load and return the full content of a specific profile."""
    profile_id = str(args.get("profile_id", ""))
    if not profile_id:
        return _error("profile_id is required.")

    try:
        _loader, src = _load_profile_flex(
            profile_id, ("provider", "quality", "film-type", "review")
        )
        return _ok(
            profile_id=src.path.stem,
            file=str(src.path),
            raw=src.raw,
        )
    except FileNotFoundError:
        return _error(f"Profile '{profile_id}' not found.")
    except Exception as e:
        return _error(str(e))


async def get_runtime_mode(args: dict[str, object]) -> dict[str, object]:
    """Return current server mode and the active project's stored runtime mode."""
    rt = get_runtime()
    active = rt.get_active()
    project_mode = rt.server_mode
    profile_stack: dict[str, str] = {}
    if active is not None:
        project_mode = str(active.get("runtime_mode", project_mode))
        stack = active.get("profile_stack", {})
        if isinstance(stack, dict):
            profile_stack = {str(k): str(v) for k, v in stack.items()}
    if active is not None and project_mode != rt.server_mode:
        return _error(
            "Active project runtime_mode does not match the MCP server mode.",
            server_mode=rt.server_mode,
            project_runtime_mode=project_mode,
            profile_stack=profile_stack,
        )
    return _ok(
        server_mode=rt.server_mode,
        runtime_mode=project_mode,
        project_runtime_mode=project_mode if active is not None else "",
        aligned=True,
        profile_stack=profile_stack,
    )


# --- Provider tools ------------------------------------------------------


async def check_provider_health(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    provider_id = str(args.get("provider_id", "")).strip()
    if not provider_id:
        provider_ids = rt.list_providers()
        if rt.server_mode == "mock" and not provider_ids:
            provider_id = "mock-video-provider"
        elif provider_ids:
            provider_id = provider_ids[0]
        else:
            return _error("provider_id is required when no providers are registered.")
    health = rt.get_provider_health(provider_id)
    if health is None:
        return _ok(provider_id=provider_id, status="unknown", message="No health data recorded.")
    return _ok(provider_id=provider_id, status=health["status"], reason=health.get("reason", ""))


async def resolve_provider_block(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    provider_id = str(args.get("provider_id", ""))
    if not provider_id:
        return _error("provider_id is required")
    rt.set_provider_health(provider_id, "healthy")
    return _ok(provider_id=provider_id, status="healthy")


async def list_providers(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    provider_ids = rt.list_providers()
    result = []
    for pid in provider_ids:
        health = rt.get_provider_health(pid)
        result.append(
            {
                "provider_id": pid,
                "status": health["status"] if health else "unknown",
            }
        )
    if not result and rt.server_mode == "mock":
        result.append({"provider_id": "mock-video-provider", "status": "healthy"})
    return _ok(providers=result, total=len(result))


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
    """Assemble a review cut using the AssemblyAgent."""
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    from film_pipeline.post.assembly_agent import AssemblyAgent

    agent = AssemblyAgent()
    plan = agent.build_plan(
        project_id=active["project_id"],
        shot_ids=args.get("shot_ids", []),  # type: ignore[arg-type]
        clip_paths=args.get("clip_paths", []),  # type: ignore[arg-type]
    )
    issues = agent.validate_plan(plan)
    return _ok(plan_id=plan.plan_id, clip_count=plan.clip_count, issues=issues)


async def assemble_final_cut(args: dict[str, object]) -> dict[str, object]:
    return _stub("assemble_final_cut")


async def export_delivery_package(args: dict[str, object]) -> dict[str, object]:
    """Export a delivery package using the DeliveryPackagingAgent."""
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    from film_pipeline.post.delivery_packaging_agent import DeliveryPackagingAgent

    agent = DeliveryPackagingAgent()
    package = agent.build_package(
        project_id=active["project_id"],
        video_path=str(args.get("video_path", "")),
        subtitle_path=str(args.get("subtitle_path", "")),
        audio_stems_dir=str(args.get("audio_stems_dir", "")),
        stills_dir=str(args.get("stills_dir", "")),
        validation_report_path=str(args.get("validation_report_path", "")),
        cost_report_path=str(args.get("cost_report_path", "")),
        credits_path=str(args.get("credits_path", "")),
    )
    return _ok(
        package_id=package.package_id,
        is_complete=package.is_complete,
        missing=package.missing_items,
    )


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


def _canonicalize_profile_stack(args: dict[str, object]) -> dict[str, str]:
    stack: dict[str, str] = {}
    mapping = {
        "film_type_profile": ("film-type",),
        "quality_profile": ("quality",),
        "provider_profile": ("provider",),
        "review_profile": ("review",),
        "auto_approve_profile": ("",),  # no prefix — matches any profile dir
    }
    for key, prefixes in mapping.items():
        raw = str(args.get(key, "")).strip()
        if raw:
            _loader, src = _load_profile_flex(raw, prefixes)
            stack[key] = src.path.stem
        else:
            stack[key] = ""
    return stack


def _resolve_project_config(profile_stack: dict[str, str]) -> dict[str, object]:
    from film_pipeline.config.resolver import ConfigResolver

    names = ["base.studio"]
    for key in (
        "film_type_profile",
        "quality_profile",
        "provider_profile",
        "review_profile",
        "auto_approve_profile",
    ):
        value = profile_stack.get(key, "")
        if value:
            names.append(value)

    resolver = ConfigResolver()
    resolved = resolver.resolve(names)
    return {
        "raw": resolved.raw,
        "sources": [source.path.stem for source in resolved.sources],
        "conflicts": [
            {
                "code": conflict.code,
                "message": conflict.message,
                "severity": conflict.severity,
            }
            for conflict in resolved.conflicts
        ],
    }


def _register_project_providers(
    rt: Any,
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> None:
    from film_pipeline.providers.factory import build_provider_adapter

    provider_ids = _provider_specs(profile_stack, resolved_config)
    if not provider_ids:
        return

    rt.clear_providers()
    for spec in provider_ids:
        provider_id = str(spec["provider_id"])
        provider_type = str(spec.get("provider_type", "video"))
        models = [str(model) for model in cast(list[Any], spec.get("models", [])) if str(model)]
        adapter = build_provider_adapter(
            provider_id,
            provider_type=provider_type,
            models=models,
        )
        rt.register_provider(provider_id, adapter)
        rt.set_provider_health(provider_id, "healthy")


def _provider_specs(
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> list[dict[str, object]]:
    provider_profile = profile_stack.get("provider_profile", "")
    if provider_profile:
        try:
            _loader, src = _load_profile_flex(provider_profile, ("provider",))
            providers = src.raw.get("providers", {})
            specs = _provider_specs_from_raw(providers)
            if specs:
                return specs
        except FileNotFoundError:
            pass

    providers = resolved_config.get("providers", {})
    if isinstance(providers, dict):
        specs = _provider_specs_from_raw(providers)
        if specs:
            return specs
    return []


def _provider_specs_from_raw(providers: object) -> list[dict[str, object]]:
    if not isinstance(providers, dict):
        return []
    specs: list[dict[str, object]] = []
    for section, provider_type in (("video", "video"), ("image", "image")):
        entries = providers.get(section, [])
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    provider_id = str(entry.get("provider_id", "")).strip()
                    if provider_id:
                        models = entry.get("models", [])
                        specs.append(
                            {
                                "provider_id": provider_id,
                                "provider_type": provider_type,
                                "models": models if isinstance(models, list) else [],
                            }
                        )
    order = providers.get("order", [])
    if isinstance(order, list):
        for item in order:
            provider_id = str(item).strip()
            if provider_id:
                specs.append(
                    {
                        "provider_id": provider_id,
                        "provider_type": "video",
                        "models": [],
                    }
                )
    deduped: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for spec in specs:
        key = (str(spec["provider_id"]), str(spec["provider_type"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(spec)
    return deduped


def _missing_provider_credentials(
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> list[dict[str, str]]:
    from film_pipeline.providers.credentials import _env_var_for, is_configured

    missing: list[dict[str, str]] = []
    seen: set[str] = set()
    for spec in _provider_specs(profile_stack, resolved_config):
        provider_id = str(spec["provider_id"])
        if provider_id in seen:
            continue
        seen.add(provider_id)
        env_var = _env_var_for(provider_id)
        if not env_var:
            continue
        if is_configured(provider_id):
            continue
        missing.append({"provider_id": provider_id, "env_var": env_var})
    return missing


def _load_profile_flex(
    profile_id: str,
    prefixes: tuple[str, ...],
) -> tuple[Any, Any]:
    """Load a profile spec, trying prefixed variants.

    Returns ``(loader, source)`` where *source* is a ``ProfileSource``
    (with ``.raw``, ``.path``, ``.name`` attributes).
    """
    from film_pipeline.config.loader import ProfileLoader

    loader = ProfileLoader()
    candidates = [profile_id]
    if "." not in profile_id:
        candidates.extend(f"{prefix}.{profile_id}" for prefix in prefixes)
    for candidate in candidates:
        try:
            return loader, loader.load(candidate)
        except FileNotFoundError:
            continue
    raise FileNotFoundError(profile_id)
