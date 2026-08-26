"""Camera bible generation tool."""

from __future__ import annotations

from typing import Any

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import _error, _ok, _services
from ._shared import (
    _load_artifact_if_present,
    _register_active_artifact_ref,
    _save_visual_dev_candidate,
)


def _constitution_camera_philosophy(constitution: Any) -> str:
    """Camera-philosophy text from the FilmConstitution mapping, if shaped as one."""
    return str(constitution.get("camera_philosophy", "")) if isinstance(constitution, dict) else ""


def _request_camera_bible_output(
    rt: Any, project_id: str, camera_philosophy: str
) -> dict[str, Any]:
    """Obtain CameraLanguageBible JSON from the model adapter or mock fallback."""
    runner = _services(rt).prompt_runner
    if runner.model_adapter is None:
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
    raw = runner.model_adapter.chat(
        f"Create a CameraLanguageBible for a film with camera philosophy: "
        f"{camera_philosophy}. "
        "Return JSON with 'profiles' array (profile_id, use_case, lens, "
        "framing, movement, depth_of_field, composition_rules, "
        "transition_rules, emotional_meaning) and 'default_profile_id'.",
        model=runner.model_router.resolve("creative_writer"),
    )
    return raw if isinstance(raw, dict) else {}


def _execute_camera_bible_agent(model_output: dict[str, Any]) -> dict[str, Any] | None:
    """Run CameraBibleAgent over the model output; None signals invalid output."""
    from film_pipeline.agents.impl.camera_bible_agent import CameraBibleAgent
    from film_pipeline.schemas._base import AgentFamily, AgentRole
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
    from film_pipeline.schemas._base import ArtifactType

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
    active = rt.get_active()
    if not active:
        return _error("No active project.")
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
