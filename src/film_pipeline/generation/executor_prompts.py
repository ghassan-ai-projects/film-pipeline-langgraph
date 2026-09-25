"""Prompt resolution for generation rows.

Picks the best prompt text for a shot: a rendered prompt from the
gen_planning prompt package when ``prompt_ref`` names one, then a
structured prompt assembled from the shot matrix row, then a plain
fallback so submission never blocks.
"""

from __future__ import annotations

from typing import Any

from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.schemas.base import FilmPhase


def load_latest_artifact(
    store: ArtifactStore, project_id: str, phase: FilmPhase, artifact_id: str
) -> dict[str, Any] | None:
    """Load the newest version of an artifact body, or None when absent."""
    latest = store.latest_version(project_id, phase.value, artifact_id)
    if latest < 1:
        return None
    try:
        return store.load(project_id, phase, artifact_id, latest)
    except (FileNotFoundError, ValueError):
        return None


def resolve_shot_prompt(
    store: ArtifactStore,
    project_id: str,
    shot_id: str,
    shot_row: dict[str, Any],
    prompt_ref: str = "",
) -> str:
    """Resolve the best prompt text for a shot.

    Prefers a rendered prompt from the gen_planning prompt artifact when
    ``prompt_ref`` names one, then a structured prompt from the shot
    matrix row, then a plain fallback so submission never blocks.
    """
    rendered = _rendered_prompt(store, project_id, shot_id, prompt_ref)
    if rendered:
        return rendered
    if shot_row:
        structured = _structured_prompt(store, project_id, shot_row)
        if structured:
            return structured
    return f"Cinematic shot {shot_id} for project {project_id}."


def _rendered_prompt(store: ArtifactStore, project_id: str, shot_id: str, prompt_ref: str) -> str:
    """Rendered prompt for *shot_id* from the package *prompt_ref* names."""
    if not prompt_ref:
        return ""
    artifact_id = _referenced_artifact_id(prompt_ref)
    for phase in (FilmPhase.GEN_PLANNING, FilmPhase.SHOT_BIBLE):
        package = load_latest_artifact(store, project_id, phase, artifact_id)
        rendered = _entry_prompt_for_shot(package, shot_id)
        if rendered:
            return rendered
    return ""


def _referenced_artifact_id(prompt_ref: str) -> str:
    """Strip the ``namespace:`` prefix from a prompt reference."""
    return prompt_ref.split(":")[1] if ":" in prompt_ref else prompt_ref


def _entry_prompt_for_shot(package: object, shot_id: str) -> str:
    """Rendered prompt of the first package entry for *shot_id*, if any."""
    if not isinstance(package, dict):
        return ""
    for entry in package.get("entries", []) or []:
        if isinstance(entry, dict) and str(entry.get("shot_id", "")) == shot_id:
            return str(entry.get("rendered_prompt", "") or "")
    return ""


def _structured_prompt(store: ArtifactStore, project_id: str, shot_row: dict[str, Any]) -> str:
    """Structured prompt assembled from the shot matrix row and bibles."""
    from film_pipeline.generation.prompt_builder import build_structured_prompt

    return build_structured_prompt(
        _prompt_entry_from_shot_row(shot_row),
        character_bible=_character_bible(store, project_id, shot_row),
        constitution=_film_constitution(store, project_id),
    )


def _prompt_entry_from_shot_row(shot_row: dict[str, Any]) -> dict[str, Any]:
    """Map a shot matrix row onto a structured-prompt entry."""
    characters = shot_row.get("characters") or []
    environment = str(shot_row.get("environment", "") or "")
    return {
        "subject_type": "environment" if not characters else "character",
        "subject_id": environment if not characters else str(characters[0]),
        "frame_role": str(shot_row.get("camera_profile", "") or ""),
        "prompt_text": str(shot_row.get("story_function", "") or ""),
        "lighting": str(shot_row.get("lighting_state", "") or ""),
        "notes": str(shot_row.get("environment_state", "") or ""),
    }


def _character_bible(
    store: ArtifactStore, project_id: str, shot_row: dict[str, Any]
) -> dict[str, Any] | None:
    """Latest character bible when the shot casts characters, else None."""
    if not shot_row.get("characters"):
        return None
    bible = load_latest_artifact(store, project_id, FilmPhase.VISUAL_DEV, "character_bible")
    return bible if isinstance(bible, dict) else None


def _film_constitution(store: ArtifactStore, project_id: str) -> dict[str, Any] | None:
    """Latest film constitution artifact, or None when absent."""
    constitution = load_latest_artifact(
        store, project_id, FilmPhase.CONSTITUTION, "film_constitution"
    )
    return constitution if isinstance(constitution, dict) else None
