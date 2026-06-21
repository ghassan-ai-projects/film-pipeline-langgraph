# Phase 2 — Structured Prompt Construction (Block-Based)

**Status:** Not started
**Depends on:** Phase 0 (directories, for output context)
**Blocks:** Phase 3 (Gemini review needs structured prompts to validate against), Phase 4 (identity consistency needs CHAR_DESC block)

---

## Goal

Build every reference image prompt from structured, version-locked blocks instead of freeform text hallucinated by the LLM.

## Why

The current prompt chain has two fatal weaknesses:

1. **VisualDevAgent prompt template** shows `"prompt_text": "Create a production-ready character sheet..."` as the example — the model pattern-matches this and produces equally vague prompts.

2. **`_reference_prompt()` fallback** builds `"Create a production-ready {asset_type} for the {subject_type} '{subject_id}'. Photorealistic. No text. No logos."` — no character description, no angle, no expression, no lighting, no camera direction.

3. **`CharacterBible.identity_block` exists but is unused.** It's described as *"Locked descriptive block used in reference-image and video prompts"* — purpose-built for this exact use case.

## Prompt Block Structure

### Character Entries

```
CHAR_DESC + FRAME_ROLE + EXPRESSION + LIGHTING + CAMERA + ID_REINFORCE + GLOBAL_NEGATIVES
```

| Block | Source | Purpose |
|-------|--------|---------|
| `CHAR_DESC` | `CharacterBible.identity_block` | Locked description of the character |
| `FRAME_ROLE` | `ReferenceIndexEntry.frame_role` | Angle: "front face", "3/4 left", "profile right", "full body" |
| `EXPRESSION` | `ReferenceIndexEntry.expression` | "neutral", "frustrated", "tired", "peaceful" |
| `LIGHTING` | `FilmConstitution.visual_language` | "painterly natural light", "golden afternoon" |
| `CAMERA` | `FilmConstitution.camera_philosophy` | "observational, breath-paced" |
| `ID_REINFORCE` | Generated dynamically | "Same person as in all other frames. Consistent facial features." |
| `GLOBAL_NEGATIVES` | Constant | `"No text. No logos. No 2D animation. No cartoon..."` |

### Environment Entries

```
ENV_BASE + ANGLE + LIGHTING + MOOD + CAMERA + ENV_REINFORCE + GLOBAL_NEGATIVES
```

| Block | Source | Purpose |
|-------|--------|---------|
| `ENV_BASE` | FilmConstitution + script scene descriptions | Locked description: geometry, materials, era, key features |
| `ANGLE` | `ReferenceIndexEntry.frame_role` | "wide establishing", "alt angle desk", "detail texture" |
| `LIGHTING` | `ReferenceIndexEntry.lighting` | "cool night", "golden afternoon", "neutral studio" |
| `MOOD` | `FilmConstitution.tone` | "melancholic, painterly", "tense, claustrophobic" |
| `CAMERA` | `FilmConstitution.camera_philosophy` | "observational, breath-paced", "static wide" |
| `ENV_REINFORCE` | Generated dynamically | "Same location across all angles. No characters visible." |
| `GLOBAL_NEGATIVES` | Constant + env addition | Standard negatives + `"No characters visible. No people."` |

## Examples

### Before (current)
```
Create a production-ready character_identity_sheet for the character 'Leo Marchetti'.
Photorealistic. No text. No logos. No watermark.
```

### After (structured — character)
```
A man in his early 40s, Mediterranean features, short dark hair with grey at the temples,
a weathered face with deep-set brown eyes and a faint scar across his left eyebrow.
Medium build, 1.78m, carries tension in his shoulders. Front face, looking directly at
camera. Neutral expression. Painterly natural light, soft key from above-left.
Observational camera, intimate close-up distance. Same person as in all other frames.
Consistent facial features. Same age, same bone structure.

No text. No logos. No 2D animation. No cartoon. No anime. No illustrated style.
Photorealistic only. No other characters visible. No watermarks. No grain.
```

### After (structured — environment)
```
A modern artist's studio, converted warehouse with exposed brick walls, 6-meter ceilings
with steel beams, large north-facing frosted windows. Scuffed hardwood floor.
Paint-splattered workbench along the left wall. Wide establishing shot showing the full
room. Cool night lighting. Melancholic, painterly mood. Observational camera, static wide.
Same location across all angles. Consistent geometry, same furniture placement. No
characters visible.

No text. No logos. No 2D animation. No cartoon. No people. No watermarks. No grain.
```

## Frame-Role-Specific Tuning

### Character Roles

