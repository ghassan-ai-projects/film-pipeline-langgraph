"""Production agent templates: visual dev, shot bible, generation, QC, assembly, review."""

from __future__ import annotations

from film_pipeline.agents._prompt_template import PromptTemplate
from film_pipeline.agents.prompt_templates.defaults._quality import (
    _QUALITY_DIRECTIVE,
)


def _visual_development_creator() -> PromptTemplate:
    return PromptTemplate(
        template_id="visual-dev-creator-v2",
        agent_id="reference-strategy-planner",
        version=2,
        role="You are the visual-dev-agent (Visual Development Creator). "
        "Your role is to design the visual look of the film.",
        core_task=(
            "Create visual development references from the script and constitution:\n"
            "1. Produce reference entries for EVERY character in the script.\n"
            "2. Produce reference entries for EVERY environment/location.\n"
            "3. For characters: front-face (neutral), 3-4-left, 3-4-right, "
            "profile, plus key expressions.\n"
            "4. For environments: wide-establishing, key angles, lighting variants.\n"
            "5. Assign provider tiers: 'fast' for bulk (environments, body shots, "
            "expressions), 'standard' for critical anchors (hero face, key poses), "
            "'ultra' for detail insets (eyes, hands, textures).\n"
            "6. The film is {target_runtime_seconds}s ({film_type}). Scale "
            "reference count accordingly."
        ),
        context_template=(
            "{constraints}\n\n" + "Script ref: {script_ref}\n"
            "Script content:\n{script_content}\n"
            "Story bible ref: {story_bible_ref}\n"
            "Story bible content:\n{story_bible_content}\n"
            "Constitution ref: {constitution_ref}\n"
            "Constitution content:\n{constitution_content}\n"
            "Target runtime: {target_runtime_seconds}s | Film type: {film_type}\n"
            "Project ID: {project_id}\n"
            "KB refs: {kb_refs}"
        ),
        constraints=(
            "Visual references must be concrete and production-ready. "
            "Every shot must reference specific camera and lighting choices. "
            "The visual language must be consistent with the constitution."
        ),
        output_format=(
            "Respond with valid JSON containing visual development references.\n"
            "{\n"
            '  "visual_dev": {\n'
            '    "project_id": "...",\n'
            '    "reference_entries": [\n'
            "      {\n"
            '        "reference_id": "ref_001",\n'
            '        "asset_path": "",\n'
            '        "asset_type": "character_identity_sheet",\n'
            '        "subject_type": "character",\n'
            '        "subject_id": "char_001",\n'
            '        "approved_for": ["prompt_anchor"],\n'
            '        "quality_score": 80.0,\n'
            '        "provider": "",\n'
            '        "tier": "fast",\n'
            '        "frame_role": "front-face",\n'
            '        "expression": "neutral",\n'
            '        "lighting": "",\n'
            '        "prompt_text": "Create a production-ready character sheet...",\n'
            '        "prompt_refs": [],\n'
            '        "source_frames": [],\n'
            '        "notes": "",\n'
            '        "moderation_risk": "low",\n'
            '        "validation": {"status": "pending", "score": 0.0, "reports": []},\n'
            '        "ai_usability": {"score": 0.0, "risks": [], "notes": ""}\n'
            "      }\n"
            "    ]\n"
            "  }\n"
            "}"
        ),
        output_schema_ref="reference.ReferenceIndex",
        quality_instructions=_QUALITY_DIRECTIVE,
    )


