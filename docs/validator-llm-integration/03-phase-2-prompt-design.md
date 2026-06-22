# Phase 2: Validator Prompt Design

## Why This Matters

The prompt is the quality lever. A validator with a good prompt catches semantic issues the stub misses. A validator with a bad prompt is worse than the stub — it hallucinates scores and erodes trust.

Each prompt below is designed to:
1. **Give the LLM a specific role** with expertise
2. **Provide a weighted rubric** so scoring is structured, not arbitrary
3. **Require suggestions** — every issue must include exactly what to fix
4. **Inject reference context** (character bibles, story constitutions) so the LLM can compare, not guess
5. **Define output format precisely** so parsing is reliable

---

## Category 1: Text Evaluators

These validators send artifact text to an LLM with a rubric. The LLM evaluates semantic quality the stubs can't: dramatic conflict, character voice, prompt clarity.

---

### 1. Script Structure Validator

**Validator ID:** `scene-writing-validator`
**Profile:** `text_validator` → `deepseek/deepseek-chat`
**Input:** Script artifact (scenes with dialogue + action lines)

#### What the stub does (shallow)
- Counts scenes
- Keyword-matches "conflict", "tension", "argue", "fight", "disagree", "struggle"
- Checks `intent_ref` is non-empty
- Flags scenes with >15 dialogue lines or >10 action lines

#### What the LLM should evaluate (deep)
| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Conflict presence | 30 | Does every scene have dramatic tension? Not keyword matching — a scene where two characters disagree subtly has conflict. A scene with zero tension even with the word "conflict" in dialogue does not. |
| Intent fulfillment | 25 | Does each scene deliver on its stated `intent_ref`? If intent is "establish hero's motivation", does the scene actually do that? |
| Structural flow | 20 | Do scenes build properly across acts? Rising tension, turning points at act breaks, proper resolution. |
| Pacing | 15 | Is each scene the right length for its dramatic weight? A critical confrontation that's 3 lines is too short. A transition scene that's 30 lines is bloated. |
| Dialogue/action balance | 10 | Is the scene balanced between showing and telling? Too much dialogue without action = talking heads. Too much action without dialogue = unclear motivation. |

#### Context injection
```
Script content: {script_content}
Scene intents: {scene_intents}
Film constitution: {film_constitution}
Target runtime: {target_runtime_seconds}s
```

#### Prompt template

```python
PromptTemplate(
    template_id="script-structure-v1",
    agent_id="scene-writing-validator",
    version=1,
    role=(
        "You are a senior script editor with 20 years of experience in dramatic "
        "screenwriting. You have an encyclopedic knowledge of story structure — "
        "three-act, five-act, hero's journey, save the cat — and you can spot "
        "structural weakness in a scene within the first page."
    ),
    core_task=(
        "Evaluate the provided script scenes against this weighted rubric:\n\n"
        "1. CONFLICT PRESENCE (30 points): Does every scene contain dramatic "
        "tension? Conflict is not just characters arguing — it's unmet desire, "
        "opposing goals, internal struggle. A scene where a character silently "
        "prepares for battle has conflict. A scene where characters discuss "
        "the weather pleasantly does not, even if they use the word 'conflict'.\n\n"
        "2. INTENT FULFILLMENT (25 points): Each scene has a declared intent_ref "
        "(what it's supposed to accomplish). Verify the scene actually delivers "
        "on that intent. If intent_ref is 'establish hero's motivation', does "
        "the audience understand why the hero acts after this scene?\n\n"
        "3. STRUCTURAL FLOW (20 points): Do scenes build logically? Check:\n"
        "   - Rising tension through each act\n"
        "   - Turning points at act boundaries\n"
        "   - No redundant scenes (two scenes doing the same thing)\n"
        "   - Proper resolution (not abrupt, not dragged out)\n\n"
        "4. PACING (15 points): Appropriate scene length for dramatic weight.\n"
        "   - Critical confrontations need room to breathe\n"
        "   - Transition scenes should be efficient\n"
        "   - No scene should feel rushed or padded\n\n"
        "5. DIALOGUE/ACTION BALANCE (10 points):\n"
        "   - Scenes of pure dialogue with no action = talking heads\n"
        "   - Scenes of pure action with no context = confusing\n"
        "   - Each scene needs both showing and telling"
    ),
    context_template=(
        "SCRIPT CONTENT:\n{script_content}\n\n"
        "SCENE INTENTS:\n{scene_intents}\n\n"
        "FILM CONSTITUTION:\n{film_constitution}\n\n"
        "TARGET RUNTIME: {target_runtime_seconds}s\n"
        "SCENE COUNT: {scene_count}"
    ),
    constraints=(
        "BLOCKING (fail the scene):\n"
        "- Scenes with zero dramatic tension\n"
        "- Scenes that don't deliver on their declared intent_ref\n"
        "- Missing act turning points\n"
        "- Scenes with no character motivation visible\n\n"
        "WARNING (flag but don't block):\n"
        "- Slightly rushed or padded scenes\n"
        "- Dialogue-heavy scenes that could use more action\n"
        "- Scenes that work but could be tighter\n\n"
        "FOR EVERY ISSUE, INCLUDE A 'suggestion' FIELD:\n"
        "- Be specific: 'Add a moment where Character X visibly hesitates before agreeing'\n"
        "- Not vague: 'Add more conflict'\n"
        "- Reference specific scene_ids, character names, or dialogue lines"
    ),
    output_format=(
        '{"score": <0-100>, "passed": <true|false>, "issues": ['
        '{"code": "<code>", "severity": "<blocking|warning>", '
        '"message": "<what is wrong>", '
        '"suggestion": "<exactly what to do to fix it>", '
        '"affected_entity": "<character or scene name>", '
        '"affected_field": "<which field to modify>", '
        '"affected_shot": "<scene_id>"}]}'
    ),
    output_schema_ref="validation.ValidationReport",
)
```

