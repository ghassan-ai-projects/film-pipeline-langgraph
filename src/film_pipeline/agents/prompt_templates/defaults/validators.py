"""Validator prompt templates for LLM-based validation (7 validators)."""

from __future__ import annotations

from film_pipeline.agents._prompt_template import PromptTemplate


def _script_structure_validator() -> PromptTemplate:
    return PromptTemplate(
        template_id="script-structure-v2",
        agent_id="scene-writing-validator",
        version=2,
        role=(
            "You are a senior script editor with 20 years of experience in dramatic "
            "screenwriting. You can spot structural weakness in a scene within the "
            "first page."
        ),
        core_task=(
            "Evaluate the script scenes against this weighted rubric:\n\n"
            "1. CONFLICT PRESENCE (30 pts): Does every scene contain dramatic "
            "tension? Not keyword matching — a scene where characters disagree "
            "subtly has conflict. A scene with the word 'conflict' but zero tension "
            "does not.\n\n"
            "2. INTENT FULFILLMENT (25 pts): Each scene has a declared intent_ref. "
            "Verify the scene delivers on that intent.\n\n"
            "3. STRUCTURAL FLOW (20 pts): Do scenes build logically? Rising tension, "
            "turning points at act breaks, proper resolution, no redundant scenes.\n\n"
            "4. PACING (15 pts): Appropriate scene length for dramatic weight. "
            "Critical confrontations need room; transition scenes should be efficient.\n\n"
            "5. DIALOGUE/ACTION BALANCE (10 pts): Not pure talking heads, not pure "
            "action without context."
        ),
        context_template=(
            "{constraints}\n\n" + "SCRIPT CONTENT:\n{script_content}\n\n"
            "SCENE INTENTS:\n{scene_intents}\n\n"
            "FILM CONSTITUTION:\n{film_constitution}\n\n"
            "TARGET RUNTIME: {target_runtime_seconds}s\n"
            "SCENE COUNT: {scene_count}"
        ),
        constraints=(
            "BLOCKING: scenes with zero dramatic tension, scenes that do not deliver "
            "on declared intent_ref, missing act turning points, no character "
            "motivation visible.\n"
            "WARNING: slightly rushed or padded scenes, dialogue-heavy scenes needing "
            "more action.\n\n"
            "For every issue, include a 'suggestion' field with the EXACT fix — "
            "reference specific scene_ids, character names, or dialogue lines. "
            "NOT vague like 'add more conflict'."
        ),
        output_format=(
            '{"score": <0-100>, "passed": <true|false>, "issues": ['
            '{"code": "<code>", "severity": "<blocking|warning>", '
            '"message": "<what is wrong>", '
            '"suggestion": "<exactly what to do to fix it>", '
            '"affected_entity": "<scene_id>", '
            '"affected_field": "<dialogue|action_lines|intent_ref>", '
            '"affected_shot": "<scene_id>"}]}'
        ),
        output_schema_ref="validation.ValidationReport",
    )


def _dialogue_voice_validator() -> PromptTemplate:
    return PromptTemplate(
        template_id="dialogue-voice-v2",
        agent_id="dialogue-voice-validator",
        version=2,
        role=(
            "You are a dialogue coach and dramaturg who has worked with Academy "
            "Award-winning actors. You can hear a character's voice in your head "
            "after reading three lines, and you know instantly when a line does not "
            "belong to that character."
        ),
        core_task=(
            "Evaluate all dialogue against this weighted rubric:\n\n"
            "1. VOICE DIFFERENTIATION (35 pts): Read all of Character A's lines, "
            "then Character B's. Would you know who was speaking if names were "
            "removed? Check vocabulary, sentence rhythm, formality, verbal tics.\n\n"
            "2. CHARACTER TRUTH (25 pts): Compare dialogue against CharacterDossier. "
            "The 'must_not_change' traits are SACRED — flag any violation.\n\n"
            "3. ORGANIC EXPOSITION (20 pts): Is information revealed through conflict "
            "and discovery, or dumped? 'As you know...' = BAD. 'You were not there.' "
            "= GOOD.\n\n"
            "4. DIALOGUE ECONOMY (10 pts): Could any line be cut without losing "
            "character, plot, or emotion?\n\n"
            "5. SUBTEXT (10 pts): Do characters say exactly what they mean? Strong "
            "dialogue has characters saying one thing while meaning another."
        ),
        context_template=(
            "{constraints}\n\n" + "SCRIPT DIALOGUE:\n{script_content}\n\n"
            "CHARACTER DOSSIERS:\n{character_dossiers}\n\n"
            "CHARACTER VOICE NOTES:\n{voice_notes}"
        ),
        constraints=(
            "BLOCKING: two or more characters with indistinguishable voices, "
            "dialogue violating 'must_not_change' traits, exposition dumps, "
            "any character with zero distinctive speech patterns.\n"
            "WARNING: scenes where one character dominates, occasional generic "
            "lines.\n\n"
            "For every issue, include a 'suggestion' field with the EXACT line "
            "that is problematic (quote it) and a rewritten version."
        ),
        output_format=(
            '{"score": <0-100>, "passed": <true|false>, "issues": ['
            '{"code": "<code>", "severity": "<blocking|warning>", '
            '"message": "<what is wrong, quote the line>", '
            '"suggestion": "<rewrite the line or add direction>", '
            '"affected_entity": "<character_id>", '
            '"affected_field": "dialogue", '
            '"affected_shot": "<scene_id>"}]}'
        ),
        output_schema_ref="validation.ValidationReport",
    )


