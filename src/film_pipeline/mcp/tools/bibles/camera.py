"""Camera bible generation tool."""

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
    _constitution_camera_philosophy,
    _load_artifact_if_present,
    _register_active_artifact_ref,
    _run_bible_agent,
    _save_visual_dev_candidate,
)

_AGENT_ID = "camera-bible-agent"


def _deliver_camera_bible(
    rt: Any, active: dict[str, Any], store: Any, project_id: str, bible: Any
) -> dict[str, object]:
    """Persist the bible, publish its ref on the active project, and respond."""
    from film_pipeline.schemas.base import ArtifactType

    ref = _save_visual_dev_candidate(
        store,
        project_id,
        "camera_language_bible",
        ArtifactType.CAMERA_LANGUAGE_BIBLE,
        "mcp.generate_camera_bible",
        bible,
    )
    _register_active_artifact_ref(rt, active, project_id, "camera_bible_ref", ref)
    return _ok(camera_bible_ref=ref, profiles=len(bible.profiles))


async def generate_camera_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate a CameraLanguageBible from FilmConstitution."""
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
            "Design the film's camera language.",
            {
                "camera_philosophy": _constitution_camera_philosophy(constitution),
                "project_id": project_id,
            },
        )
        return _deliver_camera_bible(rt, active, store, project_id, result["camera_bible"])
    except InvalidBibleOutput:
        return _error("CameraBible agent produced invalid output.")
    except Exception as exc:
        return _error(f"CameraBible generation failed: {exc}")