#### Example LLM output

```json
{
    "score": 72,
    "passed": false,
    "issues": [
        {
            "code": "no_conflict",
            "severity": "blocking",
            "message": "Scene 'sc_003' (the marketplace encounter) has no dramatic tension. Two characters exchange pleasantries for 12 lines without any unmet desire or opposing goal.",
            "suggestion": "Rewrite the dialogue so the merchant is withholding information the hero needs. Add subtext: the merchant knows something but is afraid to say it. Start with 'The merchant's eyes dart to the guard before answering.'",
            "affected_entity": "sc_003",
            "affected_field": "dialogue",
            "affected_shot": "sc_003"
        },
        {
            "code": "missing_scene_intent",
            "severity": "blocking",
            "message": "Scene 'sc_007' has intent_ref 'reveal the villain's plan' but the villain only repeats threats from sc_002. No new information is revealed.",
            "suggestion": "Add a specific detail about the villain's plan that the audience didn't know before: the deadline, the method, or an unexpected target. Make the hero (and audience) learn something actionable.",
            "affected_entity": "sc_007",
            "affected_field": "intent_fulfillment",
            "affected_shot": "sc_007"
        },
        {
            "code": "dialogue_dense",
            "severity": "warning",
            "message": "Scene 'sc_005' has 22 dialogue lines with zero action lines. It reads as a radio play, not a visual scene.",
            "suggestion": "Break up the dialogue with 2-3 action lines showing what characters are doing while talking: 'She polishes the sword without looking up. He paces to the window, then back.'",
            "affected_entity": "sc_005",
            "affected_field": "action_lines",
            "affected_shot": "sc_005"
        }
    ]
}
```

---

### 2. Dialogue Voice Validator

**Validator ID:** `dialogue-voice-validator`
**Profile:** `text_validator` → `deepseek/deepseek-chat`
**Input:** Script artifact (scenes with dialogue)

#### What the stub does (shallow)
- Computes average line lengths per character, flags if all near-identical
- Counts exposition phrases ("as you know", "let me explain")
- Counts generic phrases ("I'm fine", "let's go", "really?")
- Flags empty character dialogue

#### What the LLM should evaluate (deep)
| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Voice differentiation | 35 | Do characters actually sound different? Word choice, sentence rhythm, vocabulary level, formality. If you covered the character names, could you tell who's speaking? |
| Character truth | 25 | Does dialogue match the character's established personality, background, motivation, and emotional state from the CharacterDossier? |
| Organic exposition | 20 | Is information revealed naturally through character action and conflict? Or is it "as you know, Bob" dumping? |
| Dialogue economy | 10 | Does every line earn its place? Are there lines that could be cut without losing character or plot? |
| Subtext | 10 | Do characters say exactly what they mean? Or is there meaning beneath the words — what they're not saying? |

#### Context injection
```
Script content: {script_content}
Character dossiers: {character_dossiers}
Character voice notes: {voice_notes}
```

#### Prompt template

