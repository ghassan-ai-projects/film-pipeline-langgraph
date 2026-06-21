# Reference Image Pipeline — Implementation Plan

> **Date:** 2026-06-21
> **Based on:** `docs/reference-image/gap-analysis.md`
> **Source spec:** `docs/reference-image-generation-and-validation.md` (legacy 9-phase)
> **Constraint:** Sequential generation is fine. No parallel dispatch needed.

---

## Phase 0 — Organize Output Directories

**Goal:** Save generated images into a type+subject hierarchy instead of a flat `sheets/` directory.

**Why:** The legacy spec prescribes `references/characters/CHAR_001/`, `references/environments/ENV_001/`, etc. Flat output makes it impossible to find frames later, breaks the reference index, and prevents composite sheet construction (which expects frames organized by type+subject).

**Target structure:**
```
<project>/references/
├── characters/
│   └── <subject_id>/
│       ├── master-frames/       ← raw provider outputs
│       │   ├── front-face.png
│       │   ├── 3-4-left.png
│       │   └── full-body.png
│       └── validation-report.json
├── environments/
│   └── <subject_id>/
│       └── master-frames/
├── props/
│   └── <subject_id>/
├── style/
├── scale/
├── index/
│   ├── reference-index.json
│   └── reference-validation-summary.json
└── review-packages/
```

**Files to change:**
- `mcp/tools/__init__.py` — `generate_reference_images()`: compute output path as `references/{type}s/{subject_id}/master-frames/{reference_id}.png` instead of `references/sheets/{job_id}.png`
- `schemas/reference.py` — no schema change needed; `asset_path` already stores relative paths

**Naming convention for frames:**
- Use the `reference_id` sanitized (replace `:` with `-`, `/` with `-`) as filename stem
- Append frame type suffix when multiple frames per entry: `{ref_id}-front.png`, `{ref_id}-3-4-left.png`

**Estimated effort:** ~30 lines changed. One file.

---

## Phase 1 — Auto-Heuristic Checks (Per-Frame Validation Stage 1)

**Goal:** Before accepting a generated image, run 5 free checks that catch ~80% of obvious failures.

**Why:** The legacy spec catches broken/corrupt/blank images at $0 cost before any Gemini review. Without this, we accept garbage from the provider and call it "validated."

**Checks:**

| # | Check | Method | Fail If |
|---|-------|--------|---------|
| 1 | File exists | `Path.stat().st_size` | 0 bytes |
| 2 | Min resolution | `PIL.Image.open().size` | < 512×512 |
| 3 | Not corrupt | `PIL.Image.open()` + `.verify()` | Can't open / corrupt |
| 4 | Has content | Color variance (std dev across pixels) | Solid color / all black / all white |
| 5 | Face present | `PIL.Image.open()` — face width >10% of frame | No detectable face (character frames only) |

**Implementation:**
- Check 5 (face detection) is optional for non-character frames — gated on `subject_type == "character"`
- Failed heuristics → mark entry `generation_status = "failed"`, add issue to `entry["issues"]`, skip Gemini review
- Passed heuristics → proceed to Gemini review (Phase 3)

**Files to change:**
- **NEW** `generation/frame_heuristics.py` — module with `run_heuristic_checks(image_path: Path, subject_type: str) -> HeuristicResult`
- `mcp/tools/__init__.py` — `generate_reference_images()`: call `run_heuristic_checks()` after download, before accepting

**Dependencies:** `Pillow` — already in pyproject.toml? Need to verify.

**Estimated effort:** ~60 lines. One new file + ~15 lines changed in tools.

---

## Phase 2 — Structured Prompt Construction (Block-Based)

**Goal:** Build every reference image prompt from structured, version-locked blocks instead of
freeform text hallucinated by the LLM.

**Why:** The current prompt chain has two fatal weaknesses:

1. **VisualDevAgent prompt template** shows `"prompt_text": "Create a production-ready character
   sheet..."` as the example — the model pattern-matches this and produces equally vague prompts.
   The LLM has access to the full script, constitution, and story bible but isn't told to extract
   structured descriptions from them.

2. **`_reference_prompt()` fallback** builds `"Create a production-ready {asset_type} for the
   {subject_type} '{subject_id}'. Photorealistic. No text. No logos."` — no character description,
   no angle, no expression, no lighting, no camera direction. This is what actually gets sent to
   Imagen when the LLM's `prompt_text` is empty.

3. **`CharacterBible.identity_block` exists but is unused.** It's literally described as *"Locked
   descriptive block used in reference-image and video prompts"* — purpose-built for this exact
   use case. Never fed into the prompt chain.

### 2.1 — Prompt Block Structure

Every reference image prompt must be assembled from these blocks (matching the legacy spec):

**Character entries:**
```
CHAR_DESC + FRAME_ROLE + EXPRESSION + LIGHTING + CAMERA + ID_REINFORCE + GLOBAL_NEGATIVES
```

**Environment entries:**
```
ENV_BASE + ANGLE + LIGHTING + MOOD + CAMERA + ENV_REINFORCE + GLOBAL_NEGATIVES
```

### 2.1a — Character Block Table

