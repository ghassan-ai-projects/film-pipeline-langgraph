"""Camera bible generation tool."""

from __future__ import annotations

from typing import Any

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import _error, _latest_artifact_version, _ok, _services


async def generate_camera_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate a CameraLanguageBible from FilmConstitution."""
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import FilmPhase

        constitution = store.load(project_id, FilmPhase("constitution"), "film_constitution", 1)
    except (FileNotFoundError, ValueError):
        return _error("FilmConstitution not found.")

    camera_philosophy = (
        str(constitution.get("camera_philosophy", "")) if isinstance(constitution, dict) else ""
    )

    try:
        from film_pipeline.agents.impl.camera_bible_agent import CameraBibleAgent
        from film_pipeline.schemas._base import AgentFamily, AgentRole, ArtifactStatus, ArtifactType
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
        runner = _services(rt).prompt_runner
        model_output: dict[str, Any]
        if runner.model_adapter is not None:
            raw = runner.model_adapter.chat(
                f"Create a CameraLanguageBible for a film with camera philosophy: "
                f"{camera_philosophy}. "
                "Return JSON with 'profiles' array (profile_id, use_case, lens, "
                "framing, movement, depth_of_field, composition_rules, "
                "transition_rules, emotional_meaning) and 'default_profile_id'.",
                model=runner.model_router.resolve("creative_writer"),
            )
            model_output = raw if isinstance(raw, dict) else {}
        else:
            model_output = {
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

        result = agent.execute(model_output)
        if not agent.validate(result):
            return _error("CameraBible agent produced invalid output.")
        bible = result["camera_bible"]

        from datetime import UTC, datetime

        from film_pipeline.schemas.artifact import ArtifactMetadata

        next_version = (
            _latest_artifact_version(
                store, project_id, FilmPhase("visual_dev"), "camera_language_bible"
            )
            + 1
        )
        meta = ArtifactMetadata(
            artifact_id="camera_language_bible",
            artifact_type=ArtifactType.CAMERA_LANGUAGE_BIBLE,
            project_id=project_id,
            phase=FilmPhase("visual_dev"),
            version=next_version,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_camera_bible",
            created_at=datetime.now(UTC),
        )
        ref = store.save(bible, meta)
        active["camera_bible_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(camera_bible_ref=ref, profiles=len(bible.profiles))
    except Exception as exc:
        return _error(f"CameraBible generation failed: {exc}")
