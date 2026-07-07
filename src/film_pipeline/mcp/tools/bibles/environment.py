"""Environment bible generation tool."""

from __future__ import annotations

from typing import Any

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import _error, _latest_artifact_version, _ok, _services
from ._shared import _extract_script_text


async def generate_environment_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate an EnvironmentBible from Script + FilmConstitution.

    Produces a locked environment description (locked_prompt_block, fingerprint,
    zones, viewpoints, lighting states, color palette) used by
    generate_reference_images for structured prompt construction.
    """
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")

    project_id = str(active["project_id"])
    environment_id = str(args.get("environment_id", "")).strip()
    if not environment_id:
        return _error("environment_id is required.")
    environment_name = str(args.get("environment_name", environment_id)).strip()

    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import FilmPhase

        script_data = store.load(project_id, FilmPhase("script"), "script", 1)
        script_text = _extract_script_text(script_data)
    except (FileNotFoundError, ValueError):
        return _error("Script artifact not found. Run script phase first.")

    try:
        constitution = store.load(project_id, FilmPhase("constitution"), "film_constitution", 1)
    except (FileNotFoundError, ValueError):
        return _error("FilmConstitution not found. Run constitution phase first.")

    constitution_text = (
        str(constitution.get("visual_language", "")) if isinstance(constitution, dict) else ""
    )
    theme_text = str(constitution.get("theme", "")) if isinstance(constitution, dict) else ""

    prompt = f"""# Role
You are an environment design specialist. Given a script and film constitution,
produce a detailed EnvironmentBible for a single location.

# Core Task
Create an EnvironmentBible for environment '{environment_name}' (id: {environment_id}).

# Context
Film Theme: {theme_text}
Visual Language: {constitution_text}

Script:
{script_text[:8000]}

# Constraints
- locked_prompt_block must be a one-paragraph description of the environment
  injected verbatim into every prompt. Specific and durable.
- fingerprint.text must be a compressed invariant block (2-3 sentences) that
  captures the essence of the space.
- zones: sub-areas within the environment, each with allowed viewpoints.
- viewpoints: approved camera positions with lens and framing.
- lighting_states: named, repeatable lighting states (at least 2).
- color_palette: 4-8 hex color codes (e.g. "#1a1a2e") that define the
  environment's color identity.
- must_not_change: 3-5 invariants the agents must never alter.

# Output Format
Return ONLY valid JSON:
{{
  "environment_id": "{environment_id}",
  "project_id": "{project_id}",
  "name": "{environment_name}",
  "locked_prompt_block": "One-paragraph description for prompts",
  "invariants": ["invariant 1", "invariant 2"],
  "zones": [
    {{"zone_id": "main_area", "description": "...", "allowed_viewpoints": ["vp_wide", "vp_close"]}}
  ],
  "viewpoints": [
    {{"viewpoint_id": "vp_wide", "description": "Wide establishing shot",
      "lens": "24mm", "framing": "full room"}}
  ],
  "lighting_states": [
    {{"state_id": "golden_afternoon",
      "description": "Warm afternoon light through windows",
      "shadow_direction": "long, eastward", "color_temperature": "3200K",
      "primary_source": "window"}}
  ],
  "color_palette": ["#1a1a2e", "#e94560", "#0f3460", "#16213e"],
  "fingerprint": {{"text": "Compressed invariant block"}},
  "reference_assets": [],
  "must_not_change": ["invariant 1", "invariant 2"]
}}"""

    try:
        from film_pipeline.agents.impl.environment_bible_agent import EnvironmentBibleAgent
        from film_pipeline.schemas._base import AgentFamily, AgentRole
        from film_pipeline.schemas.handoff import AgentRegistration

        agent = EnvironmentBibleAgent(
            AgentRegistration(
                agent_id="environment-bible-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["environment_design"],
                input_artifacts=["script", "film_constitution"],
                output_artifacts=["environment_bible"],
            )
        )

        runner = _services(rt).prompt_runner
        model_output: dict[str, Any]
        if runner.model_adapter is not None:
            raw = runner.model_adapter.chat(
                prompt, model=runner.model_router.resolve("creative_writer")
            )
            model_output = raw if isinstance(raw, dict) else {}
        else:
            model_output = {
                "environment_id": environment_id,
                "project_id": project_id,
                "name": environment_name,
                "locked_prompt_block": f"A {environment_name} — generated in mock mode.",
                "invariants": [],
                "zones": [],
                "viewpoints": [],
                "lighting_states": [],
                "color_palette": ["#1a1a2e", "#e94560"],
                "fingerprint": {"text": f"The {environment_name} — mock mode."},
                "reference_assets": [],
                "must_not_change": ["locked_prompt_block"],
            }

        result = agent.execute(model_output)
        if not agent.validate(result):
            return _error("EnvironmentBible agent produced invalid output.")

        bible = result["environment_bible"]

        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType
        from film_pipeline.schemas.artifact import ArtifactMetadata

        next_version = (
            _latest_artifact_version(
                store, project_id, FilmPhase("visual_dev"), "environment_bible"
            )
            + 1
        )
        meta = ArtifactMetadata(
            artifact_id="environment_bible",
            artifact_type=ArtifactType.ENVIRONMENT_BIBLE,
            project_id=project_id,
            phase=FilmPhase("visual_dev"),
            version=next_version,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_environment_bible",
            created_at=datetime.now(UTC),
        )
        ref = store.save(bible, meta)

        active["environment_bible_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(
            environment_bible_ref=ref,
            environment_id=environment_id,
            locked_prompt_block=bible.locked_prompt_block,
            palette=bible.color_palette,
        )

    except Exception as exc:
        return _error(f"EnvironmentBible generation failed: {exc}")
