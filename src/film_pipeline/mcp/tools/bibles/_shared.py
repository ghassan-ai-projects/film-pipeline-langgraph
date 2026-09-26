"""Shared helpers for bible generation tools."""

from __future__ import annotations

from typing import Any, cast

from ..helpers import _latest_artifact_version, _services


def _dialogue_line(dialogue: object) -> str | None:
    """Format one dialogue entry as 'character: line'; None for non-mappings."""
    if not isinstance(dialogue, dict):
        return None
    char = dialogue.get("character_id", dialogue.get("character", ""))
    line = dialogue.get("line", dialogue.get("text", ""))
    return f"{char}: {line}"


def _scene_lines(scene: object) -> list[str]:
    """Collect heading, action, and dialogue lines from one scene."""
    if not isinstance(scene, dict):
        return []
    lines: list[str] = []
    heading = scene.get("heading", scene.get("scene_heading", ""))
    if heading:
        lines.append(str(heading))
    for action in cast(list[Any], scene.get("action_lines", scene.get("actions", []))):
        lines.append(str(action))
    for dialogue in cast(list[Any], scene.get("dialogue_lines", scene.get("dialogue", []))):
        line = _dialogue_line(dialogue)
        if line is not None:
            lines.append(line)
    return lines


def _scenes_text(scenes: object) -> str | None:
    """Join all scene lines; None when scenes is not a list."""
    if not isinstance(scenes, list):
        return None
    lines: list[str] = []
    for scene in scenes:
        lines.extend(_scene_lines(scene))
    return "\n".join(lines)


def _extract_script_text(script_data: object | None) -> str:
    """Extract readable text from the Script artifact."""
    if not isinstance(script_data, dict):
        return "" if script_data is None else str(script_data)
    joined = _scenes_text(script_data.get("scenes", script_data.get("content", [])))
    if joined is None:
        return str(script_data)
    return joined


def _load_versioned_artifact(store: Any, project_id: str, phase: str, artifact_id: str) -> Any:
    """Load the latest version of an artifact from its creation phase."""
    from film_pipeline.schemas.base import FilmPhase

    version = store.latest_version(project_id, phase, artifact_id)
    return store.load(project_id, FilmPhase(phase), artifact_id, max(1, version))


def _load_artifact_if_present(store: Any, project_id: str, phase: str, artifact_id: str) -> Any:
    """Load the latest version of an artifact; None when missing or unreadable."""
    try:
        return _load_versioned_artifact(store, project_id, phase, artifact_id)
    except (FileNotFoundError, ValueError):
        return None


def _load_script_text(store: Any, project_id: str) -> str | None:
    """Load the Script artifact and flatten it; None when unavailable."""
    try:
        script_data = _load_versioned_artifact(store, project_id, "script", "script")
        return _extract_script_text(script_data)
    except (FileNotFoundError, ValueError):
        return None


def _constitution_theme(constitution: Any) -> str:
    """Theme text from the FilmConstitution mapping, if shaped as one."""
    return str(constitution.get("theme", "")) if isinstance(constitution, dict) else ""


def _constitution_visual_language(constitution: Any) -> str:
    """Visual-language text from the FilmConstitution mapping, if shaped as one."""
    return str(constitution.get("visual_language", "")) if isinstance(constitution, dict) else ""


def _constitution_tone(constitution: Any) -> str:
    """Tone text from the FilmConstitution mapping, if shaped as one."""
    return str(constitution.get("tone", "")) if isinstance(constitution, dict) else ""


def _constitution_camera_philosophy(constitution: Any) -> str:
    """Camera-philosophy text from the FilmConstitution mapping, if shaped as one."""
    return str(constitution.get("camera_philosophy", "")) if isinstance(constitution, dict) else ""


def _run_bible_agent(
    rt: Any,
    agent_id: str,
    task: str,
    context_vars: dict[str, str],
) -> dict[str, Any]:
    """Produce one bible by running its roster agent through the shared path.

    This is the MCP counterpart of ``orchestration.nodes._agent``: the contract
    comes from the roster, the prompt from the dedicated template registry, the
    model call and its retry ladder from ``PromptRunner``, the mock from
    ``studio.mock_responses``, and the parse from the agent's own ``execute()``.

    The tool layer previously assembled prompts by hand and called
    ``model_adapter.chat`` directly, which was a second agent lifecycle: the
    model id was resolved through a method that did not exist, and the reply was
    tested with ``isinstance(raw, dict)`` against a ``-> str`` return, so the
    real-model path both raised and could never have produced a bible.

    Raises:
        KeyError: the agent is not on the roster or has no dedicated template.
        ValueError: the agent rejected the model output.
    """
    from film_pipeline.agents.prompt_templates.registry import get_registry
    from film_pipeline.agents.registry import get_agent_class

    services = _services(rt)
    registry = services.agent_registry
    contract = registry.lookup_by_id(agent_id) if registry is not None else None
    if contract is None:
        raise KeyError(f"Agent '{agent_id}' is not registered on the roster.")

    impl_class = get_agent_class(agent_id)
    if impl_class is None:
        raise KeyError(f"Agent '{agent_id}' has no implementation class.")

    runner = services.prompt_runner
    project_id = str(context_vars.get("project_id", ""))
    kb = services.kb_for(
        project_id=project_id,
        phase="visual_dev",
        agent_id=agent_id,
        task=task,
    )
    template = get_registry().get_required(agent_id)
    model_output, _, _ = runner.run_from_template(
        template,
        kb,
        task,
        model_profile=contract.default_model_profile,
        context_vars=context_vars,
        agent_id=agent_id,
    )

    agent = impl_class(contract)
    result = agent.execute(model_output)
    if not agent.validate(result):
        raise ValueError(f"Agent '{agent_id}' produced invalid output.")
    return result


def _save_visual_dev_candidate(
    store: Any,
    project_id: str,
    artifact_id: str,
    artifact_type: Any,
    created_by: str,
    bible: Any,
) -> str:
    """Persist a bible as the next CANDIDATE version in visual_dev."""
    from datetime import UTC, datetime

    from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef
    from film_pipeline.schemas.base import ArtifactStatus, FilmPhase

    next_version = (
        _latest_artifact_version(store, project_id, FilmPhase("visual_dev"), artifact_id) + 1
    )
    meta = ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        project_id=project_id,
        phase=FilmPhase("visual_dev"),
        version=next_version,
        status=ArtifactStatus.CANDIDATE,
        parents=[],
        created_by=created_by,
        created_at=datetime.now(UTC),
    )
    ref: ArtifactRef = store.save(bible, meta)
    return ref.to_string()


def _register_active_artifact_ref(
    rt: Any, active: dict[str, Any], project_id: str, state_key: str, ref: object
) -> None:
    """Record an artifact reference on the active project and persist state."""
    active[state_key] = ref
    active.setdefault("artifact_refs", []).append(ref)
    rt.projects[project_id] = active
    rt._persist_project_state(project_id)
