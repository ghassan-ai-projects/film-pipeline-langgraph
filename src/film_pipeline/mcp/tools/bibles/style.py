"""Style bible generation tool."""

from __future__ import annotations

from typing import Any

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import _error, _ok, _services
from ._shared import (
    _chat_json_or_mock,
    _constitution_tone,
    _constitution_visual_language,
    _load_artifact_if_present,
    _register_active_artifact_ref,
    _save_visual_dev_candidate,
)


def _style_palette_hint(store: Any, project_id: str) -> str:
    """Best-effort palette hint from an existing EnvironmentBible."""
    env_bible = _load_artifact_if_present(store, project_id, "visual_dev", "environment_bible")
    if not isinstance(env_bible, dict):
        return ""
    return ", ".join(str(c) for c in env_bible.get("color_palette", [])[:6])


def _style_prompt(visual_language: str, tone: str, palette_hint: str) -> str:
    """Assemble the StyleBible prompt."""
    return (
        f"Create a StyleBible. Visual language: {visual_language}. "
        f"Tone: {tone}. Palette hints: {palette_hint}. "
        "Return JSON with 'color_palette' (4-8 hex codes), "
        "'texture', 'grain', 'visual_mood', 'reference_stills', "
        "and 'must_not_change'."
    )


def _style_mock_payload(project_id: str) -> dict[str, Any]:
    """Minimal valid StyleBible response for mock mode."""
    return {
        "project_id": project_id,
        "color_palette": ["#1a1a2e", "#e94560", "#0f3460", "#16213e"],
        "texture": "gritty, painterly",
        "grain": "subtle 16mm grain",
        "visual_mood": "melancholic, high-contrast",
        "reference_stills": [],
        "must_not_change": ["color_palette"],
    }


def _request_style_bible_output(rt: Any, prompt: str, project_id: str) -> dict[str, Any]:
    """Obtain StyleBible JSON from the model adapter or mock fallback."""
    return _chat_json_or_mock(rt, prompt, _style_mock_payload(project_id))


def _execute_style_bible_agent(model_output: dict[str, Any]) -> dict[str, Any] | None:
    """Run StyleBibleAgent over the model output; None signals invalid output."""
    from film_pipeline.agents.impl.style_bible_agent import StyleBibleAgent
    from film_pipeline.schemas._base import AgentFamily, AgentRole
    from film_pipeline.schemas.handoff import AgentRegistration

    agent = StyleBibleAgent(
        AgentRegistration(
            agent_id="style-bible-agent",
            family=AgentFamily.DEVELOPMENT,
            role=AgentRole.CREATOR,
            capabilities=["style_definition"],
            input_artifacts=["film_constitution", "environment_bible"],
            output_artifacts=["style_bible"],
        )
    )
    result = agent.execute(model_output)
    if not agent.validate(result):
        return None
    return result


def _deliver_style_bible(
    rt: Any, active: dict[str, Any], store: Any, project_id: str, bible: Any
) -> dict[str, object]:
    """Persist the bible, publish its ref on the active project, and respond."""
    from film_pipeline.schemas._base import ArtifactType

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
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    constitution = _load_artifact_if_present(store, project_id, "constitution", "film_constitution")
    if constitution is None:
        return _error("FilmConstitution not found.")

    prompt = _style_prompt(
        _constitution_visual_language(constitution),
        _constitution_tone(constitution),
        _style_palette_hint(store, project_id),
    )

    try:
        model_output = _request_style_bible_output(rt, prompt, project_id)
        result = _execute_style_bible_agent(model_output)
        if result is None:
            return _error("StyleBible agent produced invalid output.")
        return _deliver_style_bible(rt, active, store, project_id, result["style_bible"])
    except Exception as exc:
        return _error(f"StyleBible generation failed: {exc}")