| frame_role | FRAME_ROLE text |
|-----------|----------------|
| `front-face` | "Front face, looking directly at camera. Face centered, well-lit, dominant in frame." |
| `3-4-left` | "Three-quarter angle facing left. Face clearly visible, features recognizable." |
| `3-4-right` | "Three-quarter angle facing right. Face clearly visible, features recognizable." |
| `profile-right` | "Right profile. Clean silhouette, ear and jawline clearly visible." |
| `profile-left` | "Left profile. Clean silhouette, ear and jawline clearly visible." |
| `full-body` | "Full body standing. Entire figure from head to feet visible. Neutral stance." |
| `expression-neutral` | "Neutral expression. Relaxed face, mouth closed, eyes open naturally." |
| `expression-frustrated` | "Frustrated expression. Furrowed brow, tightened jaw, slight tension in mouth." |
| `expression-tired` | "Tired expression. Slightly drooped eyelids, relaxed mouth, subtle exhaustion." |
| `expression-peaceful` | "Peaceful expression. Soft eyes, slight relaxed smile, calm demeanor." |
| `detail-eyes` | "Extreme close-up of eyes. Sharp focus on iris and eyelashes. Both eyes visible." |
| `detail-hands` | "Close-up of hands. Fingers clearly visible, natural resting position." |
| `wardrobe-baseline` | "Full body showing default costume. Clean, unworn state." |

### Environment Roles

| frame_role | ANGLE block text |
|-----------|-----------------|
| `wide-establishing` | "Wide establishing shot showing the full space. This is the canonical view." |
| `alt-angle-desk` | "Alternate angle from desk perspective. Same room, same geometry." |
| `alt-angle-corner` | "Alternate angle from opposite corner. Same room, same furniture placement." |
| `alt-angle-entrance` | "View from the entrance. Same room geometry, confirms entryway." |
| `lighting-cool-night` | "Same wide establishing composition. Cool night lighting." |
| `lighting-golden-afternoon` | "Same wide establishing composition. Golden afternoon light." |
| `lighting-overcast-morning` | "Same wide establishing composition. Overcast morning: soft diffuse light." |
| `detail-texture` | "Extreme close-up of a surface texture. Sharp focus on material detail." |
| `detail-prop` | "Close-up of a key prop in situ. Material and condition readable." |
| `color-palette` | "Flat color swatches arranged as a horizontal strip. Include hex codes." |

## Environment Lighting Variants

Environment boards often need multiple lighting variants of the same wide shot:

1. Use the same `ENV_BASE` block (locked geometry description)
2. Change only the `LIGHTING` block
3. Keep the `ANGLE` block as "wide establishing"
4. Strengthen `ENV_REINFORCE`: "Same location as the canonical wide establishing shot. Identical geometry, identical furniture placement. Only lighting changes."

## Fallback Chains

### Character (no CharacterBible)

1. `FilmConstitution.character_truths` — extract truth for this character
2. `FilmConstitution.visual_language` — for LIGHTING and CAMERA
3. Script/treatment prose — any character descriptions in text
4. Entry `prompt_text` — the LLM-generated description from visual dev phase

### Environment (no EnvironmentBible — no schema exists)

1. Script scene descriptions — headings and action lines describing the location
2. `FilmConstitution.visual_language` — environment-related visual keywords
3. VisualDevAgent entry `prompt_text` — LLM-generated description
4. Entry `notes` — additional context

## Global Negatives (Appended to All Prompts)

```
No text. No logos. No 2D animation. No cartoon. No anime. No illustrated style.
Photorealistic only. No other characters visible. No watermarks. No grain.
```

Environment addition: `"No characters visible. No people."`

## Integration with Identity Consistency (Phase 4)

When Phase 4 generates subsequent frames, the `ID_REINFORCE` block is strengthened:
```
Same person as the anchor frame. Identical facial structure, identical features.
Same age, same bone structure, same skin texture. No variation in identity.
```

## Sources to Load

| Artifact | Phase | What it provides |
|----------|-------|-----------------|
| `character_bible` | visual_dev | `identity_block` — locked character description (character only) |
| `film_constitution` | constitution | `visual_language`, `camera_philosophy`, `tone`, `character_truths` |
| `script` | script | Scene descriptions for environment fallback, character prose |

## Where Prompt Construction Happens

```
generate_reference_images()
  └─ for each entry:
       ├─ load CharacterBible for entry.subject_id (if exists)
       ├─ load FilmConstitution
       ├─ build_structured_prompt(entry, bible, constitution) → structured prompt
       ├─ send to provider
       └─ ...
```

## Files

| File | Action |
|------|--------|
| **NEW** `generation/prompt_builder.py` | `build_structured_prompt()` — handles both character and environment |
| `mcp/tools/__init__.py` | `_reference_prompt()` replaced with `build_structured_prompt()` |
| `schemas/reference.py` | Add `expression: str`, `lighting: str`, `frame_role: str` fields |
| `agents/prompt_templates/defaults.py` | Update visual-dev template for `frame_role`, `expression`, `lighting`, `tier` |
| `agents/impl/visual_dev_agent.py` | Parse new fields from model output |
| `graph/nodes.py` | Add `character_bible_ref` to context_vars |

## Effort

~200 lines. One new file + ~60 lines across 5 files.

## Tests

| Type | What |
|------|------|
| Unit | `build_structured_prompt()` assembles correct blocks from CharacterBible + FilmConstitution |
| Unit | Falls back to constitution.character_truths when no CharacterBible |
| Unit | Frame-role-specific tuning: each role produces correct block text |
| Unit | Global negatives appended to every prompt |
| Unit | Environment: ENV_BASE + ANGLE + LIGHTING + MOOD + ENV_REINFORCE blocks correct |
| Unit | Environment: fallback chain works without EnvironmentBible |