| Block | Source | Purpose |
|-------|--------|---------|
| `CHAR_DESC` | `CharacterBible.identity_block` | Locked description of the character |
| `FRAME_ROLE` | `ReferenceIndexEntry.frame_role` | Angle/distance: "front face", "3/4 left", "profile right", "full body" |
| `EXPRESSION` | `ReferenceIndexEntry.expression` (new field) | "neutral", "frustrated", "tired", "peaceful" — only for expression entries |
| `LIGHTING` | `FilmConstitution.visual_language` | "painterly natural light", "golden afternoon", "cool night" |
| `CAMERA` | `FilmConstitution.camera_philosophy` | "observational, breath-paced", "intimate close-up" |
| `ID_REINFORCE` | Generated dynamically | "Same person as in all other frames. Consistent facial features. Same age, same bone structure." |
| `GLOBAL_NEGATIVES` | Constant (locked) | `"No text. No logos. No 2D animation. No cartoon. No anime. No illustrated style. Photorealistic only. No other characters visible. No watermarks. No grain."` |

### 2.1b — Environment Block Table

| Block | Source | Purpose |
|-------|--------|---------|
| `ENV_BASE` | `FilmConstitution.visual_language` + script scene descriptions | Locked description of the environment: geometry, materials, era, key features |
| `ANGLE` | `ReferenceIndexEntry.frame_role` | "wide establishing", "alternate angle desk", "alternate angle corner", "detail texture" |
| `LIGHTING` | `ReferenceIndexEntry.lighting` (new field) | "cool night", "golden afternoon", "neutral studio" — environment entries often have multiple lighting variants |
| `MOOD` | `FilmConstitution.tone` | "melancholic, painterly", "tense, claustrophobic" |
| `CAMERA` | `FilmConstitution.camera_philosophy` | "observational, breath-paced", "static wide" |
| `ENV_REINFORCE` | Generated dynamically | "Same location across all angles. Consistent geometry, same furniture placement, same architectural details. No characters visible." |
| `GLOBAL_NEGATIVES` | Constant (locked) | Same as character — `"No text. No logos..."` plus `"No characters visible. No people."` |

### 2.2 — No Character Bible? Fall Back to Constitution

If no `CharacterBible` artifact exists (characters not yet formalized), fall back to:
- `FilmConstitution.character_truths` — extract the truth for this character
- `FilmConstitution.visual_language` — for LIGHTING and CAMERA blocks
- The treatment/script for any character descriptions in prose

### 2.3 — Example: Before vs After

**Before (current):**
```
Create a production-ready character_identity_sheet for the character 'Leo Marchetti'.
Photorealistic. No text. No logos. No watermark. Stable identity.
Useful as a film generation reference anchor.
```

**After (structured):**
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

### 2.4 — Frame-Role-Specific Tuning

Each `frame_role` adds role-specific guidance to the FRAME_ROLE block:

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

### 2.5 — Global Negatives (Constant, Appended to All Prompts)

```
No text. No logos. No 2D animation. No cartoon. No anime. No illustrated style.
Photorealistic only. No other characters visible. No watermarks. No grain.
```

This block is version-locked. If it changes, all previously generated frames are flagged for review.

**Environment addition:** Environment prompts append `"No characters visible. No people."` to the
global negatives block, since environment boards must be clean spatial references.

### 2.6 — Environment Example: Before vs After

**Before (current):**
```
Create a production-ready environment_board for the environment 'Modern Studio'.
Photorealistic. No text. No logos. No watermark. Stable identity.
Useful as a film generation reference anchor.
```

**After (structured):**
```
A modern artist's studio, converted warehouse with exposed brick walls, 6-meter
ceilings with steel beams, large north-facing frosted windows. Scuffed hardwood floor.
Paint-splattered workbench along the left wall, metal shelving with supplies on the
right. Wide establishing shot showing the full room from the entrance. Cool night
lighting, blue ambient through the windows, warm tungsten practicals on the workbench.
Melancholic, painterly mood. Observational camera, static wide position. Same location
across all angles. Consistent geometry, same furniture placement, same architectural
details. No characters visible.

No text. No logos. No 2D animation. No cartoon. No anime. No illustrated style.
Photorealistic only. No other characters visible. No people. No watermarks. No grain.
```

### 2.7 — Environment Frame-Role-Specific Tuning

Each `frame_role` for environments adds role-specific guidance:

| frame_role | ANGLE block text |
|-----------|-----------------|
| `wide-establishing` | "Wide establishing shot showing the full space. Dominant in composition. This is the canonical view that all other angles must be consistent with." |
| `alt-angle-desk` | "Alternate angle from desk perspective. Same room, same geometry, different viewpoint confirming spatial layout." |
| `alt-angle-corner` | "Alternate angle from opposite corner. Same room, same furniture placement, different viewpoint." |
| `alt-angle-entrance` | "View from the entrance. Same room geometry, confirms entryway and spatial flow." |
| `lighting-cool-night` | "Same wide establishing composition. Cool night lighting: blue ambient through windows, warm tungsten practicals, deep shadows in corners." |
| `lighting-golden-afternoon` | "Same wide establishing composition. Golden afternoon light: warm sun through windows, long shadows, dust motes visible in light beams." |
| `lighting-overcast-morning` | "Same wide establishing composition. Overcast morning: soft diffuse light, no sharp shadows, muted colors." |
| `detail-texture` | "Extreme close-up of a surface texture. Sharp focus on material detail — paint splatter, wood grain, brick texture, fabric weave." |
| `detail-prop` | "Close-up of a key prop in situ. Object clearly visible in context, material and condition readable." |
| `color-palette` | "Flat color swatches arranged as a horizontal strip. 3-5 dominant colors from the environment. Include hex codes below each swatch." |