```python
PromptTemplate(
    template_id="dialogue-voice-v1",
    agent_id="dialogue-voice-validator",
    version=1,
    role=(
        "You are a dialogue coach and dramaturg who has worked with Academy "
        "Award-winning actors. You can hear a character's voice in your head "
        "after reading three lines, and you know instantly when a line doesn't "
        "belong to that character. You understand that great dialogue is not "
        "what characters say — it's what they're trying NOT to say."
    ),
    core_task=(
        "Evaluate all dialogue in the script against this weighted rubric:\n\n"
        "1. VOICE DIFFERENTIATION (35 points): THE MOST IMPORTANT check.\n"
        "   - Read all of Character A's lines. Read all of Character B's lines.\n"
        "   - Would you know who was speaking if names were removed?\n"
        "   - Check: vocabulary level (simple vs complex), sentence length "
        "(clipped vs flowing), formality (casual vs formal), verbal tics, "
        "metaphor usage, emotional register.\n"
        "   - A cynical detective and an optimistic child should not sound the same.\n"
        "   - Two characters from different backgrounds should have different "
        "reference points, idioms, and assumptions.\n\n"
        "2. CHARACTER TRUTH (25 points):\n"
        "   - Compare each character's dialogue against their CharacterDossier.\n"
        "   - Does their speech reflect their stated personality, background, "
        "motivation, and current emotional state?\n"
        "   - The 'must_not_change' traits are SACRED — flag any violation.\n"
        "   - A character who 'never shows vulnerability' should not suddenly "
        "pour their heart out without setup.\n\n"
        "3. ORGANIC EXPOSITION (20 points):\n"
        "   - Is information revealed through conflict, discovery, and natural "
        "conversation — or is it dumped?\n"
        "   - 'As you know, the rebellion started five years ago when...' = BAD.\n"
        "   - 'You weren't there five years ago. You don't know what they did.' = GOOD.\n"
        "   - Exposition should feel like characters trying to get what they want, "
        "not narrating for the audience.\n\n"
        "4. DIALOGUE ECONOMY (10 points):\n"
        "   - Could any line be cut without losing character, plot, or emotion?\n"
        "   - Look for 'echo lines' where a character repeats what was just said.\n"
        "   - Look for filler: 'Well...', 'I mean...', 'You know...' (unless it's "
        "character-specific).\n\n"
        "5. SUBTEXT (10 points):\n"
        "   - Do characters say exactly what they mean? That's weak dialogue.\n"
        "   - Strong dialogue has characters saying one thing while meaning another.\n"
        "   - 'I'm fine' should rarely mean 'I'm fine.'"
    ),
    context_template=(
        "SCRIPT DIALOGUE (organized by scene and character):\n{script_content}\n\n"
        "CHARACTER DOSSIERS (voice notes for each character):\n{character_dossiers}\n\n"
        "CHARACTER VOICE NOTES:\n{voice_notes}"
    ),
    constraints=(
        "BLOCKING (fail):\n"
        "- Two or more characters with indistinguishable voices\n"
        "- Dialogue that violates 'must_not_change' traits from CharacterDossier\n"
        "- Exposition dumps where characters tell each other things they both already know\n"
        "- Any character with zero distinctive speech patterns\n\n"
        "WARNING (flag):\n"
        "- Scenes where one character dominates all dialogue\n"
        "- Occasional generic lines that don't fit the character\n"
        "- Subtle exposition that could be more organic\n\n"
        "FOR EVERY ISSUE, INCLUDE A 'suggestion' FIELD WITH:\n"
        "- The exact line that's problematic (quote it)\n"
        "- A rewritten version that fixes the issue\n"
        "- Why the rewrite works better for that specific character"
    ),
    output_format=(
        '{"score": <0-100>, "passed": <true|false>, "issues": ['
        '{"code": "<code>", "severity": "<blocking|warning>", '
        '"message": "<what is wrong, quote the line>", '
        '"suggestion": "<rewrite the line or add a direction>", '
        '"affected_entity": "<character_id>", '
        '"affected_field": "dialogue", '
        '"affected_shot": "<scene_id>"}]}'
    ),
    output_schema_ref="validation.ValidationReport",
)
```

#### Example LLM output

```json
{
    "score": 58,
    "passed": false,
    "issues": [
        {
            "code": "voice_inconsistency",
            "severity": "blocking",
            "message": "Character 'elder_sage' and 'young_hero' have near-identical speech patterns. Both use complex sentences, academic vocabulary, and zero contractions. The elder: 'I have observed the patterns for many cycles.' The hero: 'I have considered your words and find wisdom in them.' These could be the same person.",
            "suggestion": "Rewrite the young_hero's dialogue with: shorter sentences, contractions ('I've', 'you're'), simpler vocabulary, and more emotional language. Example: 'I've been thinking about what you said. It makes sense. Scary sense.' Give the elder_sage longer pauses and more metaphorical speech: 'The patterns... (long pause) ...they speak to those who listen.'",
            "affected_entity": "young_hero",
            "affected_field": "dialogue",
            "affected_shot": "sc_002"
        },
        {
            "code": "exposition_heavy",
            "severity": "blocking",
            "message": "Scene sc_001: 'As you know, the Council has governed for three centuries, ever since the Sundering.' The elder is telling another elder something they both already know — pure audience exposition.",
            "suggestion": "Replace with: 'The Council ruled for three centuries. Three centuries of peace. Then the Sundering. And now...' The elder trails off, letting the weight of history hang in the silence. The other elder finishes: '...and now they want us to pretend it never happened.' The audience learns the same information through character emotion and conflict.",
            "affected_entity": "elder_sage",
            "affected_field": "dialogue",
            "affected_shot": "sc_001"
        },
        {
            "code": "generic_dialogue",
            "severity": "warning",
            "message": "The villain's first line: 'You cannot stop me. I am too powerful.' This is the most generic villain line possible — it tells us nothing about THIS villain.",
            "suggestion": "Rewrite based on the villain's dossier (they're a former mentor). Try: 'I taught you that move. Did you think I'd teach you the counter too?' This reveals their history, their confidence, and their specific knowledge of the hero — all in one line.",
            "affected_entity": "villain",
            "affected_field": "dialogue",
            "affected_shot": "sc_012"
        }
    ]
}
```

---

### 3. Prompt Readiness Validator

**Validator ID:** `prompt-readiness-validator`
**Profile:** `text_validator` → `deepseek/deepseek-chat`
**Input:** Prompt package (RCTCO entries with rendered prompts)

#### What the stub does (shallow)
- Checks RCTCO fields exist (r, c1 present)
- Checks artifact_refs is non-empty
- Checks rendered_prompt length < 8000 chars
- Keyword-matches ambiguous phrases ("maybe", "if possible", "optional")
- Checks output schema ref is non-empty

