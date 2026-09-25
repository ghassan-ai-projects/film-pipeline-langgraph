"""Resolve each generation request's prompt text from planning artifacts."""

from __future__ import annotations

from typing import Any

from film_pipeline.graph.nodes._context import (
    _parse_ref,
)
from film_pipeline.graph.services import GraphServices


def _load_artifact_data(
    state: dict[str, Any],
    services: GraphServices,
    ref: str,
) -> Any:
    """Load artifact data by ref from its phase, or ``None`` when absent."""
    if not ref or ":" not in ref:
        return None
    try:
        parsed = _parse_ref(ref)
    except ValueError:
        # Non-artifact refs (e.g. the "prompt:<id>" namespace) don't resolve
        # here; callers fall back to other prompt sources.
        return None
    project_id = str(state.get("project_id", ""))
    if not project_id:
        return None
    from film_pipeline.schemas.base import FilmPhase

    try:
        return services.artifact_store.load(
            project_id, FilmPhase(parsed.phase), parsed.artifact_id, parsed.version
        )
    except (FileNotFoundError, ValueError, KeyError):
        return None


def _load_matrix_rows(
    state: dict[str, Any],
    services: GraphServices,
) -> list[dict[str, Any]]:
    """Load rows from the master film matrix artifact."""
    shot_matrix_ref = str(state.get("shot_matrix_ref", ""))
    if not shot_matrix_ref:
        return []
    data = _load_artifact_data(state, services, shot_matrix_ref)
    if not isinstance(data, dict):
        return []
    rows = data.get("rows", [])
    if isinstance(rows, list):
        return [r if isinstance(r, dict) else r.model_dump() for r in rows]
    return []


def _find_matrix_row(rows: list[dict[str, Any]], shot_id: str) -> dict[str, Any] | None:
    for row in rows:
        if str(row.get("shot_id", "")) == shot_id:
            return row
    return None


def _prompt_entry_from_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map a master-matrix row onto the structured prompt-builder entry shape."""
    characters = row.get("characters") or []
    environment = str(row.get("environment", "") or "")
    subject_type = "environment" if not characters else "character"
    subject_id = environment if not characters else str(characters[0])
    return {
        "subject_type": subject_type,
        "subject_id": subject_id,
        "frame_role": str(row.get("camera_profile", "") or ""),
        "prompt_text": str(row.get("story_function", "") or ""),
        "lighting": str(row.get("lighting_state", "") or ""),
        "notes": str(row.get("environment_state", "") or ""),
    }


def _load_visual_dev_bible(
    services: GraphServices,
    project_id: str,
    bible_id: str,
) -> dict[str, Any] | None:
    """Load the latest visual_dev bible, returning None when absent or malformed."""
    from film_pipeline.schemas.base import FilmPhase

    version = services.artifact_store.latest_version(project_id, "visual_dev", bible_id)
    try:
        data = services.artifact_store.load(
            project_id, FilmPhase("visual_dev"), bible_id, max(1, version)
        )
    except (FileNotFoundError, ValueError, KeyError):
        return None
    return data if isinstance(data, dict) else None


def _build_prompt_from_matrix_row(
    state: dict[str, Any],
    services: GraphServices,
    row: dict[str, Any],
) -> str:
    """Build a structured generation prompt from the shot matrix row."""
    from film_pipeline.generation.prompt_builder import build_structured_prompt

    characters = row.get("characters") or []
    environment = str(row.get("environment", "") or "")

    entry = _prompt_entry_from_row(row)

    constitution_ref = str(state.get("constitution_ref", "") or "")
    constitution = (
        _load_artifact_data(state, services, constitution_ref) if constitution_ref else None
    )
    constitution = constitution if isinstance(constitution, dict) else None

    character_bible: dict[str, Any] | None = None
    project_id = str(state.get("project_id", ""))
    if characters:
        character_bible = _load_visual_dev_bible(services, project_id, "character_bible")
    elif environment:
        # Loaded despite being unconsumed here, matching the historical load path.
        _load_visual_dev_bible(services, project_id, "environment_bible")

    return build_structured_prompt(
        entry,
        character_bible=character_bible,
        constitution=constitution,
    )


def _compose_prompt_from_rctco(rctco: dict[str, Any]) -> str:
    """Compose fallback prompt text from an entry's RCTCO block."""
    parts: list[str] = []
    if rctco.get("r"):
        parts.append(str(rctco["r"]))
    if rctco.get("c1"):
        parts.append(str(rctco["c1"]))
    constraints = rctco.get("c2") or []
    if constraints:
        parts.append("Constraints:")
        parts.extend(f"- {c}" for c in constraints)
    context = rctco.get("t") or {}
    if context:
        parts.append("Context:")
        for key, value in context.items():
            parts.append(f"- {key}: {value}")
    return "\n\n".join(parts)


def _resolve_prompt_for_request(
    state: dict[str, Any],
    services: GraphServices,
    req: dict[str, Any],
    matrix_rows: list[dict[str, Any]],
) -> str:
    """Resolve a generation request's prompt_ref to actual prompt text."""
    prompt_ref = str(req.get("prompt_ref", "") or "")
    shot_id = str(req.get("shot_id", "") or "")

    if prompt_ref and services:
        data = _load_artifact_data(state, services, prompt_ref)
        entries = (data.get("entries") or []) if isinstance(data, dict) else []
        for entry in entries:
            if not isinstance(entry, dict) or str(entry.get("shot_id", "")) != shot_id:
                continue
            rendered = str(entry.get("rendered_prompt", "") or "")
            if rendered:
                return rendered
            rctco = entry.get("rctco")
            if isinstance(rctco, dict):
                return _compose_prompt_from_rctco(rctco)

    row = _find_matrix_row(matrix_rows, shot_id)
    if row is not None:
        return _build_prompt_from_matrix_row(state, services, row)

    return str(req.get("prompt", "") or "")