### 2.8 — Environment Lighting Variants

Environment boards often need multiple lighting variants of the same wide shot. The prompt
builder handles this by:

1. Using the same `ENV_BASE` block (locked geometry description)
2. Changing only the `LIGHTING` block
3. Keeping the `ANGLE` block as "wide establishing"
4. Strengthening `ENV_REINFORCE`: "Same location as the canonical wide establishing shot.
   Identical geometry, identical furniture placement. Only lighting changes."

This ensures lighting variants don't accidentally alter the room geometry.

### 2.9 — No Environment Bible? Fall Back Chain

There is no `EnvironmentBible` schema (unlike `CharacterBible`). The `ENV_BASE` block is
assembled from this fallback chain:

1. **Script scene descriptions** — scene headings and action lines describing the location
2. **FilmConstitution.visual_language** — any environment-related visual keywords
3. **VisualDevAgent entry `prompt_text`** — the LLM-generated description from the visual
   dev phase, which had access to the full script and constitution
4. **Entry `notes`** — any additional context from the reference index entry

If none of these provide sufficient detail, the prompt builder logs a warning and uses
the most detailed source available. An environment prompt can never be as empty as the
current `_reference_prompt()` fallback.

### 2.10 — Integration with Identity Consistency (Phase 4)

When Phase 4 generates subsequent frames with seed lock + I2I, the `ID_REINFORCE` block is
strengthened:
```
Same person as the anchor frame. Identical facial structure, identical features.
Same age, same bone structure, same skin texture. No variation in identity.
```

### 2.11 — Sources to Load

The prompt builder needs access to these artifacts (loaded from artifact store):

| Artifact | Phase | What it provides |
|----------|-------|-----------------|
| `character_bible` | visual_dev | `identity_block` — the locked character description (character entries only) |
| `film_constitution` | constitution | `visual_language`, `camera_philosophy`, `tone`, `character_truths` |
| `script` | script | Scene descriptions for environment fallback, character descriptions in prose |

### 2.12 — Where Prompt Construction Happens

In the current flow, prompts are built inside `_reference_prompt()` in `mcp/tools/__init__.py`,
called from `generate_reference_images`. The new flow:

```
generate_reference_images()
  └─ for each entry:
       ├─ load CharacterBible for entry.subject_id (if exists)
       ├─ load FilmConstitution for visual_language + camera_philosophy
       ├─ build_prompt_blocks(entry, bible, constitution) → structured prompt
       ├─ send to provider
       └─ ...
```

**Files to change:**
- **NEW** `generation/prompt_builder.py` — `build_structured_prompt(entry, bible, constitution) -> str` — handles both character and environment block assembly
- `mcp/tools/__init__.py` — `_reference_prompt()` replaced with call to `build_structured_prompt()`
- `schemas/reference.py` — add `expression: str = ""` and `lighting: str = ""` fields to `ReferenceIndexEntry`
- `agents/prompt_templates/defaults.py` — update visual-dev template to produce `frame_role`, `expression`, `lighting`, and `tier` per entry
- `agents/impl/visual_dev_agent.py` — parse `frame_role`, `expression`, `lighting`, `tier` from model output
- `graph/nodes.py` — add `character_bible_ref` to context_vars for visual_dev phase

**Estimated effort:** ~200 lines. One new file + ~60 lines across 5 files.

---

## Phase 3 — Gemini Per-Frame AI Review (Per-Frame Validation Stage 2)

**Goal:** For frames that pass heuristics, run a Gemini Flash review against the legacy rubric.

**Why:** Heuristics catch technical failures. Gemini catches semantic failures — wrong expression, missing subject, artifacts the human eye would see. Per the legacy spec, ~$0.001/frame.

**Rubric (40 pts, threshold ≥28/70%):**

| Domain | Max | Checks |
|--------|-----|--------|
| Subject Present | 10 | Expected subject visible? Face/character clear? |
| Prompt Match | 10 | Expression, position, lighting match prompt? |
| Artifact Freedom | 10 | No deformities, merges, extra anatomy? |
| Technical Quality | 10 | Sharp focus, proper exposure, clean quality? |

**Selective validation (save cost):**

| Frame Type | Gemini Review |
|-----------|---------------|
| Environment wide shots | ❌ Skip |
| Environment lighting variants | ❌ Skip |
| Character front face | ✅ Always |
| Character alt angles | ✅ Spot-check 30% |
| Character expressions | ✅ First 3, then spot-check |
| Detail insets | ❌ Skip |
| Scale reference | ✅ Once |
| Prop views | ✅ Once |

**Implementation:**
- Build Gemini prompt from the legacy template (see Appendix A in gap-analysis spec)
- Call through the existing model adapter (`services.prompt_runner` or direct Gemini client)
- Parse JSON response: `{frame_id, scores: {subject, prompt_match, artifacts, technical}, total, passed, actionable_feedback}`
- Pass (≥28) → `generation_status = "validated"`, record scores
- Fail → `generation_status = "needs_regeneration"`, store actionable_feedback, retry logic (Phase 5)

**Files to change:**
- **NEW** `generation/frame_reviewer.py` — `review_frame(image_path, prompt_text, subject_type) -> FrameReviewResult`
- `mcp/tools/__init__.py` — `generate_reference_images()`: call `review_frame()` after heuristics pass

