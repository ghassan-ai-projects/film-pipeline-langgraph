"""Style bible generation tool."""

from __future__ import annotations

from typing import Any

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import (
    _error,
    _ok,
    _services,
    require_project_state,
)
from ._shared import (
    InvalidBibleOutput,
    _constitution_tone,
    _constitution_visual_language,
    _load_artifact_if_present,
    _register_active_artifact_ref,
    _run_bible_agent,
    _save_visual_dev_candidate,
)

_AGENT_ID = "style-bible-agent"


def _style_palette_hint(store: Any, project_id: str) -> str:
    """Best-effort palette hint from an existing EnvironmentBible."""
    env_bible = _load_artifact_if_present(store, project_id, "visual_dev", "environment_bible")
    if not isinstance(env_bible, dict):
        return ""
    return ", ".join(str(c) for c in env_bible.get("color_palette", [])[:6])


def _deliver_style_bible(
    rt: Any, active: dict[str, Any], store: Any, project_id: str, bible: Any
) -> dict[str, object]:
    """Persist the bible, publish its ref on the active project, and respond."""
    from film_pipeline.schemas.base import ArtifactType

    ref = _save_visual_dev_candidate(
        store,
        project_id,
        "style_bible",
        ArtifactType.STYLE_BIBLE,
        "mcp.generate_style_bible",
        bible,
    )
    _register_active_artifact_ref(rt, active, project_id, "style_bible_ref", ref)
    return _ok(style_bible_ref=ref, palette=bible.color_palette, mood=bible.visual_mood)


async def generate_style_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate a StyleBible from FilmConstitution + EnvironmentBible palettes."""
    rt = tools_pkg.get_runtime()
    active = require_project_state(args)
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    constitution = _load_artifact_if_present(store, project_id, "constitution", "film_constitution")
    if constitution is None:
        return _error("FilmConstitution not found.")

    try:
        result = _run_bible_agent(
            rt,
            _AGENT_ID,
            "Define the film's visual style.",
            {
                "visual_language": _constitution_visual_language(constitution),
                "tone": _constitution_tone(constitution),
                "palette_hint": _style_palette_hint(store, project_id),
                "project_id": project_id,
            },
        )
        return _deliver_style_bible(rt, active, store, project_id, result["style_bible"])
    except InvalidBibleOutput:
        return _error("StyleBible agent produced invalid output.")
    except Exception as exc:
        return _error(f"StyleBible generation failed: {exc}")
