"""Character bible generation tool."""

from __future__ import annotations

from typing import Any

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import (
    _error,
    _ok,
    _register_active_artifact_ref,
    _services,
    require_project_state,
)
from ._shared import (
    InvalidBibleOutput,
    _constitution_theme,
    _load_artifact_if_present,
    _load_script_text,
    _run_bible_agent,
    _save_visual_dev_candidate,
)

_AGENT_ID = "character-bible-agent"


def _deliver_character_bible(
    rt: Any,
    active: dict[str, Any],
    store: Any,
    project_id: str,
    character_id: str,
    bible: Any,
) -> dict[str, object]:
    """Persist the bible, publish its ref on the active project, and respond."""
    from film_pipeline.schemas.base import ArtifactType

    ref = _save_visual_dev_candidate(
        store,
        project_id,
        "character_bible",
        ArtifactType.CHARACTER_BIBLE,
        "mcp.generate_character_bible",
        bible,
    )
    _register_active_artifact_ref(rt, active, project_id, "character_bible_ref", ref)
    return _ok(
        character_bible_ref=ref,
        character_id=character_id,
        identity_block=bible.visual_identity.identity_block,
    )


async def generate_character_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate a CharacterBible from Script + FilmConstitution.

    Produces a locked character description (identity_block, voice, wardrobe,
    emotional arc, relationships) used by generate_reference_images for
    structured prompt construction.
    """
    rt = tools_pkg.get_runtime()
    active = require_project_state(args)

    project_id = str(active["project_id"])
    character_id = str(args.get("character_id", "")).strip()
    if not character_id:
        return _error("character_id is required.")
    character_name = str(args.get("character_name", character_id)).strip()

    store = _services(rt).artifact_store

    script_text = _load_script_text(store, project_id)
    if script_text is None:
        return _error("Script artifact not found. Run script phase first.")

    constitution = _load_artifact_if_present(store, project_id, "constitution", "film_constitution")
    if constitution is None:
        return _error("FilmConstitution not found. Run constitution phase first.")

    try:
        result = _run_bible_agent(
            rt,
            _AGENT_ID,
            f"Write the character bible for {character_name}.",
            {
                "character_id": character_id,
                "character_name": character_name,
                "theme": _constitution_theme(constitution),
                "constitution_content": _constitution_text(constitution),
                "script_content": script_text,
                "project_id": project_id,
            },
            subject_key="character_id",
            subject_id=character_id,
        )
        return _deliver_character_bible(
            rt, active, store, project_id, character_id, result["character_bible"]
        )
    except InvalidBibleOutput:
        return _error("CharacterBible agent produced invalid output.")
    except Exception as exc:
        return _error(f"CharacterBible generation failed: {exc}")


def _constitution_text(constitution: Any) -> str:
    """Flatten the FilmConstitution into the prompt's context block."""
    if isinstance(constitution, dict):
        return "\n".join(f"{k}: {v}" for k, v in constitution.items())
    return str(constitution)