**Estimated effort:** ~120 lines. One new file + ~20 lines changed in tools.

---

## Phase 4 — Identity Consistency (Seed Lock + I2I)

**Goal:** When generating multiple frames for the same character, enforce visual identity
consistency so all frames show the same person.

**Why:** Independent generation of each frame (front face, 3/4 left, profile, expressions)
produces a different face every time. The resulting composite sheet shows 5 different people
wearing similar clothes — useless as a production reference. The legacy spec solved this with
two mechanisms: seed locking and image-to-image fallback.

**Mechanism 1 — Seed Locking (provider-supported):**
- Imagen 4 supports a `seed` parameter. Same seed + same prompt prefix = same identity.
- Generate the anchor frame (front face) first with a fixed seed.
- All subsequent frames for the same subject use the same seed.
- This is the primary mechanism — zero additional cost.

**Mechanism 2 — Image-to-Image Fallback (when seed alone drifts):**
- If seed-locked generation produces visible identity drift (detected by Gemini review in
  Phase 3 scoring low on "Subject Present"), switch to I2I mode.
- I2I uses the anchor frame as a reference image with strength 0.3–0.5.
- Strength 0.3: strong identity lock, limits angle/expression freedom.
- Strength 0.5: looser identity, allows more variation — default starting point.
- Each subsequent frame call passes the anchor as `reference_images=[anchor_path]`.

**Generation order per character:**
```
1. Generate front face (anchor) — no reference, seed=X
2. Validate anchor (heuristics + Gemini)
3. If anchor fails → retry (max 2, Phase 5)
4. If anchor passes → lock seed=X and anchor_path
5. Generate 3/4 left  — same seed=X, I2I from anchor if seed-drift detected
6. Generate profile   — same seed=X, I2I from anchor if seed-drift detected
7. Generate full body — same seed=X, I2I from anchor if seed-drift detected
8. Generate expressions — same seed=X, I2I from anchor if seed-drift detected
9. Validate each subsequent frame (heuristics + Gemini)
10. Retry any failing frames (Phase 5)
```

**Seed drift detection:**
- After generating a subsequent frame, run Gemini per-frame review (Phase 3).
- If `scores.subject < 7/10` with actionable feedback like "different face" or "identity
  inconsistent" → flag as seed drift.
- On first drift: retry with same seed (provider jitter).
- On second drift: switch to I2I with strength 0.5.
- On third drift with I2I: switch to I2I with strength 0.3 (strong lock).
- If still drifting: accept best attempt, tag `identity_unclear`, flag for human review.

**Data to track per subject group:**
```python
identity_state = {
    "anchor_frame_path": Path,      # path to locked front face
    "anchor_seed": int,             # seed used for anchor
    "i2i_active": bool,             # whether I2I fallback is in use
    "i2i_strength": float,         # current I2I strength (0.3–0.5)
}
```

**Files to change:**
- `mcp/tools/__init__.py` — `generate_reference_images()`: group entries by subject_id,
  generate anchor first, pass seed + reference_images to provider for subsequent frames
- `providers/adapters/imagen4_gemini.py` — verify `build_payload()` accepts `seed` and
  `reference_images` parameters (may need updates)
- `providers/base.py` — verify `build_payload()` signature supports seed + reference_images
- `generation/frame_reviewer.py` — detect seed drift from Gemini review scores

**Estimated effort:** ~100 lines. Mostly in `generate_reference_images` loop restructuring.

---

## Phase 5 — Retry Logic

**Goal:** On validation failure, retry up to 2 times with specific fixes, then use best attempt.

**Why:** The legacy spec rule is "max 2 retries per frame, best attempt used after that, flagged for human review. Never block the pipeline."

**Logic:**
```
for attempt in 1..3:
    generate frame
    run heuristics
    if heuristics fail → retry with same prompt (provider glitch)
    run Gemini review
    if score >= 28 → accept, break
    if attempt < 3 → regenerate with actionable_feedback injected into prompt
    if attempt == 3 → accept best attempt, mark human_review_required
```

**Data to track per entry:**
- `retry_count: int`
- `best_score: float`
- `best_attempt: int`
- `actionable_feedback: str` (from last Gemini review)

**Files to change:**
- `schemas/reference.py` — add `retry_count`, `best_score`, `best_attempt` to `ReferenceIndexEntry`
- `mcp/tools/__init__.py` — `generate_reference_images()`: wrap generation in retry loop

**Estimated effort:** ~50 lines. Schema change + loop in tools.

---

## Phase 6 — Provider Tier Routing

**Goal:** Route entries to different provider configs based on a `tier` field.

**Why:** The legacy spec uses 3 tiers:
- **Fast** ($0.02) — bulk frames: environments, expressions, body shots
- **Standard** ($0.05) — critical anchors: hero face, key poses
- **Ultra** ($0.10) — detail insets: eyes, hands, textures

Currently all entries use the same provider. Adding tier routing gives cost control and quality
differentiation.

**Implementation:**
- Add `tier: Literal["fast", "standard", "ultra"] = "fast"` to `ReferenceIndexEntry`
- Update `VisualDevAgent` prompt template to let the model assign tiers
- In `generate_reference_images`, select provider parameters (resolution, quality preset, model variant) based on tier
- For Imagen 4: `fast` = standard quality, `standard` = high quality + seed, `ultra` = max quality + seed + higher resolution