def _prompt_readiness_validator() -> PromptTemplate:
    return PromptTemplate(
        template_id="prompt-readiness-v2",
        agent_id="prompt-readiness-validator",
        version=2,
        role=(
            "You are a prompt engineer who has designed thousands of LLM prompts "
            "for production systems. You know the difference between a good prompt "
            "and a great prompt is specificity."
        ),
        core_task=(
            "Evaluate each prompt entry against this rubric:\n\n"
            "1. TASK SPECIFICITY (30 pts): Can an LLM read the core_task and know "
            "exactly what to produce? 'Create a shot of the hero' = BAD. 'Generate "
            "an over-the-shoulder shot of the hero at the desk, lit by a single "
            "desk lamp, rain streaking the window' = GOOD.\n\n"
            "2. ROLE CLARITY (25 pts): Does the role give the LLM a useful lens? "
            "The role should narrow creative space, not broaden it.\n\n"
            "3. CONSTRAINT QUALITY (20 pts): Are constraints specific and testable? "
            "Flag any constraint using 'maybe', 'try to', 'if possible', "
            "'preferably', or 'should' without measurable standards.\n\n"
            "4. CONTEXT COMPLETENESS (15 pts): Can the agent execute without "
            "guessing? Every reference in the prompt must be available in context.\n\n"
            "5. OUTPUT FORMAT (10 pts): Is the output schema appropriate and "
            "well-defined?"
        ),
        context_template=(
            "{constraints}\n\n" + "PROMPT ENTRIES:\n{prompt_entries}\n\n"
            "EXPECTED OUTPUT SCHEMA: {output_schema}\n\n"
            "AVAILABLE CONTEXT VARIABLES: {context_variables}\n"
            "ENTRY COUNT: {entry_count}"
        ),
        constraints=(
            "BLOCKING: core task is vague (under 20 words, no specific descriptors), "
            "missing artifact references, ambiguous constraints, no output schema.\n"
            "WARNING: role could be more specific, context includes unnecessary "
            "information.\n\n"
            "For every issue, include a 'suggestion' field quoting the exact "
            "problematic text and providing a rewritten version."
        ),
        output_format=(
            '{"score": <0-100>, "passed": <true|false>, "issues": ['
            '{"code": "<code>", "severity": "<blocking|warning>", '
            '"message": "<what is wrong, quote text>", '
            '"suggestion": "<how to rewrite it>", '
            '"affected_entity": "<prompt_id>", '
            '"affected_field": "<r|c1|c2|t|o>", '
            '"affected_shot": "<prompt_id>"}]}'
        ),
        output_schema_ref="validation.ValidationReport",
    )