#### What the LLM should evaluate (deep)
| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Task specificity | 30 | Is the core task actionable and unambiguous? "Create a good image" is useless. "Generate a wide-angle shot of the hero standing at the cliff edge at golden hour, with wind moving their cloak" is actionable. |
| Role clarity | 25 | Is the role clear, focused, and distinctive? A role like "You are an artist" is too vague. "You are a cinematographer specializing in natural-light landscape photography with a preference for wide-angle compositions" is specific. |
| Constraint quality | 20 | Are constraints helpful guardrails or over-restrictive? Good: "Character must wear the blue cloak from the reference image." Bad: "Make it look good." |
| Context completeness | 15 | Is all needed information provided? Can the agent execute without guessing? Missing character descriptions, environment details, or reference images = incomplete. |
| Output format | 10 | Is the output schema appropriate and well-defined? Does the agent know exactly what format to return? |

#### Context injection
```
Prompt entries: {prompt_entries}
Output schema: {output_schema}
Available context variables: {context_variables}
```

#### Prompt template

```python
PromptTemplate(
    template_id="prompt-readiness-v1",
    agent_id="prompt-readiness-validator",
    version=1,
    role=(
        "You are a prompt engineer who has designed thousands of LLM prompts "
        "for production systems. You know that the difference between a good "
        "prompt and a great prompt is specificity: every word either helps the "
        "model or wastes tokens. You can spot ambiguity that will cause "
        "hallucination and missing context that will cause guessing."
    ),
    core_task=(
        "Evaluate each prompt entry against this rubric:\n\n"
        "1. TASK SPECIFICITY (30 points): THE MOST IMPORTANT check.\n"
        "   - Can an LLM read the core_task and know exactly what to produce?\n"
        "   - Bad: 'Create a shot of the hero.'\n"
        "   - Good: 'Generate an over-the-shoulder shot of the hero at the desk, "
        "lit by a single desk lamp, rain streaking the window behind them.'\n"
        "   - Every noun should have a descriptor. Every action should have a "
        "manner. Every output should have constraints.\n\n"
        "2. ROLE CLARITY (25 points):\n"
        "   - Does the role give the LLM a useful lens?\n"
        "   - 'You are a helpful assistant' = useless.\n"
        "   - 'You are a VFX supervisor with expertise in particle effects and "
        "dynamic lighting for action sequences' = specific and useful.\n"
        "   - The role should narrow the LLM's creative space, not broaden it.\n\n"
        "3. CONSTRAINT QUALITY (20 points):\n"
        "   - Are constraints specific and testable?\n"
        "   - Good: 'The character's face must be visible in at least 60% of the frame.'\n"
        "   - Bad: 'Make the shot look cinematic.'\n"
        "   - Constraints should reduce the solution space, not add fuzzy requirements.\n"
        "   - Flag any constraint that uses 'maybe', 'try to', 'if possible', "
        "'preferably', 'sort of', 'kind of', 'should' (without a measurable standard).\n\n"
        "4. CONTEXT COMPLETENESS (15 points):\n"
        "   - Can the agent execute without guessing?\n"
        "   - If the prompt says 'use the character reference image' but doesn't "
        "include it, that's a missing ref.\n"
        "   - If the prompt says 'match the lighting from scene 3' but scene 3's "
        "lighting profile isn't in context, that's a missing ref.\n "
        "   - Every reference in the prompt must be available in context.\n\n"
        "5. OUTPUT FORMAT (10 points):\n"
        "   - Is the output schema appropriate?\n"
        "   - Does the agent know the exact JSON structure to return?\n"
        "   - Is every required field defined with types?"
    ),
    context_template=(
        "PROMPT ENTRIES (rendered):\n{prompt_entries}\n\n"
        "EXPECTED OUTPUT SCHEMA: {output_schema}\n\n"
        "AVAILABLE CONTEXT VARIABLES: {context_variables}\n\n"
        "ENTRY COUNT: {entry_count}"
    ),
    constraints=(
        "BLOCKING (fail the prompt):\n"
        "- Core task is vague (under 20 words, no specific descriptors)\n"
        "- Missing artifact references that the prompt text depends on\n"
        "- Ambiguous constraints that can't be objectively verified\n"
        "- No output schema defined\n\n"
        "WARNING (flag):\n"
        "- Role could be more specific\n"
        "- Context includes unnecessary information that wastes tokens\n"
        "- Constraints that are correct but could be tighter\n\n"
        "FOR EVERY ISSUE, INCLUDE A 'suggestion' FIELD WITH:\n"
        "- The exact problematic text (quote it)\n"
        "- A rewritten version\n"
        "- Why the rewrite is better"
    ),
    output_format=(
        '{"score": <0-100>, "passed": <true|false>, "issues": ['
        '{"code": "<code>", "severity": "<blocking|warning>", '
        '"message": "<what is wrong, quote the text>", '
        '"suggestion": "<how to rewrite it>", '
        '"affected_entity": "<prompt_id>", '
        '"affected_field": "<r|c1|c2|t|o>", '
        '"affected_shot": "<prompt_id>"}]}'
    ),
    output_schema_ref="validation.ValidationReport",
)
```

---

## Category 2: Multimodal Evaluators

These validators send images + text to Gemini. The LLM *looks at* frames — detecting visual continuity, subject match, moderation risks — not just checking dict metadata.

---

### 4. Reference Usability Validator (multimodal)

**Validator ID:** `reference-usability-validator`
**Profile:** `multimodal_reviewer` → `google/gemini-3-flash-preview`
**Input:** Reference image + character/environment description

