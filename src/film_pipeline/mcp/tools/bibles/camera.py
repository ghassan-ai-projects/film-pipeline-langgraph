"""Camera bible generation tool."""

from __future__ import annotations

from typing import Any

from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec
from film_pipeline.schemas.base import ArtifactType

from ..helpers import (
    _error,
    _ok,
    _register_active_artifact_ref,
    _services,
)
from ._shared import (
    InvalidBibleOutput,
    _constitution_camera_philosophy,
    _load_artifact_if_present,
    _run_bible_agent,
    _save_visual_dev_candidate,
)

_AGENT_ID = "camera-bible-agent"


def _deliver_camera_bible(
    rt: Any, active: dict[str, Any], store: Any, project_id: str, bible: Any
) -> dict[str, object]:
    """Persist the bible, publish its ref on the active project, and respond."""

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


async def generate_camera_bible(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Generate a CameraLanguageBible from FilmConstitution."""
    rt = ctx.runtime
    active = ctx.project_state()
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


# ── Tool declaration ─────────────────────────────────────────────────────────
# Declared next to the handler it describes (doc 04 slice 1).


class GenerateCameraBibleArgs(ToolArgs):
    """Arguments for `generate_camera_bible` (none)."""


GENERATE_CAMERA_BIBLE = ToolSpec(
    name="generate_camera_bible",
    group=ToolGroup.GENERATION,
    description="Generate a CameraLanguageBible from the FilmConstitution.",
    args=GenerateCameraBibleArgs,
    handler=generate_camera_bible,
    mutates=True,
    active_project=True,
)
