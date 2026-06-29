"""Character / environment / camera / style / shot bible generation tools."""

from __future__ import annotations

from typing import Any, cast

import film_pipeline.mcp.tools as tools_pkg

from .helpers import _error, _latest_artifact_version, _ok, _services


def _extract_script_text(script_data: dict[str, object] | None) -> str:
    """Extract readable text from the Script artifact."""
    if script_data is None:
        return ""
    if isinstance(script_data, dict):
        scenes = script_data.get("scenes", script_data.get("content", []))
        if isinstance(scenes, list):
            lines: list[str] = []
            for scene in scenes:
                if isinstance(scene, dict):
                    heading = scene.get("heading", scene.get("scene_heading", ""))
                    if heading:
                        lines.append(str(heading))
                    if scene is not None:
                        for action in cast(
                            list[Any], scene.get("action_lines", scene.get("actions", []))
                        ):
                            lines.append(str(action))
                        for dialogue in cast(
                            list[Any], scene.get("dialogue_lines", scene.get("dialogue", []))
                        ):
                            if isinstance(dialogue, dict):
                                char = dialogue.get("character_id", dialogue.get("character", ""))
                                line = dialogue.get("line", dialogue.get("text", ""))
                                lines.append(f"{char}: {line}")
            return "\n".join(lines)
    return str(script_data)


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


def _generate_continuity_ledger(store: Any, project_id: str, matrix: Any) -> str | None:
    """Generate a basic continuity ledger from the shot matrix."""
    try:
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
        from film_pipeline.schemas.artifact import ArtifactMetadata
        from film_pipeline.schemas.continuity import (
            ContinuityLedger,
            ContinuityLedgerEntry,
            StateRecord,
        )

        entries: list[ContinuityLedgerEntry] = []
        prev_chars: list[str] = []
        prev_env = ""

        for _i, row in enumerate(matrix.rows):
            current_chars = [str(c) for c in row.characters]
            current_env = str(row.environment)
            entries.append(
                ContinuityLedgerEntry(
                    shot_id=row.shot_id,
                    state_in=[
                        StateRecord(
                            label="characters",
                            description=", ".join(prev_chars) if prev_chars else "none",
                            refs=prev_chars,
                        ),
                        StateRecord(
                            label="environment",
                            description=prev_env,
                            refs=[prev_env] if prev_env else [],
                        ),
                    ],
                    action="",
                    state_out=[
                        StateRecord(
                            label="characters",
                            description=", ".join(current_chars) if current_chars else "none",
                            refs=current_chars,
                        ),
                        StateRecord(
                            label="environment",
                            description=current_env,
                            refs=[current_env] if current_env else [],
                        ),
                    ],
                )
            )
            prev_chars = current_chars
            prev_env = current_env

        ledger = ContinuityLedger(
            project_id=project_id,
            entries=entries,
        )
        next_version = (
            _latest_artifact_version(
                store, project_id, FilmPhase("shot_bible"), "continuity_ledger"
            )
            + 1
        )
        meta = ArtifactMetadata(
            artifact_id="continuity_ledger",
            artifact_type=ArtifactType.CONTINUITY_LEDGER,
            project_id=project_id,
            phase=FilmPhase("shot_bible"),
            version=next_version,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_shot_bible",
            created_at=datetime.now(UTC),
        )
        return cast(str, store.save(ledger, meta))
    except Exception:
        return None


async def generate_shot_bible(args: dict[str, object]) -> dict[str, object]:
    """Generate MasterFilmMatrix + ContinuityLedger from Script + visual refs.

    Produces the shot-by-shot production matrix (every clip as a row with
    scene, characters, env, camera, chaining) and a continuity ledger
    tracking state_in/state_out per shot.
    """
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import FilmPhase

        script_data = store.load(project_id, FilmPhase("script"), "script", 1)
        ref_data = store.load(project_id, FilmPhase("visual_dev"), "reference_index", 1)
    except (FileNotFoundError, ValueError) as e:
        return _error(f"Required artifacts not found: {e}")

    script_text = _extract_script_text(script_data)
    ref_summary = ""
    if isinstance(ref_data, dict):
        entries = ref_data.get("entries", [])
        ref_summary = ", ".join(
            f"{e.get('subject_type', '')}/{e.get('subject_id', '')}({e.get('frame_role', '')})"
            for e in entries[:20]
            if isinstance(e, dict)
        )

    try:
        from film_pipeline.agents.impl.shot_bible_agent import ShotBibleAgent
        from film_pipeline.schemas._base import AgentFamily, AgentRole, ArtifactStatus, ArtifactType
        from film_pipeline.schemas.handoff import AgentRegistration

        agent = ShotBibleAgent(
            AgentRegistration(
                agent_id="shot-design-agent",
                family=AgentFamily.DEVELOPMENT,
                role=AgentRole.CREATOR,
                capabilities=["shot_design", "matrix_planning"],
                input_artifacts=["script", "visual_refs", "character_bible"],
                output_artifacts=["master_film_matrix"],
            )
        )
        runner = _services(rt).prompt_runner
        model_output: dict[str, Any]
        if runner.model_adapter is not None:
            raw = runner.model_adapter.chat(
                f"Create a MasterFilmMatrix from the script and visual references.\n\n"
                f"Script:\n{script_text[:6000]}\n\n"
                f"Visual references available:\n{ref_summary}\n\n"
                "Return JSON with 'shot_matrix' containing 'rows' array of shot rows "
                "(shot_id, act_id, scene_id, duration_seconds, characters, environment, "
                "camera_profile, priority, risk_level) and 'coverage_groups' array.",
                model=runner.model_router.resolve("creative_writer"),
            )
            model_output = raw if isinstance(raw, dict) else {}
        else:
            model_output = {
                "shot_matrix": {
                    "project_id": project_id,
                    "rows": [
                        {
                            "shot_id": "S001",
                            "act_id": "act1",
                            "scene_id": "scene_01",
                            "duration_seconds": 5,
                            "characters": ["leo"],
                            "environment": "studio",
                            "camera_profile": "default",
                            "priority": "standard",
                            "risk_level": "low",
                            "generation_order": 1,
                        }
                    ],
                    "coverage_groups": [],
                }
            }

        result = agent.execute(model_output)
        if not agent.validate(result):
            return _error("ShotBible agent produced invalid output.")
        matrix = result["shot_matrix"]

        from datetime import UTC, datetime

        from film_pipeline.schemas.artifact import ArtifactMetadata

        next_version = (
            _latest_artifact_version(
                store, project_id, FilmPhase("shot_bible"), "master_film_matrix"
            )
            + 1
        )
        meta = ArtifactMetadata(
            artifact_id="master_film_matrix",
            artifact_type=ArtifactType.MASTER_FILM_MATRIX,
            project_id=project_id,
            phase=FilmPhase("shot_bible"),
            version=next_version,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="mcp.generate_shot_bible",
            created_at=datetime.now(UTC),
        )
        ref = store.save(matrix, meta)
        active["shot_matrix_ref"] = ref
        active.setdefault("artifact_refs", []).append(ref)

        # Generate a basic continuity ledger from the matrix
        ledger_ref = _generate_continuity_ledger(store, project_id, matrix)

        rt.projects[project_id] = active
        rt._persist_project_state(project_id)

        return _ok(
            shot_matrix_ref=ref,
            shot_count=len(matrix.rows),
            continuity_ledger_ref=ledger_ref,
        )
    except Exception as exc:
        return _error(f"Shot bible generation failed: {exc}")
