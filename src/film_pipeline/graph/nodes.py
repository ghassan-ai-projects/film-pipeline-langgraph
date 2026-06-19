"""Graph node definitions — one per phase.

Spine phases (intake, constitution, development, script) invoke real agents
and persist artifacts. Remaining phases are flag-only pending fan-out.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from film_pipeline.graph.services import SERVICES_KEY, GraphServices


def _get_services(state: dict[str, Any]) -> GraphServices | None:
    return state.get(SERVICES_KEY)


def _run_agent(
    state: dict[str, Any],
    agent_id: str,
    phase: str,
    task: str,
) -> dict[str, Any]:
    """Run an agent through the full lifecycle: prepare → prompt → model → execute.

    Returns the agent's result dict, or a fallback if services aren't available.
    """
    services = _get_services(state)
    if services is None:
        return {"status": "no_services", "agent": agent_id}

    registry = services.agent_registry
    contract = registry.lookup_by_id(agent_id) if registry else None
    if contract is None:
        return {"status": "agent_not_found", "agent": agent_id}

    kb = services.kb_for(
        project_id=str(state.get("project_id", "")),
        phase=phase,
        agent_id=agent_id,
        task=task,
    )

    # Build prompt, call model, execute agent
    model_output = services.prompt_runner.run(contract, kb, task)

    # The agent instance parses and validates
    from film_pipeline.agents.base import BaseAgent
    from film_pipeline.agents.impl.constitution_agent import ConstitutionAgent
    from film_pipeline.agents.impl.development_agent import DevelopmentAgent
    from film_pipeline.agents.impl.intake_agent import IntakeAgent
    from film_pipeline.agents.impl.screenwriter_agent import ScreenwriterAgent

    agent_map: dict[str, type[BaseAgent]] = {
        "intake-classifier-agent": IntakeAgent,
        "film-constitution-agent": ConstitutionAgent,
        "treatment-agent": DevelopmentAgent,
        "screenwriter-agent": ScreenwriterAgent,
    }
    agent_cls = agent_map.get(agent_id)
    if agent_cls is None:
        return {"status": "no_impl", "agent": agent_id, "model_output": model_output}

    instance: BaseAgent = agent_cls(contract)
    return instance.execute(model_output)


def _save_artifact(
    state: dict[str, Any],
    artifact: Any,
    artifact_id: str,
    phase: str,
) -> str | None:
    """Persist an artifact via ArtifactStore and return its ref string."""
    services = _get_services(state)
    if services is None:
        return None
    from datetime import UTC, datetime

    from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata

    artifact_type_str = type(artifact).__name__.lower()
    try:
        artifact_type = ArtifactType(artifact_type_str)
    except ValueError:
        artifact_type = ArtifactType.SCRIPT  # fallback for unknown types

    meta = ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        project_id=str(state.get("project_id", "")),
        phase=FilmPhase(phase),
        version=1,
        status=ArtifactStatus.CANDIDATE,
        parents=[],
        created_by="graph_node",
        created_at=datetime.now(UTC),
    )
    services.artifact_store.save(artifact, meta)
    return f"artifact:{artifact_id}:v1"


# ── Intake ───────────────────────────────────────────────────────────────────


def intake_node(state: dict[str, Any]) -> dict[str, Any]:
    """Intake: classify input, infer config, present for approval."""
    new_state = deepcopy(state)
    new_state["current_phase"] = "intake"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "config"

    result = _run_agent(
        new_state,
        agent_id="intake-classifier-agent",
        phase="intake",
        task="Classify the user's film idea and produce a project profile.",
    )
    profile = result.get("profile")
    if profile is not None:
        ref = _save_artifact(new_state, profile, "project_profile", "intake")
        if ref:
            new_state["profile_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    return new_state


# ── Constitution ─────────────────────────────────────────────────────────────


def constitution_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "constitution"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "constitution"

    result = _run_agent(
        new_state,
        agent_id="film-constitution-agent",
        phase="constitution",
        task="Create the film's creative constitution from the project idea.",
    )
    constitution = result.get("constitution")
    if constitution is not None:
        ref = _save_artifact(new_state, constitution, "film_constitution", "constitution")
        if ref:
            new_state["constitution_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    return new_state


# ── Development ──────────────────────────────────────────────────────────────


def development_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "development"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "treatment"

    result = _run_agent(
        new_state,
        agent_id="treatment-agent",
        phase="development",
        task="Write the film treatment and scene breakdown from the constitution.",
    )
    treatment = result.get("treatment")
    scene_list = result.get("scene_list")
    if treatment is not None:
        ref = _save_artifact(new_state, treatment, "treatment", "development")
        if ref:
            new_state["treatment_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)
    if scene_list is not None:
        ref = _save_artifact(new_state, scene_list, "scene_list", "development")
        if ref:
            new_state["scene_list_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    return new_state


# ── Script ───────────────────────────────────────────────────────────────────


def script_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "script"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "script"

    result = _run_agent(
        new_state,
        agent_id="screenwriter-agent",
        phase="script",
        task="Write the full screenplay from the treatment and scene intents.",
    )
    story_bible = result.get("story_bible")
    script = result.get("script")
    if story_bible is not None:
        ref = _save_artifact(new_state, story_bible, "story_bible", "script")
        if ref:
            new_state["story_bible_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)
    if script is not None:
        ref = _save_artifact(new_state, script, "script", "script")
        if ref:
            new_state["script_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    return new_state


# ── Remaining phases (flag-only, pending agent implementations) ──────────────


def visual_dev_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "visual_dev"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "visual_bible"
    return new_state


def shot_bible_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "shot_bible"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "shot_bible"
    return new_state


def gen_planning_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "gen_planning"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "generation_spend"
    return new_state


def generation_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "generation"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "generation_batch"
    return new_state


def qc_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "qc"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "qc"
    return new_state


def post_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "post"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "assembly"
    return new_state


def delivery_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "delivery"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "final_delivery"
    return new_state


def approve_phase_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["approved"] = True
    new_state["human_approval_required"] = False
    return new_state


def request_revision_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["approved"] = False
    new_state["human_approval_required"] = False
    issues = new_state.get("issues", [])
    new_state["issues"] = [
        *issues,
        {
            "issue_id": "rev",
            "severity": "warning",
            "code": "REVISION_REQUESTED",
            "message": "Human requested revision.",
        },
    ]
    return new_state