**Files to change:**
- `schemas/reference.py` — add `tier` field
- `agents/impl/visual_dev_agent.py` — parse `tier` from model output
- `agents/prompt_templates/defaults.py` — update visual-dev template to include tier assignment
- `mcp/tools/__init__.py` — `generate_reference_images()`: read tier, adjust provider call

**Estimated effort:** ~40 lines across 4 files.

---

## Phase 7 — Composite Sheet Builder (Character Identity Sheet)

**Goal:** Build the first composite sheet template — Character Identity Sheet — from generated
master frames.

**Why:** This is the biggest single piece of missing value. Individual images are raw provider
outputs. Composite sheets are what downstream video models actually consume as reference anchors.
A Character Identity Sheet with front face (2×), 3/4 angles, profile, full body, expressions,
and detail insets is the minimum viable reference product.

**Template — Character Identity Sheet:**
```
┌──────────────────────────────────────────────────────────────┐
│                  CHARACTER IDENTITY SHEET                     │
│                <subject_id> — <character_name>                │
├──────────┬──────────┬──────────┬──────────┬──────────────────┤
│  FRONT   │  3/4     │  PROFILE │  3/4 ALT │  DETAIL:         │
│  FACE    │  LEFT    │  RIGHT   │          │  Eyes close-up   │
│  (2×)    │          │          │          │                  │
│  640×640 │ 320×320  │ 320×320  │ 320×320  │  DETAIL:         │
├──────────┴──────────┴──────────┴──────────┤  Hands close-up  │
│         FULL BODY FRONT (720×400)          │                  │
├──────────┬──────────┬──────────┬──────────┤                  │
│ NEUTRAL  │ FRUS-    │ TIRED    │ PEACEFUL │                  │
│          │ TRATED   │          │          │                  │
├──────────┴──────────┴──────────┴──────────┴──────────────────┤
│  Labels in margin area (outside tiles) to prevent bleed       │
└──────────────────────────────────────────────────────────────┘
```

**Build rules:**
- Canvas: 2048×2048, white or neutral background
- Grid borders: 1px, #333
- Spacing: 8px between tiles
- Labels: rendered in margin areas only — 12px font, below or beside tiles
- Visual hierarchy: face 2× scale (640×640) > body 1× (720×400) > expressions 0.5× (320×320)
- Tiles are cropped/resized from master frames to fit their grid cells
- Output: `references/characters/<subject_id>/identity-sheet.png`

**Input:** List of master frames with roles:
```python
frames = [
    {"role": "front-face", "path": "master-frames/ref-001-front.png"},
    {"role": "3-4-left", "path": "master-frames/ref-001-3-4-l.png"},
    {"role": "profile-right", "path": "master-frames/ref-001-profile.png"},
    {"role": "full-body", "path": "master-frames/ref-001-body.png"},
    {"role": "expression-neutral", "path": "master-frames/ref-001-expr-neutral.png"},
    ...
]
```

**Implementation:**
- Pure Pillow — `Image.paste()`, `Image.resize()`, `ImageDraw` for borders and labels
- Template function: `build_character_identity_sheet(subject_id, character_name, frames) -> Path`
- Frame roles come from `ReferenceIndexEntry` metadata (new field: `frame_role`)
- If a role is missing, render placeholder (gray with label) — partial sheets are better than nothing

**Files to change:**
- **NEW** `generation/compositor.py` — `build_character_identity_sheet()`, shared helpers
- `schemas/reference.py` — add `frame_role: str = ""` to `ReferenceIndexEntry`
- `agents/prompt_templates/defaults.py` — update visual-dev template to include `frame_role`
- `agents/impl/visual_dev_agent.py` — parse `frame_role` from model output
- `mcp/tools/__init__.py` — `generate_reference_images()`: after generating all frames for a character, call compositor

**Estimated effort:** ~200 lines. One new file + ~30 lines across 4 other files.

---

## Phase 8 — Composite Validation (Sheet-Level Rubrics)

**Goal:** After building a composite sheet, run a Gemini review of the *complete sheet* against
domain-specific rubrics. This is distinct from per-frame validation (Phase 3) — it evaluates the
assembled product, not individual frames.

**Why:** Per-frame validation catches bad frames. Composite validation catches bad *sheets* —
identity drift across tiles, composition problems, contradictory features. The legacy spec found
that sheets passing per-frame checks can still fail as a unit. This gate prevents unusable
references from being locked.

### 6.1 — Character Identity Sheet Rubric (50 pts, threshold ≥40/80%)

| Domain | Max | Checks |
|--------|-----|--------|
| Identity Accuracy | 15 | Same person across all tiles? Age matches? Features consistent? No drift between front/3-4/profile? |
| Expression Fidelity | 10 | Each expression matches its label? No ambiguity? Range is useful for the story? |
| Composition Quality | 10 | Visual hierarchy clear? Largest tile = most important anchor? Labels in margins? Spacing clean? |
| Technical Quality | 10 | No artifacts? Consistent lighting across tiles? Color-matched? Clean edges? |
| Usability as Reference | 5 | Would this stabilize generation across 60+ shots? Is identity unambiguous? |

### 6.2 — Environment Board Rubric (50 pts, threshold ≥40/80%)