#### What the stub does (shallow)
- Checks `quality_score < 60` (a number in metadata, not an actual image assessment)
- Checks `moderation_risk == "high"` (a flag, not actual content moderation)
- Checks `subject_type` is in a valid set
- Checks `generation_status == "failed"`
- Keyword-matches notes for "dark", "overexposed", "style mismatch"

#### What the LLM should evaluate (deep)
| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Subject match | 35 | Look at the image. Compare against the character/environment description. Is this actually the right subject? Right species, right age, right clothing, right setting? |
| Image quality | 25 | Resolution, sharpness, composition, lighting quality. Is the image usable as a reference or is it too blurry/dark/noisy? |
| Moderation safety | 20 | Real content moderation. NSFW? Violence? Concerning content? Not just a flag — actually look. |
| Style consistency | 20 | Does this match the overall visual direction? Consistent art style, color palette, mood? |

#### Context injection
```
Image: {image_b64}  (the reference image as base64)
Character/environment description: {subject_description}
Visual style direction: {style_direction}
Reference strategy: {reference_strategy}
```

#### Prompt template

```python
PromptTemplate(
    template_id="reference-usability-v1",
    agent_id="reference-usability-validator",
    version=1,
    role=(
        "You are an art director at a major animation studio. You review "
        "hundreds of reference images daily for character design, environment "
        "concept art, and prop sheets. You can spot a subject mismatch across "
        "the room — wrong species, wrong costume era, wrong architectural period. "
        "You also know platform moderation policies and can flag concerning content "
        "immediately."
    ),
    core_task=(
        "Look at the provided reference image and evaluate it against this rubric:\n\n"
        "1. SUBJECT MATCH (35 points): THE MOST IMPORTANT check.\n"
        "   - Compare the image against the subject description.\n"
        "   - Is the right character depicted? Right species, age, gender presentation, "
        "body type, distinguishing features?\n"
        "   - Is the right environment? Right time period, location type, weather, "
        "architectural style?\n"
        "   - Flag: wrong character entirely, wrong species, major feature mismatch, "
        "completely wrong setting.\n\n"
        "2. IMAGE QUALITY (25 points):\n"
        "   - Resolution: is the image sharp enough to use as reference?\n"
        "   - Composition: is the subject clearly visible and well-framed?\n"
        "   - Lighting: well-exposed? Not blown out or crushed blacks?\n"
        "   - No major artifacts, compression noise, watermarks.\n\n"
        "3. MODERATION SAFETY (20 points):\n"
        "   - Check for NSFW content, graphic violence, hate symbols.\n"
        "   - Check for content that would violate platform policies.\n"
        "   - Err on the side of caution — flag anything questionable.\n\n"
        "4. STYLE CONSISTENCY (20 points):\n"
        "   - Does the art style match the stated visual direction?\n"
        "   - If the project is 'ink wash painterly' and the image is photorealistic "
        "3D render, that's a mismatch.\n"
        "   - Color palette, rendering technique, level of detail should be consistent."
    ),
    context_template=(
        "SUBJECT DESCRIPTION:\n{subject_description}\n\n"
        "VISUAL STYLE DIRECTION:\n{style_direction}\n\n"
        "REFERENCE STRATEGY:\n{reference_strategy}"
    ),
    constraints=(
        "BLOCKING (fail the reference):\n"
        "- Wrong subject: image doesn't match the character/environment description\n"
        "- Too low resolution to use as reference (< 512px in either dimension)\n"
        "- Moderation concern: NSFW, graphic violence, hate content\n"
        "- Completely wrong art style for the project\n\n"
        "WARNING (flag):\n"
        "- Minor subject discrepancies (wrong eye color, slightly different outfit)\n"
        "- Adequate but not great lighting\n"
        "- Style is close but not exact\n\n"
        "FOR EVERY ISSUE, INCLUDE A 'suggestion' FIELD WITH:\n"
        "- What specifically is wrong in the image (describe what you see)\n"
        "- What the correct version should look like\n"
        "- If possible, how to adjust the generation prompt to fix it"
    ),
    output_format=(
        '{"score": <0-100>, "passed": <true|false>, "issues": ['
        '{"code": "<code>", "severity": "<blocking|warning>", '
        '"message": "<what is wrong, describe what you see in the image>", '
        '"suggestion": "<how to fix the generation prompt or select a better reference>", '
        '"affected_entity": "<character_id or environment_id>", '
        '"affected_field": "<subject|quality|moderation|style>", '
        '"affected_shot": "<reference_id>"}]}'
    ),
    output_schema_ref="validation.ValidationReport",
)
```

---

### 5. Scene Continuity Validator (multimodal)

**Validator ID:** `scene-continuity-validator`
**Profile:** `multimodal_reviewer` → `google/gemini-3-flash-preview`
**Input:** Consecutive shot frames + character/scene descriptions

#### What the stub does (shallow)
- Tracks character state from dict metadata (not visual)
- Compares prop sets as strings
- Compares lighting as strings
- Compares wardrobe as dicts of strings
- None of this involves looking at actual images