def _shot_bible_creator() -> PromptTemplate:
    return PromptTemplate(
        template_id="shot-bible-creator-v5",
        agent_id="shot-design-agent",
        version=5,
        role=(
            "You are the shot-bible-agent (Shot Bible Creator). "
            "Your PRIMARY job is to produce exactly the right number of shot "
            "matrix rows as specified in the Execution Brief. Creativity comes "
            "second — first, get the count and runtime correct. The Execution "
            "Brief overrides conflicting scene, treatment, or shot-count hints."
        ),
        core_task=(
            "STEP 1: Read the Execution Brief below. Extract the total number "
            "of shots required (sum all movement shot_counts) and the target "
            "runtime. Write these down.\n\n"
            "STEP 2: Produce EXACTLY that many master_film_matrix rows. "
            "Each row must have: shot_id, act_id (matching the movement_id from "
            "the brief), scene_id, duration_seconds, characters, environment, "
            "camera_profile, and prompt_ref.\n\n"
            "STEP 3: After writing all rows, COUNT THEM. Verify the count "
            "matches the brief's total. Verify the sum of duration_seconds "
            "matches the target runtime. If not, adjust before outputting.\n\n"
            "The script and visual references provide the creative content "
            "(what happens in each shot). But the STRUCTURE (how many shots, "
            "how long) comes ONLY from the Execution Brief. Do not improvise "
            "the count or turn scenes/movements into additional acts."
        ),
        context_template=(
            "{constraints}\n\n" + "=== EXECUTION BRIEF (YOUR STRUCTURAL CONTRACT) ===\n"
            "{execution_brief_content}\n"
            "=== END BRIEF ===\n\n"
            "=== SCENE LIST (every scene must be covered) ===\n"
            "Scene list ref: {scene_list_ref}\n"
            "Scene list content:\n{scene_list_content}\n\n"
            "Script ref: {script_ref}\n"
            "Script content:\n{script_content}\n"
            "Visual refs: {visual_refs}\n"
            "Visual refs content:\n{visual_refs_content}\n"
            "Target scene count: {target_scene_count}\n"
            "Project ID: {project_id}\n"
            "KB refs: {kb_refs}"
        ),
        constraints=(
            "1. COUNT FIRST: Before writing any creative content, determine the "
            "exact number of rows needed from the Execution Brief. Write this "
            "number at the top of your working memory.\n"
            "2. DISTRIBUTE BY ACT: Each row's act_id must match the "
            "movement_id in the brief. If act_1 needs 5 shots, produce exactly "
            "5 rows with act_id='act_1'.\n"
            "3. COVER EVERY SCENE: Every scene_id from the Scene List and Script "
            "must appear in at least one matrix row. No scene may be dropped.\n"
            "4. DURATION PER SHOT: Use the duration_range_seconds from the "
            "brief. If the range is [10,15], each shot must be 10-15 seconds.\n"
            "5. FINAL COUNT CHECK: Count your rows before outputting. Compare "
            "to the brief. If they don't match, add or remove rows until they do.\n"
            "6. FINAL RUNTIME CHECK: Sum all duration_seconds. Compare to "
            "target_runtime_seconds. Adjust individual durations if needed.\n"
            "7. The Execution Brief is authoritative over conflicting project "
            "target_shot_count or max_shot_count hints.\n"
            "8. Every shot must have camera position, movement, lens, and "
            "emotional intent."
        ),
        output_format=(
            "Respond with valid JSON:\n"
            "{\n"
            '  "shot_matrix": {\n'
            '    "project_id": "...",\n'
            '    "rows": [\n'
            "      // EXACTLY the number of rows specified in the Execution Brief\n"
            "      // Count: you must output N rows where N = sum of all "
            "movement shot_counts\n"
            "      {\n"
            '        "shot_id": "s_001",\n'
            '        "act_id": "act_1",\n'
            '        "scene_id": "sc_001",\n'
            '        "duration_seconds": 12,\n'
            '        "characters": ["..."],\n'
            '        "environment": "...",\n'
            '        "camera_profile": "...",\n'
            '        "prompt_ref": "",\n'
            '        "generation_order": 1\n'
            "      }\n"
            "      // ... more rows to reach the EXACT count from the brief\n"
            "    ],\n"
            '    "coverage_groups": []\n'
            "  }\n"
            "}"
        ),
        output_schema_ref="matrix.ShotMatrix",
        quality_instructions=_QUALITY_DIRECTIVE,
    )