| Domain | Max | Checks |
|--------|-----|--------|
| Spatial Consistency | 15 | Same geometry across angles? No new walls/furniture/appearing objects? Layout coherent? |
| Lighting Accuracy | 10 | Lighting matches target? Consistent direction? Shadows believable? |
| Mood Encoding | 10 | Mood matches scene description? Palette consistent? Atmosphere readable? |
| Technical Quality | 10 | No artifacts? Clean composites? Consistent exposure across tiles? |
| Usability as Reference | 5 | Would this stabilize environment across shots? Spatial reference unambiguous? |

### 6.3 — Scale Reference Sheet Rubric (20 pts, threshold ≥16/80%)

| Domain | Max | Checks |
|--------|-----|--------|
| Relative Proportion | 10 | Characters correctly scaled relative to each other? Heights match bible? |
| Context Clarity | 5 | Scale reference bar clear and usable? Increments legible? |
| Technical Quality | 5 | Consistent perspective across all characters? Same ground plane? |

### 6.4 — Style & Color Board Rubric (30 pts, threshold ≥24/80%)

| Domain | Max | Checks |
|--------|-----|--------|
| Palette Clarity | 10 | Palette swatches clear? Hex codes included? Dominant colors identifiable? |
| Mood Encoding | 10 | Visual mood matches film constitution? Texture/light/grain examples coherent? |
| Technical Quality | 5 | Clean layout? No artifacts? Swatches clearly separated? |
| Usability | 5 | Usable as a prompt anchor? Not over-constraining? |

### 6.5 — Prop Sheet Rubric (30 pts, threshold ≥24/80%)

| Domain | Max | Checks |
|--------|-----|--------|
| Object Clarity | 10 | Silhouette clear? Material readable? No ambiguity about what it is? |
| Scale Reference | 10 | In-hand view gives scale? Isolated view shows detail? |
| State Coverage | 5 | Changed/damaged states covered if story-relevant? |
| Technical Quality | 5 | Clean renders? No artifacts? Consistent lighting? |

### 6.6 — Camera Reference Board Rubric (30 pts, threshold ≥24/80%)

| Domain | Max | Checks |
|--------|-----|--------|
| Composition Clarity | 10 | Close-up style readable? Wide-shot composition clear? |
| Movement Mood | 10 | Camera movement intent visible? Lens feeling conveyed? |
| Usability | 10 | Would this stabilize camera grammar across shots? Not over-constraining? |

### Implementation

**Gemini prompt structure (all sheet types):**
```
You are validating an AI-generated reference sheet for film production.
Sheet type: {sheet_type}
Subject: {subject_id}
Prompt used: {prompt_text}

Score against this rubric:
{rubric_domains}

Threshold: {threshold}

Return JSON:
{
  "sheet_id": "",
  "sheet_type": "",
  "scores": {
    "{domain}": {"score": 0, "max": N, "notes": ""}
  },
  "total": 0,
  "passed": false,
  "actionable_feedback": "",
  "failing_tiles": [],
  "bad_reference_tags": []
}
```

**Validation statuses (assigned after review):**

| Status | Meaning | Action |
|--------|---------|--------|
| `approved` | ≥ threshold, no concerns | Lock sheet, register in index |
| `approved_with_notes` | ≥ threshold, minor concerns | Lock sheet, include notes in prompt assembly |
| `needs_delta_fix` | Failed, specific tiles identified | Regenerate only failing tiles (Phase 9) |
| `needs_regeneration` | Failed, no clear tile-level fix | Regenerate entire sheet |
| `human_review_required` | Model uncertain, creative tradeoff | Flag for operator review |
| `rejected` | Harmful or unusable | Do not use |

**Bad reference tags (applied by Gemini when detected):**

| Tag | Meaning |
|-----|---------|
| `too_noisy` | Too many competing subjects |
| `identity_unclear` | Inconsistent face across tiles |
| `geometry_unclear` | Cluttered environment, confused layout |
| `style_conflict` | Strong mismatch with desired output style |
| `moderation_risk` | Contains elements likely to trigger provider filter |
| `low_resolution` | Too small for generation model to read |
| `text_bleed_risk` | Labels encroach on tile content |
| `contradictory` | Conflicting signals (e.g., two different palettes) |

**Multi-model review (for critical anchors):**
- Main character identity sheets → 2+ different models review
- Consensus report preserves disagreements — if model A says beautiful but model B says
  poor for AI continuity, that tension is recorded, not squashed

**Selective composite validation (save cost):**
- Character identity sheets: ✅ Always
- Environment boards: ✅ Always for recurring environments, skip for one-off
- Scale sheets: ✅ Once
- Style boards: ✅ Once
- Prop sheets: ✅ Spot-check 50%
- Camera boards: ✅ Once

**Files to change:**
- **NEW** `generation/sheet_reviewer.py` — `review_composite_sheet(sheet_path, sheet_type, subject_id, prompt_text) -> SheetReviewResult`
- `generation/compositor.py` — `build_character_identity_sheet()` triggers composite validation after build
- `mcp/tools/__init__.py` — wire composite validation into the generation flow

**Estimated effort:** ~180 lines. One new file + ~30 lines across 2 files.

---

## Phase 9 — Delta Regeneration

**Goal:** When composite validation fails with specific tile-level issues, regenerate only the
failing tiles instead of the entire sheet.

**Why:** The legacy spec found 30–40% cost reduction by replacing specific tiles instead of
regenerating entire batches. If the front face is good but the profile angle shows a different
person, you regenerate the profile — not all 12 frames.