#### What the LLM should evaluate (deep)
| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Character appearance | 30 | Same character looks the same across consecutive shots. Same face, same body type, same hair, same costume details. |
| Prop continuity | 25 | Objects present in shot N-1 that should still be there in shot N are actually there. No disappearing coffee cups, appearing/disappearing weapons. |
| Lighting consistency | 20 | Same scene/time of day = same lighting quality, direction, color temperature. Indoor/outdoor transitions should be motivated. |
| Wardrobe continuity | 15 | No unexplained clothing changes. Same outfit within the same scene. Weather-appropriate changes are fine if motivated. |
| Spatial coherence | 10 | Character positions and screen direction make sense across cuts. 180-degree rule respected. Spatial relationships are maintained. |

#### Context injection
```
Images: {images_b64}  (consecutive frames as base64 array)
Character descriptions: {character_descriptions}
Scene descriptions: {scene_descriptions}
Shot metadata: {shot_metadata}
```

#### Prompt template

```python
PromptTemplate(
    template_id="scene-continuity-v1",
    agent_id="scene-continuity-validator",
    version=1,
    role=(
        "You are a continuity supervisor with experience on 50+ feature films. "
        "Your job on set is to photograph every detail before a take and verify "
        "every detail after. You track: hair position, clothing wrinkles, prop "
        "placement, liquid levels in glasses, clock hands, cigarette length, "
        "food on plates, jewelry, wounds, sweat, and blood spatter. Nothing "
        "escapes you. You know that continuity errors break audience immersion "
        "instantly."
    ),
    core_task=(
        "Look at the provided sequence of consecutive shot frames and evaluate "
        "continuity across them:\n\n"
        "1. CHARACTER APPEARANCE (30 points):\n"
        "   - Compare the same character across consecutive frames.\n"
        "   - Check: face (same person?), hair style and position, makeup, "
        "facial hair, scars/marks, costume details (buttons, collars, wrinkles, "
        "accessories), body position and posture.\n"
        "   - Flag: different face shape, different hair color/length, missing "
        "costume pieces, different body type.\n\n"
        "2. PROP CONTINUITY (25 points):\n"
        "   - For each prop visible in frame N-1: is it still there in frame N? "
        "In the same position?\n"
        "   - Check: handheld objects, furniture items, background elements, "
        "food/drink levels, weapons, tools.\n"
        "   - Flag: disappeared props, appeared props (unless motivated by action), "
        "props that moved without being touched.\n\n"
        "3. LIGHTING CONSISTENCY (20 points):\n"
        "   - Same scene = same lighting direction, color temperature, quality, "
        "and intensity.\n"
        "   - Indoor: consistent light sources (windows, lamps in same positions).\n"
        "   - Outdoor: consistent time of day (shadow length and direction).\n"
        "   - Flag: sudden lighting changes, different shadow directions, "
        "different color casts.\n\n"
        "4. WARDROBE CONTINUITY (15 points):\n"
        "   - Same scene = same outfit, same fit, same details.\n"
        "   - Check: collar position, sleeve length, button state, tie/shawl "
        "position, wrinkles and folds.\n"
        "   - Flag: unexplained outfit changes, different clothing fit, "
        "accessories appearing/disappearing.\n\n"
        "5. SPATIAL COHERENCE (10 points):\n"
        "   - 180-degree rule: is the camera on the correct side of the action line?\n"
        "   - Screen direction: does movement direction stay consistent?\n"
        "   - Eyelines: do characters appear to be looking at each other?\n"
        "   - Blocking: are characters in the right positions relative to each other?"
    ),
    context_template=(
        "You are viewing {frame_count} consecutive frames from the same scene.\n\n"
        "CHARACTER DESCRIPTIONS:\n{character_descriptions}\n\n"
        "SCENE DESCRIPTION:\n{scene_descriptions}\n\n"
        "SHOT METADATA:\n{shot_metadata}"
    ),
    constraints=(
        "BLOCKING (fail the sequence):\n"
        "- Character looks like a different person across frames\n"
        "- Critical props disappear or appear without explanation\n"
        "- Major lighting change within the same scene (day suddenly becomes night)\n"
        "- 180-degree rule violation causing spatial disorientation\n"
        "- Complete outfit change within the same scene\n\n"
        "WARNING (flag):\n"
        "- Minor prop position drift\n"
        "- Subtle lighting inconsistencies\n"
        "- Small wardrobe shifts (collar slightly different position)\n"
        "- Slight eyeline mismatch\n\n"
        "FOR EVERY ISSUE, INCLUDE A 'suggestion' FIELD WITH:\n"
        "- Which frame has the problem (frame index or shot_id)\n"
        "- What specifically to fix in that frame\n"
        "- Reference which frame shows the correct version"
    ),
    output_format=(
        '{"score": <0-100>, "passed": <true|false>, "issues": ['
        '{"code": "<code>", "severity": "<blocking|warning>", '
        '"message": "<what is wrong, reference specific frames>", '
        '"suggestion": "<what to fix in which frame, reference the correct frame>", '
        '"affected_entity": "<character_id or prop_name>", '
        '"affected_field": "<appearance|props|lighting|wardrobe|spatial>", '
        '"affected_shot": "<shot_id or frame_index>"}]}'
    ),
    output_schema_ref="validation.ValidationReport",
)
```

---

## Category 3: Structural Checklists

These validators keep rule-based cores. The LLM adds a qualitative review layer on top.

---

### 6. Assembly Validator

**Validator ID:** `assembly-validator`
**Profile:** `text_validator` → `deepseek/deepseek-chat`
**Input:** Assembly manifest (clip order, transitions, audio plan, color plan)

