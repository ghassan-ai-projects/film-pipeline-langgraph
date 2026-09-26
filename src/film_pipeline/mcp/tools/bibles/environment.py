"""Environment bible generation tool."""

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
    _constitution_theme,
    _constitution_visual_language,
    _load_artifact_if_present,
    _load_script_text,
    _register_active_artifact_ref,
    _save_visual_dev_candidate,
)


def _environment_prompt_mission(environment_name: str, environment_id: str) -> str:
    """Role and core-task section of the EnvironmentBible prompt."""
    return f"""# Role
You are an environment design specialist. Given a script and film constitution,
produce a detailed EnvironmentBible for a single location.

# Core Task
Create an EnvironmentBible for environment '{environment_name}' (id: {environment_id}).

"""


def _environment_prompt_sources(theme_text: str, constitution_text: str, script_text: str) -> str:
    """Theme, visual language, and script context section of the prompt."""
    return f"""# Context
Film Theme: {theme_text}
Visual Language: {constitution_text}

Script:
{script_text[:8000]}

"""


def _environment_prompt_constraints() -> str:
    """Quality-bar constraints section of the prompt."""
    return """# Constraints
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

"""


def _environment_prompt_json_contract(
    environment_id: str, environment_name: str, project_id: str
) -> str:
    """Output-format section of the prompt with the JSON skeleton."""
    return f"""# Output Format
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


def _environment_prompt(
    environment_id: str,
    environment_name: str,
    project_id: str,
    theme_text: str,
    constitution_text: str,
    script_text: str,
) -> str:
    """Assemble the full EnvironmentBible prompt for one location."""
    return (
        _environment_prompt_mission(environment_name, environment_id)
        + _environment_prompt_sources(theme_text, constitution_text, script_text)
        + _environment_prompt_constraints()
        + _environment_prompt_json_contract(environment_id, environment_name, project_id)
    )


def _environment_mock_payload(
    environment_id: str, environment_name: str, project_id: str
) -> dict[str, Any]:
    """Minimal valid EnvironmentBible response for mock mode."""
    return {
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


def _request_environment_bible_output(
    rt: Any, prompt: str, environment_id: str, environment_name: str, project_id: str
) -> dict[str, Any]:
    """Obtain EnvironmentBible JSON from the model adapter or mock fallback."""
    return _chat_json_or_mock(
        rt, prompt, _environment_mock_payload(environment_id, environment_name, project_id)
    )


def _execute_environment_bible_agent(model_output: dict[str, Any]) -> dict[str, Any] | None:
    """Run EnvironmentBibleAgent over the model output; None signals invalid output."""
    from film_pipeline.agents.impl.environment_bible_agent import EnvironmentBibleAgent
    from film_pipeline.schemas.base import AgentFamily, AgentRole
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
    result = agent.execute(model_output)
    if not agent.validate(result):
        return None
    return result


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

    prompt = _environment_prompt(
        environment_id,
        environment_name,
        project_id,
        _constitution_theme(constitution),
        _constitution_visual_language(constitution),
        script_text,
    )

    try:
        model_output = _request_environment_bible_output(
            rt, prompt, environment_id, environment_name, project_id
        )
        result = _execute_environment_bible_agent(model_output)
        if result is None:
            return _error("EnvironmentBible agent produced invalid output.")
        return _deliver_environment_bible(
            rt, active, store, project_id, environment_id, result["environment_bible"]
        )

    except Exception as exc:
        return _error(f"EnvironmentBible generation failed: {exc}")
