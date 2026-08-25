"""Style bible generation tool."""

from __future__ import annotations

from typing import Any

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import _error, _ok, _services
from ._shared import (
    _load_artifact_if_present,
    _load_versioned_artifact,
    _register_active_artifact_ref,
    _save_visual_dev_candidate,
)


def _style_palette_hint(store: Any, project_id: str) -> str:
    """Best-effort palette hint from an existing EnvironmentBible."""
    palette_hint = ""
    try:
        env_bible = _load_versioned_artifact(store, project_id, "visual_dev", "environment_bible")
        if isinstance(env_bible, dict):
            palette_hint = ", ".join(str(c) for c in env_bible.get("color_palette", [])[:6])
    except (FileNotFoundError, ValueError):
        pass
    return palette_hint


def _style_prompt(visual_language: str, tone: str, palette_hint: str) -> str:
    """Assemble the StyleBible prompt."""
    return (
        f"Create a StyleBible. Visual language: {visual_language}. "
        f"Tone: {tone}. Palette hints: {palette_hint}. "
        "Return JSON with 'color_palette' (4-8 hex codes), "
        "'texture', 'grain', 'visual_mood', 'reference_stills', "
        "and 'must_not_change'."
    )


def _request_style_bible_output(rt: Any, prompt: str, project_id: str) -> dict[str, Any]:
    """Obtain StyleBible JSON from the model adapter or mock fallback."""
    runner = _services(rt).prompt_runner
    if runner.model_adapter is None:
        return {
            "project_id": project_id,
            "color_palette": ["#1a1a2e", "#e94560", "#0f3460", "#16213e"],
            "texture": "gritty, painterly",
            "grain": "subtle 16mm grain",
            "visual_mood": "melancholic, high-contrast",
            "reference_stills": [],
            "must_not_change": ["color_palette"],
        }
    raw = runner.model_adapter.chat(prompt, model=runner.model_router.resolve("creative_writer"))
    return raw if isinstance(raw, dict) else {}


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

    visual_language = (
        str(constitution.get("visual_language", "")) if isinstance(constitution, dict) else ""
    )
    tone = str(constitution.get("tone", "")) if isinstance(constitution, dict) else ""
    palette_hint = _style_palette_hint(store, project_id)
    prompt = _style_prompt(visual_language, tone, palette_hint)

    try:
        from film_pipeline.schemas._base import ArtifactType

        model_output = _request_style_bible_output(rt, prompt, project_id)
        result = _execute_style_bible_agent(model_output)
        if result is None:
            return _error("StyleBible agent produced invalid output.")
        bible = result["style_bible"]

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
    except Exception as exc:
        return _error(f"StyleBible generation failed: {exc}")