**Trigger:** Composite validation (Phase 8) returns `status = "needs_delta_fix"` with
`failing_tiles` populated. Example:
```json
{
  "status": "needs_delta_fix",
  "failing_tiles": ["profile-right", "expression-tired"],
  "actionable_feedback": "Profile angle shows different jaw structure. Tired expression reads as angry."
}
```

**Logic:**
```
1. Parse composite validation report for failing_tiles list
2. For each failing tile:
   a. Look up the source frame in master-frames/
   b. Regenerate that frame with corrected prompt (actionable_feedback injected)
   c. Use same seed + I2I from anchor (identity consistency, Phase 4)
   d. Run per-frame heuristics + Gemini review on regenerated frame
   e. Retry up to 2 times (Phase 5)
3. Rebuild composite sheet with new tiles (Phase 7)
4. Re-run composite validation (Phase 8)
5. Max 3 delta iterations per sheet
6. After 3 iterations, best composite score wins — no blocking
7. Log: "{sheet_name}: best={score}/{max} after {n} delta iterations"
```

**Data to track per sheet:**
```python
delta_state = {
    "delta_iteration": int,        # 1–3
    "best_composite_score": float,
    "best_iteration": int,
    "failing_tiles_history": list[list[str]],  # per-iteration tile lists
}
```

**Files to change:**
- **NEW** `generation/delta_regenerator.py` — `regenerate_failing_tiles(sheet_review, entry_index, project_root) -> list[Path]`
- `generation/compositor.py` — expose `replace_tile(sheet_path, tile_name, new_frame_path) -> Path` for partial rebuild
- `mcp/tools/__init__.py` — wire delta loop after composite validation

**Estimated effort:** ~120 lines. One new file + ~30 lines across 2 files.

---

## Phase 10 — Post-Generation Entry Update

**Goal:** Ensure every generated entry has correct metadata after generation completes.

**Why:** Currently `generate_reference_images` sets some fields inline (quality_score=85,
locked=True, validation status=approved) even when no validation ran. After Phases 1-3,
these values should reflect actual results.

**Fields to update per entry after generation:**
```
entry["asset_path"] = relative path to generated file
entry["provider"] = provider_id
entry["source_frames"] = [relative paths to all generated frames for this entry]
entry["generation_status"] = "validated" | "needs_regeneration" | "failed"
entry["quality_score"] = gemini_score  (or heuristic fallback score)
entry["locked"] = (generation_status == "validated")
entry["validation"] = {status, score, reports}
entry["ai_usability"] = {score, risks, notes}
entry["issues"] = list of issue dicts from heuristics + Gemini
entry["retry_count"] = number of attempts
entry["best_score"] = best Gemini score across attempts
```

**Files to change:**
- `mcp/tools/__init__.py` — `generate_reference_images()`: update entry dict with real values

**Estimated effort:** ~20 lines in tools. No new files.

---

## Phase 11 — Reference Index Persistence

**Goal:** Save the updated reference index after generation, and make `inspect_reference`
return useful data.

**Why:** Already partially done (`_save_reference_index_artifact` exists), but needs to also:
- Write `references/index/reference-index.json` as a human-readable file alongside the artifact store
- Write `references/index/reference-validation-summary.json` summarizing all entry validations
- Update `inspect_reference` to show frame paths, validation scores, and issues

**Files to change:**
- `mcp/tools/__init__.py` — `generate_reference_images()`: write index JSON files to
  `project_root/references/index/`
- `mcp/tools/__init__.py` — `inspect_reference()`: enrich response with frame details

**Estimated effort:** ~30 lines. Two functions in tools.

---

## Dependency Graph

```
Phase 0 (Directories) ──┐
                         ├──→ Phase 1 (Heuristics)
Phase 6 (Tier Routing) ─┘         │
                                   ├──→ Phase 2 (Structured Prompts) ──┐
                                   │         │                          │
                                   │         ├──→ Phase 3 (Per-Frame Gemini Review)
                                   │         │         │
                                   │         │         ├──→ Phase 4 (Identity Consistency: seed lock + I2I)
                                   │         │         │         │
                                   │         │         │         ├──→ Phase 5 (Retry Logic)
                                   │         │         │         │         │
                                   │         │         │         │         ├──→ Phase 7 (Compositor)
                                   │         │         │         │         │         │
                                   │         │         │         │         │         ├──→ Phase 8 (Composite Validation)
                                   │         │         │         │         │         │         │
                                   │         │         │         │         │         │         ├──→ Phase 9 (Delta Regeneration) ──┐
                                   │         │         │         │         │         │         │         │                         │
                                   │         │         │         │         │         │         │         │    (loops back to 7)    │
                                   │         │         │         │         │         │         │         │                         │
                                   │         │         │         │         │         │         │         ├──→ Phase 10 (Entry Update) ←┘
                                   │         │         │         │         │         │         │         │         │
                                   │         │         │         │         │         │         │         │         └──→ Phase 11 (Index Persist)
                                   │         │         │         │         │         │         │         │
                                   └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
                                   (all feed into entry state)
```

Phases 0, 1, and 6 can be done in any order. Phase 2 (Structured Prompts) loads character
bibles and constitution — feeds into Phase 3 (Gemini review needs prompts to validate against)
and Phase 4 (identity consistency needs CHAR_DESC block). Phase 3 requires Phase 1+2. Phase 4
requires Phase 3 (needs Gemini scores to detect drift). Phase 5 requires Phase 3+4. Phase 7
compositor requires Phase 0 (directories) + Phase 4 (identity-consistent frames) + Phase 2
(structured prompts provide context). Phase 8 composite validation requires Phase 7. Phase 9
delta regeneration requires Phase 8 and feeds back into Phase 7. Phase 10 requires 1-9.
Phase 11 requires 10.