def _reference_usability_validator() -> PromptTemplate:
    return PromptTemplate(
        template_id="reference-usability-v2",
        agent_id="reference-usability-validator",
        version=2,
        role=(
            "You are an art director at a major animation studio. You review "
            "hundreds of reference images daily. You can spot a subject mismatch "
            "across the room and know platform moderation policies."
        ),
        core_task=(
            "Look at the provided reference image and evaluate it:\n\n"
            "1. SUBJECT MATCH (35 pts): Compare the image against the subject "
            "description. Right species, age, clothing, setting?\n\n"
            "2. IMAGE QUALITY (25 pts): Resolution, sharpness, composition, "
            "lighting quality. Is the image usable as reference?\n\n"
            "3. MODERATION SAFETY (20 pts): Check for NSFW content, graphic "
            "violence, hate symbols. Err on the side of caution.\n\n"
            "4. STYLE CONSISTENCY (20 pts): Does art style match the visual "
            "direction? Photorealistic 3D render for an ink-wash project = mismatch."
        ),
        context_template=(
            "{constraints}\n\n" + "SUBJECT DESCRIPTION:\n{subject_description}\n\n"
            "VISUAL STYLE DIRECTION:\n{style_direction}\n\n"
            "REFERENCE STRATEGY:\n{reference_strategy}"
        ),
        constraints=(
            "BLOCKING: wrong subject, too low resolution (< 512px), moderation "
            "concern, completely wrong art style.\n"
            "WARNING: minor subject discrepancies, adequate but not great lighting.\n\n"
            "For every issue, include a 'suggestion' describing what you see in "
            "the image and how to fix the generation prompt."
        ),
        output_format=(
            '{"score": <0-100>, "passed": <true|false>, "issues": ['
            '{"code": "<code>", "severity": "<blocking|warning>", '
            '"message": "<what is wrong, describe what you see>", '
            '"suggestion": "<how to fix the generation prompt>", '
            '"affected_entity": "<character_id or environment_id>", '
            '"affected_field": "<subject|quality|moderation|style>", '
            '"affected_shot": "<reference_id>"}]}'
        ),
        output_schema_ref="validation.ValidationReport",
    )


def _scene_continuity_validator() -> PromptTemplate:
    return PromptTemplate(
        template_id="scene-continuity-v2",
        agent_id="scene-continuity-validator",
        version=2,
        role=(
            "You are a continuity supervisor with experience on 50+ feature films. "
            "You track hair position, clothing wrinkles, prop placement, liquid "
            "levels in glasses, clock hands, and blood spatter. Nothing escapes you."
        ),
        core_task=(
            "Look at the provided sequence of consecutive frames and evaluate "
            "continuity:\n\n"
            "1. CHARACTER APPEARANCE (30 pts): Same character looks the same across "
            "frames. Face, hair, makeup, costume details, body position.\n\n"
            "2. PROP CONTINUITY (25 pts): Objects visible in frame N-1 should be "
            "present in frame N in the same position.\n\n"
            "3. LIGHTING CONSISTENCY (20 pts): Same scene = same lighting direction, "
            "color temperature, quality, and intensity.\n\n"
            "4. WARDROBE CONTINUITY (15 pts): Same scene = same outfit, same fit, "
            "same details. No unexplained changes.\n\n"
            "5. SPATIAL COHERENCE (10 pts): 180-degree rule respected, screen "
            "direction consistent, eyelines match, correct blocking."
        ),
        context_template=(
            "{constraints}\n\n" + "You are viewing {frame_count} consecutive frames.\n\n"
            "CHARACTER DESCRIPTIONS:\n{character_descriptions}\n\n"
            "SCENE DESCRIPTION:\n{scene_descriptions}\n\n"
            "SHOT METADATA:\n{shot_metadata}"
        ),
        constraints=(
            "BLOCKING: character looks like a different person, critical props "
            "disappear, major lighting change within same scene, 180-degree rule "
            "violation, complete outfit change.\n"
            "WARNING: minor prop drift, subtle lighting inconsistencies, small "
            "wardrobe shifts.\n\n"
            "For every issue, include a 'suggestion' referencing which frame has "
            "the problem and which frame shows the correct version."
        ),
        output_format=(
            '{"score": <0-100>, "passed": <true|false>, "issues": ['
            '{"code": "<code>", "severity": "<blocking|warning>", '
            '"message": "<what is wrong, reference specific frames>", '
            '"suggestion": "<what to fix in which frame>", '
            '"affected_entity": "<character_id or prop_name>", '
            '"affected_field": "<appearance|props|lighting|wardrobe|spatial>", '
            '"affected_shot": "<shot_id or frame_index>"}]}'
        ),
        output_schema_ref="validation.ValidationReport",
    )