def _generation_planner() -> PromptTemplate:
    return PromptTemplate(
        template_id="generation-planner-v4",
        agent_id="provider-planning-agent",
        version=4,
        role="You are the generation-planner-agent (Generation Planner). "
        "Your role is to plan the generation batch for the shot matrix, "
        "respecting the structural requirements in the Execution Brief.",
        core_task=(
            "Create a generation plan from the shot matrix. "
            "Group shots by provider compatibility, estimate cost, "
            "prioritize by dependency, and flag risky shots.\n\n"
            "IMPORTANT: The Execution Brief defines the film's structure. "
            "Every shot row in the matrix must have a complete generation plan. "
            "Do not skip rows. Your cost estimate must reflect the ACTUAL "
            "number of shots — not a placeholder."
        ),
        context_template=(
            "{constraints}\n\n" + "Execution Brief (film structure):\n{execution_brief_content}\n\n"
            "Shot matrix ref: {shot_matrix_ref}\n"
            "Shot matrix content:\n{shot_matrix_content}\n"
            "Budget cap: {budget_cap}\n"
            "Preferred providers: {preferred_providers}\n"
            "Project ID: {project_id}\n"
            "KB refs: {kb_refs}"
        ),
        constraints=(
            "Shots must be grouped by provider compatibility. "
            "{provider_pricing}\n"
            "Dependency ordering must prevent generation of a shot before "
            "its prerequisites. Flag shots that exceed budget or require "
            "unavailable providers.\n"
            "Every shot in the matrix must have a plan entry. "
            "Count your planned entries against the matrix row count. "
            "Cost estimate must have clip_count matching the total shots."
        ),
        output_format=(
            "Respond with valid JSON:\n"
            "{\n"
            '  "generation_plan": {\n'
            '    "project_id": "...",\n'
            '    "cost_estimate": {\n'
            '      "project_id": "...",\n'
            '      "batch_id": "batch-001",\n'
            '      "provider": "seedance",\n'
            '      "estimated_cost_usd": 12.50,\n'
            '      "clip_count": 20,\n'
            '      "notes": "20 shots at $0.18/s avg 12s = $43.20"\n'
            "    },\n"
            '    "shot_groups": [\n'
            "      {\n"
            '        "shot_id": "s_001",\n'
            '        "provider": "seedance",\n'
            '        "model": "2.0",\n'
            '        "mode": "test",\n'
            '        "priority": 1,\n'
            '        "estimated_cost_usd": 2.16\n'
            "      }\n"
            "    ],\n"
            '    "total_shots": 20,\n'
            '    "total_cost_usd": 43.20\n'
            "  }\n"
            "}"
        ),
        output_schema_ref="generation.GenerationPlan",
    )


def _qc_synthesizer() -> PromptTemplate:
    return PromptTemplate(
        template_id="qc-synthesizer-v3",
        agent_id="clip-validator",
        version=3,
        role="You are the qc-synthesis-agent (QC Synthesizer). "
        "Your role is to synthesize validation findings from all phases "
        "into a unified quality report with consensus scoring.",
        core_task=(
            "Review the validation findings below. Produce a unified QC report:\n"
            "1. Identify which findings agree across validators (shared findings).\n"
            "2. Identify disagreements and conflicting assessments.\n"
            "3. Compute agreement level: 'high' if 75%+ agree, 'medium' if "
            "50-75%, 'low' if under 50%.\n"
            "4. Produce a consensus status: 'pass' if no blocking findings and "
            "most validators pass, 'pass_with_notes' if minor issues, "
            "'needs_revision' if significant issues, 'blocked' if critical.\n"
            "5. Provide an orchestrator recommendation: one sentence on whether "
            "to advance, retry, or escalate."
        ),
        context_template=(
            "{constraints}\n\n" + "Validator findings (issues from all phases):\n"
            "{validator_issues}\n\n"
            "Project ID: {project_id}\n"
            "KB refs: {kb_refs}"
        ),
        constraints=(
            "Consensus must be computed by agreement level, not simple majority. "
            "Blocking findings from any validator must be preserved. "
            "Conflicting validator findings must be escalated with both positions. "
            "If no issues exist, report 'pass' with an empty reviewer list."
        ),
        output_format=(
            "Respond with valid JSON:\n"
            "{\n"
            '  "consensus": {\n'
            '    "review_id": "qc-001",\n'
            '    "project_id": "...",\n'
            '    "reviewers": [\n'
            '      {"model_id": "validator-1", "score": 85, "passed": true, '
            '"notes": "..."}\n'
            "    ],\n"
            '    "agreement_level": "high",\n'
            '    "consensus_status": "pass",\n'
            '    "shared_findings": ["..."],\n'
            '    "disagreements": ["..."],\n'
            '    "artifact_refs": [],\n'
            '    "orchestrator_recommendation": "..."\n'
            "  }\n"
            "}"
        ),
        output_schema_ref="validation.ConsensusReport",
    )


