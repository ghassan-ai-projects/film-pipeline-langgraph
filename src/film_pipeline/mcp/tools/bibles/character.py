"""Character bible generation tool."""

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
    _load_artifact_if_present,
    _load_script_text,
    _register_active_artifact_ref,
    _save_visual_dev_candidate,
)


def _character_prompt_mission(character_name: str, character_id: str) -> str:
    """Role and core-task section of the CharacterBible prompt."""
    return f"""# Role
You are a character development specialist. Given a script and film constitution,
produce a detailed CharacterBible for a single character.

# Core Task
Create a CharacterBible for character '{character_name}' (id: {character_id}).

"""


def _character_prompt_sources(constitution_text: str, script_text: str) -> str:
    """Constitution and script context section of the prompt."""
    return f"""# Context
Film Constitution:
{constitution_text}

Script:
{script_text[:8000]}

"""


def _character_prompt_constraints() -> str:
    """Quality-bar constraints section of the prompt."""
    return """# Constraints
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

"""


def _character_prompt_json_contract(character_id: str, character_name: str, project_id: str) -> str:
    """Output-format section of the prompt with the JSON skeleton."""
    return f"""# Output Format
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


def _character_prompt(
    character_id: str,
    character_name: str,
    project_id: str,
    constitution_text: str,
    script_text: str,
) -> str:
    """Assemble the full CharacterBible prompt for one character."""
    return (
        _character_prompt_mission(character_name, character_id)
        + _character_prompt_sources(constitution_text, script_text)
        + _character_prompt_constraints()
        + _character_prompt_json_contract(character_id, character_name, project_id)
    )


def _character_mock_payload(
    character_id: str, character_name: str, project_id: str
) -> dict[str, Any]:
    """Minimal valid CharacterBible response for mock mode."""
    return {
        "character_id": character_id,
        "project_id": project_id,
        "visual_identity": {
            "character_id": character_id,
            "name": character_name,
            "role": "protagonist",
            "age": "unknown",
            "physical_description": "Generated in mock mode.",
            "identity_block": (
                f"A {character_name} — generated in mock mode. Replace with real model output."
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


def _request_character_bible_output(
    rt: Any, prompt: str, character_id: str, character_name: str, project_id: str
) -> dict[str, Any]:
    """Obtain CharacterBible JSON from the model adapter or mock fallback."""
    return _chat_json_or_mock(
        rt, prompt, _character_mock_payload(character_id, character_name, project_id)
    )


def _execute_character_bible_agent(model_output: dict[str, Any]) -> dict[str, Any] | None:
    """Run CharacterBibleAgent over the model output; None signals invalid output."""
    from film_pipeline.agents.impl.character_bible_agent import CharacterBibleAgent
    from film_pipeline.schemas.base import AgentFamily, AgentRole
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
    result = agent.execute(model_output)
    if not agent.validate(result):
        return None
    return result


def _deliver_character_bible(
    rt: Any,
    active: dict[str, Any],
    store: Any,
    project_id: str,
    character_id: str,
    bible: Any,
) -> dict[str, object]:
    """Persist the bible, publish its ref on the active project, and respond."""
    from film_pipeline.schemas.base import ArtifactType

    ref = _save_visual_dev_candidate(
        store,
        project_id,
        "character_bible",
        ArtifactType.CHARACTER_BIBLE,
        "mcp.generate_character_bible",
        bible,
    )
    _register_active_artifact_ref(rt, active, project_id, "character_bible_ref", ref)
    return _ok(
        character_bible_ref=ref,
        character_id=character_id,
        identity_block=bible.visual_identity.identity_block,
    )


async def generate_character_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate a CharacterBible from Script + FilmConstitution.

    Produces a locked character description (identity_block, voice, wardrobe,
    emotional arc, relationships) used by generate_reference_images for
    structured prompt construction.
    """
    rt = tools_pkg.get_runtime()
    active = require_project_state(args)

    project_id = str(active["project_id"])
    character_id = str(args.get("character_id", "")).strip()
    if not character_id:
        return _error("character_id is required.")
    character_name = str(args.get("character_name", character_id)).strip()

    store = _services(rt).artifact_store

    script_text = _load_script_text(store, project_id)
    if script_text is None:
        return _error("Script artifact not found. Run script phase first.")

    constitution = _load_artifact_if_present(store, project_id, "constitution", "film_constitution")
    if constitution is None:
        return _error("FilmConstitution not found. Run constitution phase first.")

    prompt = _character_prompt(
        character_id,
        character_name,
        project_id,
        _constitution_theme(constitution),
        script_text,
    )

    try:
        model_output = _request_character_bible_output(
            rt, prompt, character_id, character_name, project_id
        )
        result = _execute_character_bible_agent(model_output)
        if result is None:
            return _error("CharacterBible agent produced invalid output.")
        return _deliver_character_bible(
            rt, active, store, project_id, character_id, result["character_bible"]
        )

    except Exception as exc:
        return _error(f"CharacterBible generation failed: {exc}")