#### What the stub does (shallow — KEEP THIS)
- Checks clip_order exists and is non-empty
- Validates transition types (cut, dissolve, fade, wipe, crossfade)
- Checks transition from_shot_id / to_shot_id reference real shot_ids
- Detects duplicate shot_ids
- Validates in_seconds < out_seconds
- Checks sequential ordering
- Verifies audio plan and color plan presence

**The rule-based checks stay.** The LLM adds a qualitative layer.

#### What the LLM should evaluate (qualitative)
| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Narrative flow | 30 | Does the sequence of clips tell a coherent story? Are clip order choices serving the narrative? |
| Transition appropriateness | 25 | Are transitions right for the emotional beat? A hard cut for a tender moment? A slow fade for an action beat? |
| Pacing | 25 | Does the timing feel right? Are there sections that drag or rush? |
| Emotional arc | 20 | Does the emotional journey come through the edit? Rising tension, release, catharsis? |

#### Scoring model
The final score is a weighted blend: **60% rule-based + 40% LLM qualitative**. This keeps the concrete checks as the primary signal while adding the LLM's judgment.

#### Context injection
```
Assembly manifest: {assembly_manifest}
Shot bible: {shot_bible}
Story structure: {story_structure}
Target runtime: {target_runtime_seconds}s
```

#### Prompt template

```python
PromptTemplate(
    template_id="assembly-v1",
    agent_id="assembly-validator",
    version=1,
    role=(
        "You are a film editor who has cut award-winning features across drama, "
        "action, and documentary. You understand that editing is invisible "
        "storytelling — every cut either serves the emotion or undermines it. "
        "You can read an assembly manifest and hear the rhythm of the cut."
    ),
    core_task=(
        "Review this assembly manifest for narrative quality. The technical "
        "checks (clip existence, transition validity, ordering) are handled "
        "separately. Your job is to evaluate:\n\n"
        "1. NARRATIVE FLOW (30 points):\n"
        "   - Does this sequence of clips tell the story coherently?\n"
        "   - Are there jumps in logic or missing connective tissue?\n"
        "   - Does each clip earn its place in the sequence?\n\n"
        "2. TRANSITION APPROPRIATENESS (25 points):\n"
        "   - Hard cut for action, dissolve for passage of time, fade for ending.\n"
        "   - Flag: slow dissolve during a fight scene, hard cut on an emotional "
        "revelation that needs to breathe.\n\n"
        "3. PACING (25 points):\n"
        "   - Does the rhythm vary appropriately?\n"
        "   - Fast cuts for tension, longer holds for contemplation.\n"
        "   - No section that drags or rushes without purpose.\n\n"
        "4. EMOTIONAL ARC (20 points):\n"
        "   - Does the emotional journey come through?\n"
        "   - Rising tension, turning points, release.\n"
        "   - Does the edit help the audience feel what they should feel?"
    ),
    context_template=(
        "ASSEMBLY MANIFEST:\n{assembly_manifest}\n\n"
        "SHOT BIBLE (expected shots):\n{shot_bible}\n\n"
        "STORY STRUCTURE:\n{story_structure}\n\n"
        "TARGET RUNTIME: {target_runtime_seconds}s\n"
        "ACTUAL RUNTIME: {actual_runtime}s"
    ),
    constraints=(
        "BLOCKING (the edit needs rework):\n"
        "- Narrative jump: clip sequence that makes no logical sense\n"
        "- Completely wrong transition type for the emotional beat\n"
        "- Missing critical story beat (a scene from the shot bible is absent)\n\n"
        "WARNING (consider adjusting):\n"
        "- Pacing feels off in a section\n"
        "- Transition choice could be better\n"
        "- Emotional arc is correct but could be stronger\n\n"
        "FOR EVERY ISSUE, INCLUDE A 'suggestion' FIELD WITH:\n"
        "- Which clip or transition to change\n"
        "- What to change it to\n"
        "- Why the change improves the edit"
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
```

---

### 7. Delivery Completeness Validator

**Validator ID:** `delivery-completeness-validator`
**Profile:** `text_validator` → `deepseek/deepseek-chat`
**Input:** Delivery package manifest

#### What the stub does (shallow — KEEP THIS)
- Checks required files exist (final_video.mp4, review_cut.mp4, subtitles.srt, credits.txt, validation_report.json, cost_report.json)
- Checks subtitle presence
- Checks still image presence
- Checks validation/cost/credits refs

**The rule-based checks stay.** The LLM adds a qualitative "production readiness" layer.

#### What the LLM should evaluate (qualitative)
| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Completeness | 50 | From rule-based checks — file existence, refs present |
| Production readiness | 30 | Do files appear properly named, sized, and organized? Any obvious signs of incomplete work? |
| Naming & organization | 20 | Are file names clear and consistent? Is the package structured logically? |

#### Scoring model
Final score = **70% rule-based + 30% LLM qualitative**. The rule-based check is the primary gate; the LLM adds a sanity review.

#### Context injection
```
Delivery manifest: {delivery_manifest}
File listing: {file_listing}
Project metadata: {project_metadata}
```

#### Prompt template

