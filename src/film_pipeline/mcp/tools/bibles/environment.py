"""Environment bible generation tool."""

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
    _constitution_visual_language,
    _load_artifact_if_present,
    _load_script_text,
    _run_bible_agent,
    _save_visual_dev_candidate,
)

_AGENT_ID = "environment-bible-agent"


def _deliver_environment_bible(
    rt: Any,
    active: dict[str, Any],
    store: Any,
    project_id: str,
    environment_id: str,
    bible: Any,
) -> dict[str, object]:
    """Persist the bible, publish its ref on the active project, and respond."""
    from film_pipeline.schemas.base import ArtifactType

    ref = _save_visual_dev_candidate(
        store,
        project_id,
        "environment_bible",
        ArtifactType.ENVIRONMENT_BIBLE,
        "mcp.generate_environment_bible",
        bible,
    )
    _register_active_artifact_ref(rt, active, project_id, "environment_bible_ref", ref)
    return _ok(
        environment_bible_ref=ref,
        environment_id=environment_id,
        locked_prompt_block=bible.locked_prompt_block,
        palette=bible.color_palette,
    )


async def generate_environment_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate an EnvironmentBible from Script + FilmConstitution.

    Produces a locked environment description (locked_prompt_block, fingerprint,
    zones, viewpoints, lighting states, color palette) used by
    generate_reference_images for structured prompt construction.
    """
    rt = tools_pkg.get_runtime()
    active = require_project_state(args)

    project_id = str(active["project_id"])
    environment_id = str(args.get("environment_id", "")).strip()
    if not environment_id:
        return _error("environment_id is required.")
    environment_name = str(args.get("environment_name", environment_id)).strip()

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
            f"Design the environment '{environment_name}'.",
            {
                "environment_id": environment_id,
                "environment_name": environment_name,
                "theme": _constitution_theme(constitution),
                "visual_language": _constitution_visual_language(constitution),
                "script_content": script_text,
                "project_id": project_id,
            },
            subject_key="environment_id",
            subject_id=environment_id,
        )
        return _deliver_environment_bible(
            rt, active, store, project_id, environment_id, result["environment_bible"]
        )
    except InvalidBibleOutput:
        return _error("EnvironmentBible agent produced invalid output.")
    except Exception as exc:
        return _error(f"EnvironmentBible generation failed: {exc}")