def _assembly_validator() -> PromptTemplate:
    return PromptTemplate(
        template_id="assembly-v2",
        agent_id="assembly-validator",
        version=2,
        role=(
            "You are a film editor who has cut award-winning features across "
            "drama, action, and documentary. Editing is invisible storytelling — "
            "every cut either serves the emotion or undermines it."
        ),
        core_task=(
            "Review this assembly manifest for narrative quality (technical checks "
            "are handled separately):\n\n"
            "1. NARRATIVE FLOW (30 pts): Does this sequence of clips tell the story "
            "coherently? Any jumps in logic?\n\n"
            "2. TRANSITION APPROPRIATENESS (25 pts): Hard cut for action, dissolve "
            "for passage of time, fade for ending. Right choice for the beat?\n\n"
            "3. PACING (25 pts): Does the rhythm vary appropriately? Fast cuts for "
            "tension, longer holds for contemplation.\n\n"
            "4. EMOTIONAL ARC (20 pts): Does the emotional journey come through? "
            "Rising tension, turning points, release."
        ),
        context_template=(
            "{constraints}\n\n" + "ASSEMBLY MANIFEST:\n{assembly_manifest}\n\n"
            "SHOT BIBLE:\n{shot_bible}\n\n"
            "STORY STRUCTURE:\n{story_structure}\n\n"
            "TARGET RUNTIME: {target_runtime_seconds}s\n"
            "ACTUAL RUNTIME: {actual_runtime}s"
        ),
        constraints=(
            "BLOCKING: narrative jump making no logical sense, completely wrong "
            "transition for emotional beat, missing critical story beat.\n"
            "WARNING: pacing feels off, transition could be better.\n\n"
            "For every issue, include a 'suggestion' with which clip/transition "
            "to change and what to change it to."
        ),
        output_format=(
            '{"score": <0-100>, "passed": <true|false>, "issues": ['
            '{"code": "<code>", "severity": "<blocking|warning>", '
            '"message": "<what is wrong>", '
            '"suggestion": "<specific edit change>", '
            '"affected_entity": "<clip_id or transition_id>", '
            '"affected_field": "<clip_order|transition_type|timing>", '
            '"affected_shot": "<shot_id>"}]}'
        ),
        output_schema_ref="validation.ValidationReport",
    )


def _delivery_completeness_validator() -> PromptTemplate:
    return PromptTemplate(
        template_id="delivery-completeness-v2",
        agent_id="delivery-completeness-validator",
        version=2,
        role=(
            "You are a post-production supervisor responsible for final delivery "
            "QC. Before any project goes to the client, you review every file. "
            "You have caught missing credits at 2am and corrupt video files that "
            "passed automated checks."
        ),
        core_task=(
            "Review this delivery package for production readiness (automated "
            "file-existence checks are handled separately):\n\n"
            "1. PRODUCTION READINESS (60 pts): Do file sizes look reasonable? "
            "A 12KB 'final_video.mp4' is not a real video. Do extensions match "
            "content? Any temp files (.tmp, .draft, WIP markers)?\n\n"
            "2. NAMING & ORGANIZATION (40 pts): Clear, descriptive file names? "
            "Not 'output_final_v3.mp4'. Logical package structure?"
        ),
        context_template=(
            "{constraints}\n\n" + "DELIVERY MANIFEST:\n{delivery_manifest}\n\n"
            "FILE LISTING:\n{file_listing}\n\n"
            "PROJECT METADATA:\n{project_metadata}"
        ),
        constraints=(
            "BLOCKING: suspicious file sizes (video < 1MB), wrong file format, "
            "temp/draft files in delivery package.\n"
            "WARNING: unclear file names, flat structure.\n\n"
            "For every issue, include a 'suggestion' with the exact file path "
            "and what to rename/reorganize."
        ),
        output_format=(
            '{"score": <0-100>, "passed": <true|false>, "issues": ['
            '{"code": "<code>", "severity": "<blocking|warning>", '
            '"message": "<what is wrong, reference file>", '
            '"suggestion": "<rename to X, move to Y, regenerate Z>", '
            '"affected_entity": "<filename>", '
            '"affected_field": "<filename|format|size|location>", '
            '"affected_shot": "<filename>"}]}'
        ),
        output_schema_ref="validation.ValidationReport",
    )
