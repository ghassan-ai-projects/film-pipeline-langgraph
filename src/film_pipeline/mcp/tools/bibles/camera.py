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
    _chat_json_or_mock,
    _constitution_camera_philosophy,
    _load_artifact_if_present,
    _register_active_artifact_ref,
    _save_visual_dev_candidate,
)


def _camera_bible_prompt(camera_philosophy: str) -> str:
    """Assemble the CameraLanguageBible prompt."""
    return (
        f"Create a CameraLanguageBible for a film with camera philosophy: "
        f"{camera_philosophy}. "
        "Return JSON with 'profiles' array (profile_id, use_case, lens, "
        "framing, movement, depth_of_field, composition_rules, "
        "transition_rules, emotional_meaning) and 'default_profile_id'."
    )


def _camera_mock_payload(project_id: str) -> dict[str, Any]:
    """Minimal valid CameraLanguageBible response for mock mode."""
    return {
        "project_id": project_id,
        "profiles": [
            {
                "profile_id": "default",
                "use_case": "General shots",
                "lens": "35mm prime",
                "framing": "Rule of thirds",
                "movement": "Static or slow push-in",
                "depth_of_field": "Shallow, f/2.0",
                "composition_rules": ["Rule of thirds"],
                "transition_rules": ["Cut on action"],
                "emotional_meaning": "Observational, intimate",
            }
        ],
        "default_profile_id": "default",
    }


def _request_camera_bible_output(
    rt: Any, project_id: str, camera_philosophy: str
) -> dict[str, Any]:
    """Obtain CameraLanguageBible JSON from the model adapter or mock fallback."""
    return _chat_json_or_mock(
        rt,
        _camera_bible_prompt(camera_philosophy),
        _camera_mock_payload(project_id),
    )


def _execute_camera_bible_agent(model_output: dict[str, Any]) -> dict[str, Any] | None:
    """Run CameraBibleAgent over the model output; None signals invalid output."""
    from film_pipeline.agents.impl.camera_bible_agent import CameraBibleAgent
    from film_pipeline.schemas.base import AgentFamily, AgentRole
    from film_pipeline.schemas.handoff import AgentRegistration

    agent = CameraBibleAgent(
        AgentRegistration(
            agent_id="camera-bible-agent",
            family=AgentFamily.DEVELOPMENT,
            role=AgentRole.CREATOR,
            capabilities=["camera_design"],
            input_artifacts=["film_constitution"],
            output_artifacts=["camera_language_bible"],
        )
    )
    result = agent.execute(model_output)
    if not agent.validate(result):
        return None
    return result


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
        model_output = _request_camera_bible_output(
            rt, project_id, _constitution_camera_philosophy(constitution)
        )
        result = _execute_camera_bible_agent(model_output)
        if result is None:
            return _error("CameraBible agent produced invalid output.")
        return _deliver_camera_bible(rt, active, store, project_id, result["camera_bible"])
    except Exception as exc:
        return _error(f"CameraBible generation failed: {exc}")