def _assembly_agent() -> PromptTemplate:
    return PromptTemplate(
        template_id="assembly-agent-v3",
        agent_id="failure-handling-agent",
        version=3,
        role="You are the assembly-agent (Post-Production Assembly). "
        "Your role is to assemble the final cut from generated media.",
        core_task=(
            "Create an assembly plan from generated media and the shot matrix:\n"
            "1. Order clips by shot_id matching the matrix.\n"
            "2. Define transitions between every pair of consecutive shots.\n"
            "3. Plan audio: music, SFX, and dialogue tracks.\n"
            "4. Define color look per scene.\n"
            "5. Compute total duration from clip in/out points."
        ),
        context_template=(
            "{constraints}\n\n" + "Shot matrix ref: {shot_matrix_ref}\n"
            "Shot matrix content:\n{shot_matrix_content}\n"
            "Script ref: {script_ref}\n"
            "Script content:\n{script_content}\n"
            "Project ID: {project_id}\n"
            "KB refs: {kb_refs}"
        ),
        constraints=(
            "Assembly must follow the shot order defined in the shot matrix. "
            "Transitions must be motivated by emotional or narrative intent "
            "(cut for continuity, dissolve for time passage, fade for chapter breaks). "
            "Audio and subtitle tracks must reference actual generated assets. "
            "Delivery format must match the project profile."
        ),
        output_format=(
            "Respond with valid JSON:\n"
            "{\n"
            '  "assembly": {\n'
            '    "cut_id": "review-cut-v1",\n'
            '    "project_id": "...",\n'
            '    "clip_order": [\n'
            '      {"shot_id": "s_001", "source_asset_ref": "", '
            '"in_seconds": 0, "out_seconds": 12, "coverage_role": ""}\n'
            "    ],\n"
            '    "transitions": [\n'
            '      {"from_shot_id": "s_001", "to_shot_id": "s_002", '
            '"transition_type": "cut", "duration_seconds": 0}\n'
            "    ],\n"
            '    "audio_plan": {"music_track_refs": [], "sfx_track_refs": [], '
            '"dialogue_track_refs": []},\n'
            '    "color_plan": {"look": "...", "per_scene": {}},\n'
            '    "duration_total_seconds": 240\n'
            "  }\n"
            "}"
        ),
        output_schema_ref="assembly.AssemblyPlan",
    )


def _orchestrator_review() -> PromptTemplate:
    return PromptTemplate(
        template_id="orchestrator-review-v3",
        agent_id="orchestrator-agent",
        version=3,
        role=(
            "You are the orchestrator-agent (Autonomous Quality Reviewer). "
            "Your role is to review creative output against the film's target "
            "runtime and constitution. You decide whether to approve, request "
            "revision, or escalate to human."
        ),
        core_task=(
            "Review the phase output below. Decide ONE action:\n\n"
            "1. APPROVE — output is structurally sound for the target runtime. "
            "The scene count, content depth, and pacing support the intended duration.\n\n"
            "2. REVISE — output needs specific improvements. Give ONE focused, "
            "creative suggestion. Reference specific scenes or elements. "
            "Say what's good and should be preserved. Do not list multiple issues — "
            "pick the most impactful one.\n\n"
            "3. ESCALATE — output is fundamentally wrong, the target is ambiguous, "
            "or this is the 3rd repair attempt without convergence. "
            "Only escalate when you cannot provide useful creative direction."
        ),
        context_template=(
            "{constraints}\n\n" + "TARGET FILM:\n"
            "  Runtime: {target_runtime_seconds}s\n"
            "  Film type: {film_type}\n"
            "  Pacing: {pacing_style}\n\n"
            "CONSTITUTION:\n"
            "{constitution_summary}\n\n"
            "CURRENT PHASE: {current_phase}\n"
            "CONVERGENCE ROUND: {convergence_round} of 3\n\n"
            "PHASE OUTPUT:\n"
            "{phase_output_summary}\n\n"
            "METRICS:\n"
            "{metrics_summary}\n\n"
            "CONSISTENCY WARNINGS:\n"
            "{consistency_warnings}"
        ),
        constraints=(
            "Choose exactly ONE action. Judge on craft — story, character, emotion, "
            "scene quality — not mechanics. Reference actual elements from the output "
            "(scene IDs, character names, specific descriptions) and say what to "
            "preserve, not just what to change. When revising, lead with the single "
            "most impactful change; you may note secondary issues briefly. "
            "Structural floors (scene count, runtime) are enforced separately by the "
            "Scope Contract and its gates — do NOT approve away a structural shortfall, "
            "and do not spend your judgment re-deriving counts. Focus on whether the "
            "writing is good enough to earn the runtime it fills."
        ),
        output_format=(
            "Respond with valid JSON:\n"
            "{\n"
            '  "orchestrator_decision": {\n'
            '    "action": "approve | revise | escalate",\n'
            '    "feedback": "If revising: one specific, creative suggestion. '
            'Reference specific scenes or elements.",\n'
            '    "preserve": ["what is good and should be kept"],\n'
            '    "reasoning": "Why this decision. Brief."\n'
            "  }\n"
            "}"
        ),
        output_schema_ref="orchestrator.OrchestratorDecision",
    )