---

## Files Summary

| File | Action | Phases |
|------|--------|--------|
| `schemas/reference.py` | Add `tier`, `frame_role`, `expression`, `retry_count`, `best_score`, `best_attempt`, `bad_reference_tags` | 5, 6, 7, 8 |
| `agents/prompt_templates/defaults.py` | Update visual-dev template to produce structured `prompt_text`, `frame_role`, `expression`, `tier` per entry | 2, 6, 7 |
| `agents/impl/visual_dev_agent.py` | Parse `frame_role`, `expression`, `tier` from model output | 2, 6, 7 |
| `graph/nodes.py` | Add `character_bible_ref` to context_vars for visual_dev phase | 2 |
| `mcp/tools/__init__.py` | Rewrite `generate_reference_images` — structured prompts, directories, heuristics, review, identity consistency (seed+I2I), retry, tier, compositor, composite validation, delta regen, entry update, index persist | 0–11 |
| `providers/adapters/imagen4_gemini.py` | Verify/update `build_payload()` for `seed` and `reference_images` params | 4 |
| `providers/base.py` | Verify `build_payload()` signature supports seed + reference_images | 4 |
| **NEW** `generation/frame_heuristics.py` | `run_heuristic_checks()` — 5 Pillow checks | 1 |
| **NEW** `generation/prompt_builder.py` | `build_structured_prompt()` — block-based prompt assembly from bibles | 2 |
| **NEW** `generation/frame_reviewer.py` | `review_frame()` — Gemini Flash per-frame rubric (40 pts) + seed drift detection | 3, 4 |
| **NEW** `generation/compositor.py` | `build_character_identity_sheet()` — Pillow template + composite assembly | 7 |
| **NEW** `generation/sheet_reviewer.py` | `review_composite_sheet()` — Gemini composite rubric (50/30/20 pts by type) | 8 |
| **NEW** `generation/delta_regenerator.py` | `regenerate_failing_tiles()` — tile-level replacement + max 3 iterations | 9 |
| `generation/__init__.py` | Export new modules | 1, 2, 3, 4, 7, 8, 9 |

---

## Tests

Each phase needs tests:

| Phase | Test Type | What to Test |
|-------|-----------|-------------|
| 0 | Unit | `_reference_output_path(entry) -> Path` produces correct directory structure |
| 1 | Unit | Each heuristic check with valid + invalid images (test fixtures) |
| 2 | Unit | `build_structured_prompt()` assembles correct blocks from CharacterBible + FilmConstitution |
| 2 | Unit | Falls back to constitution.character_truths when no CharacterBible exists |
| 2 | Unit | Frame-role-specific tuning: each `frame_role` produces correct ANGLE/EXPRESSION block |
| 2 | Unit | Global negatives appended to every prompt, ID_REINFORCE present when multiple frames |
| 3 | Unit | `review_frame()` parses Gemini JSON response correctly, handles errors |
| 3 | Unit | Selective validation: correct skip/always/spot-check decisions |
| 4 | Unit | Character entries grouped by subject_id, anchor generated first |
| 4 | Unit | Seed passed to provider for subsequent frames, I2I fallback when drift detected |
| 4 | Unit | Seed drift detection: subject score < 7 → flag, retry with same seed → switch to I2I |
| 5 | Unit | Retry loop terminates after max 2 retries, selects best score |
| 5 | Unit | Retry with identity consistency: subsequent frame retries use same seed + I2I from anchor |
| 6 | Unit | Tier → provider parameter mapping (fast/standard/ultra) |
| 7 | Unit | `build_character_identity_sheet()` produces valid PNG of correct dimensions |
| 7 | Unit | Missing frame → placeholder rendered, no crash |
| 8 | Unit | `review_composite_sheet()` parses Gemini composite response for each sheet type |
| 8 | Unit | Each rubric (Character 50pt, Environment 50pt, Scale 20pt, Style 30pt, Prop 30pt, Camera 30pt) scores correctly |
| 8 | Unit | Validation status assigned correctly from score vs threshold |
| 8 | Unit | Bad reference tags parsed from Gemini response |
| 9 | Unit | Delta regenerator parses failing_tiles from composite review, regenerates only listed tiles |
| 9 | Unit | Max 3 delta iterations enforced, best score tracked and selected |
| 9 | Unit | `replace_tile()` swaps a single tile in composite sheet without rebuilding all tiles |
| 0–11 | Integration | `generate_reference_images` with mock provider: full flow with identity consistency + delta regeneration |

For image-based tests (Phases 1, 7), use small synthetic images (e.g., 128×128 solid color)
as fixtures — no need for real generated images.

---

## Design Rules (from Legacy Spec, Preserved)

1. **80% threshold for sheets** — not 90%. Prevents infinite iteration loops.
2. **Labels in margins only** — never over tile content.
3. **Dominant tile 2× scale** — face is the most important anchor.
4. **Image providers, not video providers** — ~18× cheaper.
5. **Selective validation** — skip Gemini for environment variants, detail insets.
6. **Never block the pipeline** — best attempt after max retries, flag for human review.
7. **Stop rule** — more references can make results WORSE.
