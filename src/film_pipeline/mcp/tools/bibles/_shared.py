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
    from film_pipeline.schemas._base import FilmPhase

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


def _chat_json_or_mock(rt: Any, prompt: str, mock_payload: dict[str, Any]) -> dict[str, Any]:
    """Chat reply parsed as a mapping; mock_payload when no model adapter is configured."""
    runner = _services(rt).prompt_runner
    if runner.model_adapter is None:
        return mock_payload
    raw = runner.model_adapter.chat(prompt, model=runner.model_router.resolve("creative_writer"))
    return raw if isinstance(raw, dict) else {}


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

    from film_pipeline.schemas._base import ArtifactStatus, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef

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