# --- Visual-development bible creators ---------------------------------------
# These four are invoked through MCP (``mcp.tools.bibles``) rather than a graph
# phase. Their prose was previously assembled inline in each MCP tool; it lives
# here now so the MCP path and the graph path render prompts the same way, from
# the same registry. Versions start at 1 because no template existed before.


def _camera_bible_creator() -> PromptTemplate:
    return PromptTemplate(
        template_id="camera-bible-creator-v1",
        agent_id="camera-bible-agent",
        version=1,
        role=(
            "You are a camera language specialist. Given a film's camera "
            "philosophy, define the lens, framing, and movement vocabulary the "
            "film will be shot with."
        ),
        core_task=(
            "Create a CameraLanguageBible for a film whose camera philosophy is:\n"
            "{camera_philosophy}\n\n"
            "Define reusable camera profiles, and name one as the default."
        ),
        context_template=(
            "{constraints}\n\n"
            "Camera philosophy: {camera_philosophy}\n"
            "Project ID: {project_id}\n"
            "KB refs: {kb_refs}"
        ),
        constraints=(
            "Every profile must be filmable with a real lens and support. "
            "Movement must be achievable without specialized rigs beyond a "
            "gimbal, dolly, or tripod. Exactly one profile_id must equal "
            "default_profile_id."
        ),
        output_format=(
            "Respond with valid JSON:\n"
            "{\n"
            '  "camera_bible": {\n'
            '    "project_id": "...",\n'
            '    "profiles": [\n'
            "      {\n"
            '        "profile_id": "default",\n'
            '        "use_case": "...",\n'
            '        "lens": "...",\n'
            '        "framing": "...",\n'
            '        "movement": "...",\n'
            '        "depth_of_field": "...",\n'
            '        "composition_rules": ["..."],\n'
            '        "transition_rules": ["..."],\n'
            '        "emotional_meaning": "..."\n'
            "      }\n"
            "    ],\n"
            '    "default_profile_id": "default"\n'
            "  }\n"
            "}"
        ),
        output_schema_ref="camera.CameraLanguageBible",
    )


def _character_bible_creator() -> PromptTemplate:
    return PromptTemplate(
        template_id="character-bible-creator-v1",
        agent_id="character-bible-agent",
        version=1,
        role=(
            "You are a character development specialist. Given a script and film "
            "constitution, produce a detailed CharacterBible for a single character."
        ),
        core_task=(
            "Create a CharacterBible for character '{character_name}' (id: {character_id})."
        ),
        context_template=(
            "{constraints}\n\n"
            "Film Constitution:\n{constitution_content}\n\n"
            "Script:\n{script_content}\n\n"
            "Character: {character_name} (id: {character_id})\n"
            "Project ID: {project_id}\n"
            "KB refs: {kb_refs}"
        ),
        constraints=(
            "locked_prompt_block must be a one-paragraph physical description "
            "injected verbatim into every image prompt for this character — "
            "specific, durable, and free of transient state. "
            "identity must contain only appearance facts that never change. "
            "voice_rules must describe how the character speaks, not what they say."
        ),
        output_format=(
            "Respond with valid JSON:\n"
            "{\n"
            '  "character_bible": {\n'
            '    "project_id": "...",\n'
            '    "character_id": "...",\n'
            '    "identity": {"age_range": "...", "gender_presentation": "...", '
            '"build": "...", "distinguishing_marks": ["..."]},\n'
            '    "voice_rules": {"register": "...", "pace": "...", '
            '"verbal_tics": ["..."]},\n'
            '    "wardrobe_rules": {"palette": ["#rrggbb"], "silhouette": "...", '
            '"must_not_change": ["..."]},\n'
            '    "emotional_arc": {"start_state": "...", "end_state": "...", '
            '"turning_points": ["..."]},\n'
            '    "relationships": [],\n'
            '    "locked_prompt_block": "..."\n'
            "  }\n"
            "}"
        ),
        output_schema_ref="character.CharacterBible",
    )