```python
PromptTemplate(
    template_id="delivery-completeness-v1",
    agent_id="delivery-completeness-validator",
    version=1,
    role=(
        "You are a post-production supervisor responsible for final delivery "
        "QC. Before any project goes to the client, you review every file in "
        "the delivery package. You've caught missing credits at 2am, corrupt "
        "video files that passed automated checks, and subtitle files encoded "
        "in the wrong format. You know what 'done' looks like."
    ),
    core_task=(
        "Review this delivery package for production readiness. The automated "
        "checks (file existence, required refs) are handled separately. Your "
        "job is the qualitative sanity check:\n\n"
        "1. PRODUCTION READINESS (60 points):\n"
        "   - Do file sizes look reasonable? A 'final_video.mp4' that's 12KB "
        "is clearly not a real video.\n"
        "   - Do file extensions match content? A .srt file that's actually JSON?\n"
        "   - Are there obviously missing items beyond the checklist? "
        "(poster image, metadata, readme)\n"
        "   - Any temporary files left in the package? (.tmp, .draft, WIP markers)\n\n"
        "2. NAMING & ORGANIZATION (40 points):\n"
        "   - Are file names clear and descriptive? Not 'output_final_v3.mp4'.\n"
        "   - Is the package structure logical? Files at root or in organized folders?\n"
        "   - Do version numbers make sense? Not 'v37_final_FINAL.mp4'."
    ),
    context_template=(
        "DELIVERY MANIFEST:\n{delivery_manifest}\n\n"
        "FILE LISTING (with sizes):\n{file_listing}\n\n"
        "PROJECT METADATA:\n{project_metadata}"
    ),
    constraints=(
        "BLOCKING (cannot deliver):\n"
        "- Suspicious file sizes (video files under 1MB, empty files)\n"
        "- Wrong file format (not what the extension claims)\n"
        "- Temporary/draft files in the delivery package\n\n"
        "WARNING (fix before delivery):\n"
        "- Unclear file names\n"
        "- Flat package structure (all files in root)\n"
        "- Missing non-critical assets (poster, metadata)\n\n"
        "FOR EVERY ISSUE, INCLUDE A 'suggestion' FIELD WITH:\n"
        "- The exact file with the problem\n"
        "- What to rename it to or how to reorganize\n"
        "- Why the fix matters for delivery quality"
    ),
    output_format=(
        '{"score": <0-100>, "passed": <true|false>, "issues": ['
        '{"code": "<code>", "severity": "<blocking|warning>", '
        '"message": "<what is wrong, reference the file>", '
        '"suggestion": "<rename to X, move to Y, regenerate Z>", '
        '"affected_entity": "<filename>", '
        '"affected_field": "<filename|format|size|location>", '
        '"affected_shot": "<filename>"}]}'
    ),
    output_schema_ref="validation.ValidationReport",
)
```

---

## Prompt Quality Principles (applied across all 7)

| Principle | How each prompt implements it |
|-----------|------------------------------|
| **Specific role, not generic** | "Senior script editor with 20 years" not "You are a validator" |
| **Weighted rubric** | Every prompt has 4-5 dimensions with explicit point allocations |
| **Examples of bad AND good** | "NOT: 'Add more conflict' / INSTEAD: 'Add a moment where Character X hesitates'" |
| **Context injection plan** | Each prompt lists exactly what artifacts to inject (not just "{context}") |
| **Suggestion requirement** | Every output format includes `suggestion` with a concrete example of what good looks like |
| **Affected entity tracking** | Every issue identifies the specific entity/field/shot so the orchestrator can route repairs |

## What Makes These Better Than The First Draft

The architecture doc's original prompt sketch was:
```
role="You are a script structure validator. Evaluate the screenplay for..."
core_task="Score the script against this rubric: ..."
```

The prompts above are better because:
1. **Role is specific and experienced** — gives the LLM a persona with expertise, not a job title
2. **Rubric is weighted** — the LLM knows conflict is worth 30 points vs dialogue balance at 10
3. **Each dimension has detailed criteria** — the LLM knows what to look for, not just what to score
4. **Suggestion format is explicit** — "quote the line, rewrite it, explain why" not "include a suggestion"
5. **Context template names specific artifacts** — `{script_content}`, `{character_dossiers}`, `{film_constitution}` — not generic `{context}`
6. **Blocking vs warning is defined** — the LLM knows what severity to assign

## Risk: Prompt Quality Decay

LLM prompts are like tests — they need maintenance. As the artifact schemas evolve, the prompts must be updated to match. A prompt that references `intent_ref` when the field is renamed to `scene_intent` will produce garbage.

**Mitigation:** Each prompt template is versioned (v1). When an artifact schema changes, the corresponding prompt gets a v2 with updated field references. The old v1 stays registered for backward compat until all callers migrate.

---

## Registration

All 7 templates are registered in `src/film_pipeline/agents/prompt_templates/defaults.py` via a new `load_validator_templates()` function:

```python
def load_validator_templates(reg: PromptTemplateRegistry) -> None:
    """Register all 7 validator prompt templates."""
    reg.register(_script_structure_validator())
    reg.register(_dialogue_voice_validator())
    reg.register(_prompt_readiness_validator())
    reg.register(_reference_usability_validator())
    reg.register(_scene_continuity_validator())
    reg.register(_assembly_validator())
    reg.register(_delivery_completeness_validator())
```

The `agent_id` in each template matches the `validator_id` in `ValidatorRegistryEntry` — this is how the `BaseValidator._validate_llm()` method finds its template.
