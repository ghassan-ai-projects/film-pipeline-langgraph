"""Character bible generation tool."""

from __future__ import annotations

from typing import Any

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import _error, _latest_artifact_version, _ok, _services
from ._shared import _extract_script_text


async def generate_character_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate a CharacterBible from Script + FilmConstitution.

    Produces a locked character description (identity_block, voice, wardrobe,
    emotional arc, relationships) used by generate_reference_images for
    structured prompt construction.
    """
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")

    project_id = str(active["project_id"])
    character_id = str(args.get("character_id", "")).strip()
    if not character_id:
        return _error("character_id is required.")
    character_name = str(args.get("character_name", character_id)).strip()

    store = _services(rt).artifact_store

    # Load Script artifact
    try:
        from film_pipeline.schemas._base import FilmPhase

        script_data = store.load(project_id, FilmPhase("script"), "script", 1)
        script_text = _extract_script_text(script_data)
    except (FileNotFoundError, ValueError):
        return _error("Script artifact not found. Run script phase first.")

    # Load FilmConstitution artifact
    try:
        constitution = store.load(project_id, FilmPhase("constitution"), "film_constitution", 1)
    except (FileNotFoundError, ValueError):
        return _error("FilmConstitution not found. Run constitution phase first.")

    constitution_text = str(constitution.get("theme", "")) if isinstance(constitution, dict) else ""

    # Build prompt and call model
    prompt = f"""# Role
You are a character development specialist. Given a script and film constitution,
produce a detailed CharacterBible for a single character.

# Core Task
Create a CharacterBible for character '{character_name}' (id: {character_id}).

# Context
Film Constitution:
{constitution_text}

Script:
{script_text[:8000]}

# Constraints
- The identity_block must be a locked, invariant one-paragraph description
  of the character's visual appearance. This block is injected verbatim into
  every reference-image and video prompt — it must be specific and durable.
- voice_rules must capture cadence, vocabulary patterns, forbidden phrasings,
  and signature speech moves.
- wardrobe_rules must include a baseline description and act-specific variants.
- emotional_arc must have start_state, midpoint_state, end_state, and at least 2
  key_turning_points.
- relationship_map must list every meaningful relationship with other characters.
- must_not_change must list 3-5 identity invariants the agents must never alter.

# Output Format
Return ONLY valid JSON. No markdown fences, no commentary.
{{
  "character_id": "{character_id}",
  "project_id": "{project_id}",
  "visual_identity": {{
    "character_id": "{character_id}",
    "name": "{character_name}",
    "role": "protagonist | antagonist | supporting | foil",
    "age": "e.g. mid-40s",
    "physical_description": "Detailed physical description",
    "identity_block": "Locked one-paragraph visual description for prompts"
  }},
  "voice_rules": {{
    "cadence": "e.g. staccato, breathless",
    "vocabulary": ["signature", "words"],
    "forbidden_phrasings": ["never says X"],
    "signature_moves": ["repeating questions", "cutting people off"]
  }},
  "wardrobe_rules": {{
    "baseline": "Default costume description",
    "act_variants": {{"act_1": "description", "act_2": "description"}}
  }},
  "emotional_arc": {{
    "start_state": "e.g. guarded and distant",
    "midpoint_state": "e.g. vulnerable, beginning to trust",
    "end_state": "e.g. open, at peace",
    "key_turning_points": ["moment 1", "moment 2"]
  }},
  "relationship_map": [
    {{"other_character_id": "char_002", "relation": "description", "evolution": "how it changes"}}
  ],
  "reference_assets": [],
  "must_not_change": ["invariant 1", "invariant 2", "invariant 3"]
}}"""

    try:
        from film_pipeline.agents.impl.character_bible_agent import CharacterBibleAgent
        from film_pipeline.schemas._base import AgentFamily, AgentRole
        from film_pipeline.schemas.handoff import AgentRegistration

        agent = CharacterBibleAgent(
            AgentRegistration(
                agent_id="character-bible-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["character_development"],
                input_artifacts=["script", "film_constitution"],
                output_artifacts=["character_bible"],
            )
        )

        runner = _services(rt).prompt_runner

        # Use PromptRunner with model_adapter if available
        model_output: dict[str, Any]
        if runner.model_adapter is not None:
            raw = runner.model_adapter.chat(
                prompt, model=runner.model_router.resolve("creative_writer")
            )
            model_output = raw if isinstance(raw, dict) else {}
        else:
            # Mock mode: return a minimal valid response
            model_output = {
                "character_id": character_id,
                "project_id": project_id,
                "visual_identity": {
                    "character_id": character_id,
                    "name": character_name,
                    "role": "protagonist",
                    "age": "unknown",
                    "physical_description": "Generated in mock mode.",
                    "identity_block": (
                        f"A {character_name} — generated in mock mode. "
                        "Replace with real model output."
                    ),
                },
                "voice_rules": {
                    "cadence": "measured",
                    "vocabulary": [],
                    "forbidden_phrasings": [],
                    "signature_moves": [],
                },
                "wardrobe_rules": {"baseline": "", "act_variants": {}},
                "emotional_arc": {
                    "start_state": "unknown",
                    "midpoint_state": "unknown",
                    "end_state": "unknown",
                    "key_turning_points": [],
                },
                "relationship_map": [],
                "reference_assets": [],
                "must_not_change": ["identity_block"],
            }

        result = agent.execute(model_output)
        if not agent.validate(result):
            return _error("CharacterBible agent produced invalid output.")

        bible = result["character_bible"]

        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType
        from film_pipeline.schemas.artifact import ArtifactMetadata

        next_version = (
            _latest_artifact_version(store, project_id, FilmPhase("visual_dev"), "character_bible")
            + 1
        )
        meta = ArtifactMetadata(
            artifact_id="character_bible",
            artifact_type=ArtifactType.CHARACTER_BIBLE,
            project_id=project_id,
            phase=FilmPhase("visual_dev"),
            version=next_version,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_character_bible",
            created_at=datetime.now(UTC),
        )
        ref = store.save(bible, meta)

        active["character_bible_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)
        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(
            character_bible_ref=ref,
            character_id=character_id,
            identity_block=bible.visual_identity.identity_block,
        )

    except Exception as exc:
        return _error(f"CharacterBible generation failed: {exc}")