def _environment_bible_creator() -> PromptTemplate:
    return PromptTemplate(
        template_id="environment-bible-creator-v1",
        agent_id="environment-bible-agent",
        version=1,
        role=(
            "You are an environment design specialist. Given a script and film "
            "constitution, produce a detailed EnvironmentBible for a single location."
        ),
        core_task=(
            "Create an EnvironmentBible for environment '{environment_name}' "
            "(id: {environment_id})."
        ),
        context_template=(
            "{constraints}\n\n"
            "Film Theme: {theme}\n"
            "Visual Language: {visual_language}\n\n"
            "Script:\n{script_content}\n\n"
            "Environment: {environment_name} (id: {environment_id})\n"
            "Project ID: {project_id}\n"
            "KB refs: {kb_refs}"
        ),
        constraints=(
            "locked_prompt_block must be a one-paragraph description of the "
            "environment injected verbatim into every prompt — specific and durable. "
            "fingerprint.text must be a compressed invariant block (2-3 sentences) "
            "capturing the essence of the space. "
            "zones are sub-areas, each with allowed viewpoints. "
            "viewpoints are approved camera positions with lens and framing. "
            "lighting_states must be named and repeatable (at least 2). "
            "color_palette must be 4-8 hex color codes."
        ),
        output_format=(
            "Respond with valid JSON:\n"
            "{\n"
            '  "environment_bible": {\n'
            '    "environment_id": "...",\n'
            '    "project_id": "...",\n'
            '    "name": "...",\n'
            '    "locked_prompt_block": "...",\n'
            '    "invariants": [],\n'
            '    "zones": [],\n'
            '    "viewpoints": [],\n'
            '    "lighting_states": [],\n'
            '    "color_palette": ["#rrggbb"],\n'
            '    "fingerprint": {"text": "..."},\n'
            '    "reference_assets": [],\n'
            '    "must_not_change": ["locked_prompt_block"]\n'
            "  }\n"
            "}"
        ),
        output_schema_ref="environment.EnvironmentBible",
    )


def _style_bible_creator() -> PromptTemplate:
    return PromptTemplate(
        template_id="style-bible-creator-v1",
        agent_id="style-bible-agent",
        version=1,
        role=(
            "You are a visual style specialist. Given a film's visual language, "
            "tone, and existing environment palettes, define one consistent look "
            "the whole film is graded and rendered to."
        ),
        core_task=(
            "Create a StyleBible. Visual language: {visual_language}. "
            "Tone: {tone}. Palette hints: {palette_hint}."
        ),
        context_template=(
            "{constraints}\n\n"
            "Visual language: {visual_language}\n"
            "Tone: {tone}\n"
            "Palette hints: {palette_hint}\n"
            "Project ID: {project_id}\n"
            "KB refs: {kb_refs}"
        ),
        constraints=(
            "color_palette must be 4-8 hex codes and must be consistent with the "
            "existing environment palettes. texture, grain, and visual_mood must "
            "each be concrete enough to steer a render. "
            "must_not_change names the values later phases may not alter."
        ),
        output_format=(
            "Respond with valid JSON:\n"
            "{\n"
            '  "style_bible": {\n'
            '    "project_id": "...",\n'
            '    "color_palette": ["#rrggbb"],\n'
            '    "texture": "...",\n'
            '    "grain": "...",\n'
            '    "visual_mood": "...",\n'
            '    "reference_stills": [],\n'
            '    "must_not_change": ["color_palette"]\n'
            "  }\n"
            "}"
        ),
        output_schema_ref="style.StyleBible",
    )
