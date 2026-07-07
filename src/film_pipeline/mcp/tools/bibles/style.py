"""Style bible generation tool."""

from __future__ import annotations

from typing import Any

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import _error, _latest_artifact_version, _ok, _services


async def generate_style_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate a StyleBible from FilmConstitution + EnvironmentBible palettes."""
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

    visual_language = (
        str(constitution.get("visual_language", "")) if isinstance(constitution, dict) else ""
    )
    tone = str(constitution.get("tone", "")) if isinstance(constitution, dict) else ""
    palette_hint = ""
    try:
        env_bible = store.load(project_id, FilmPhase("visual_dev"), "environment_bible", 1)
        if isinstance(env_bible, dict):
            palette_hint = ", ".join(str(c) for c in env_bible.get("color_palette", [])[:6])
    except (FileNotFoundError, ValueError):
        pass

    try:
        from film_pipeline.agents.impl.style_bible_agent import StyleBibleAgent
        from film_pipeline.schemas._base import AgentFamily, AgentRole, ArtifactStatus, ArtifactType
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
        runner = _services(rt).prompt_runner
        model_output: dict[str, Any]
        if runner.model_adapter is not None:
            raw = runner.model_adapter.chat(
                f"Create a StyleBible. Visual language: {visual_language}. "
                f"Tone: {tone}. Palette hints: {palette_hint}. "
                "Return JSON with 'color_palette' (4-8 hex codes), "
                "'texture', 'grain', 'visual_mood', 'reference_stills', "
                "and 'must_not_change'.",
                model=runner.model_router.resolve("creative_writer"),
            )
            model_output = raw if isinstance(raw, dict) else {}
        else:
            model_output = {
                "project_id": project_id,
                "color_palette": ["#1a1a2e", "#e94560", "#0f3460", "#16213e"],
                "texture": "gritty, painterly",
                "grain": "subtle 16mm grain",
                "visual_mood": "melancholic, high-contrast",
                "reference_stills": [],
                "must_not_change": ["color_palette"],
            }

        result = agent.execute(model_output)
        if not agent.validate(result):
            return _error("StyleBible agent produced invalid output.")
        bible = result["style_bible"]

        from datetime import UTC, datetime

        from film_pipeline.schemas.artifact import ArtifactMetadata

        next_version = (
            _latest_artifact_version(store, project_id, FilmPhase("visual_dev"), "style_bible") + 1
        )
        meta = ArtifactMetadata(
            artifact_id="style_bible",
            artifact_type=ArtifactType.STYLE_BIBLE,
            project_id=project_id,
            phase=FilmPhase("visual_dev"),
            version=next_version,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_style_bible",
            created_at=datetime.now(UTC),
        )
        ref = store.save(bible, meta)
        active["style_bible_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(style_bible_ref=ref, palette=bible.color_palette, mood=bible.visual_mood)
    except Exception as exc:
        return _error(f"StyleBible generation failed: {exc}")
