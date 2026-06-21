# Reference Image Generation & Validation — Full Pipeline Spec

> **Purpose:** This document captures everything we know about reference image generation and
> validation from our legacy pipeline (The Primordial Stroke) and maps it to what's already
> built in `film-pipeline-langgraph`. Use this as a specification for the coding agent to
> replicate and improve the reference image flow in the new LangGraph project.
>
> **Sources:**
> - `~/ai-projects/skills/reference-image-pipeline/` (legacy skill, superseded)
> - `~/ai-projects/skills/film-production-pipeline/` (unified skill v2.0)
> - `~/ai-movies/the-primordial-stroke/` (actual production data)
> - `~/my-projects/film-pipeline-langgraph/docs/reference-image-flow.md` (existing doc)
> - `~/my-projects/film-pipeline-langgraph/src/` (existing code)

---

## 1. What Reference Images Are & Why They Exist

Reference images are **visual DNA encoding** — structured composite sheets that force the
generation model to maintain consistency across 60–120 shots in a film. They are not concept
art. They are production infrastructure.

### The Core Question Every Reference Must Answer

1. **What must stay the same?** — Face, body, wardrobe, environment geometry, palette
2. **What is allowed to vary?** — Expression, angle, lighting within ranges
3. **What should the model never invent?** — New characters, changed architecture, wrong era

If a reference image does not help answer those three questions, it is decoration, not
production reference.

---

## 2. Reference Types (7 Types)

### 2.1 Character Identity Sheet
*Primary anchor for face/body consistency.*

- Dominant front face (largest tile — 2× scale)
- 3/4 left, 3/4 right, profile angles
- Full body for proportion
- Expression strip (neutral + 3–4 emotions)
- Detail insets: eyes, hands, unique features
- Wardrobe baseline
- Labels in margins (never over tile content)

### 2.2 Costume & State Sheet
*Tracks approved costume variations and story-state changes.*

- Default costume (full body)
- Damaged/changed variants
- Emotional/physical state variants
- Act-specific looks

### 2.3 Environment Board
*Locks location geometry, mood, lighting, materials, palette.*

- Wide establishing shot (dominant)
- 2+ alternate angles confirming geometry
- Lighting variants (cool night / golden afternoon, etc.)
- Texture close-ups
- Color palette strip (3–5 dominant colors + hex codes)
- **No characters** — clean spatial reference

### 2.4 Prop & Object Sheet
*Locks story-critical objects.*

- Clean isolated view
- In-hand scale view
- Damaged/changed state if relevant
- Material detail close-ups

### 2.5 Scale Sheet
*Locks relative proportions across characters and environment.*

- Main characters side-by-side
- Scale marker bars (0.5m increments)
- Key object scale references

### 2.6 Style & Color Board
*Locks visual mood without over-constraining content.*

- Palette swatches
- Texture examples
- Light behavior reference
- Contrast/grain examples

### 2.7 Camera Reference Board
*Shows framing and camera grammar.*

- Close-up style reference
- Wide-shot composition
- Movement mood
- Lens feeling

---

## 3. Pipeline Architecture (9 Phases)

```
PHASE 0: REFERENCE STRATEGY
PHASE 1: PROMPT BLOCK LOCK
PHASE 2: BASE FRAME GENERATION
PHASE 3: PER-FRAME VALIDATION
PHASE 4: COMPOSITE SHEET CONSTRUCTION
PHASE 5: COMPOSITE VALIDATION
PHASE 6: DELTA REGENERATION
PHASE 7: REGISTRATION
PHASE 8: MATRIX & CONTINUITY INTEGRATION
```

### Phase 0 — Reference Strategy

**Inputs:** Film constitution, story bible, character bible, environment bible, camera
language bible, master film matrix, risk register.

**Outputs:** Reference matrix, priority list, provider plan, validation plan, cost estimate.

**Key questions to answer:**
- Which characters need hard identity locking?
- Which environments need geometry locking?
- Which props are story-critical?
- Which scenes are high drift risk?
- Which references may trigger provider moderation?
- Which references are needed before shot bible approval?

### Phase 1 — Prompt Block Lock

Reference prompts must use the **same locked atomic blocks** as video prompts:

```
CHAR_DESC + ANGLE_DESC + EXPRESSION + LIGHTING + CAMERA + ID_REINFORCE + NEGATIVES
ENV_BASE + ANGLE + LIGHTING + MOOD + CAMERA + ENV_REINFORCE + NEGATIVES
```

**Critical rules:**
- All prompt blocks version-locked in reference index BEFORE generation starts
- If CHAR_DESC changes mid-phase, ALL previously generated frames are invalidated
- Global negative prompt appended to ALL prompts:

```
No text. No logos. No 2D animation. No cartoon. No anime. No illustrated style.
Photorealistic only. No other characters visible. No watermarks. No grain.
```

### Phase 2 — Base Frame Generation

**Use image providers, NOT video providers.** This is ~18× cheaper.

**Cost comparison:** 149 base frames
- Video provider (old approach): 149 × $0.90 = **$134.10**
- Image provider: 149 × $0.02–0.05 = **~$3–7.50** — **18-45× cheaper**

**Provider tiers:**

| Tier | Cost/Image | When to Use |
|------|-----------|-------------|
| Fast | $0.02 | Bulk — environments, expressions, body shots |
| Standard | $0.05 | Critical anchor — hero face, key poses |
| Ultra | $0.10 | Detail insets — eyes, hands, textures |

**Generation protocol:**
- Parallel batches (image APIs handle 20+ concurrent easily)
- Square tiles (1024×1024) for consistent composite layout
- Seeds for identity consistency where supported
- I2I fallback for angle consistency (strength 0.3–0.5)
- Ancestor safety filter fallback tiered (museum context → bust-only → best-available)

**Existing code already ported:**
- `providers/factory.py` — provider adapter registry with `Imagen4GeminiProvider`
- `providers/adapters/imagen4_gemini.py` — full Gemini Imagen 4 integration
- `providers/base.py` — `BaseProviderAdapter` ABC (build_payload → submit → poll → download → extract_metadata)
- `providers/mock_image_provider.py` — mock for testing
- Cost: `Imagen4GeminiProvider.estimate_cost()` returns $0.02/$0.05/$0.10 per image

**Still missing (needs build):**
- Batch generation orchestrator (accept list of {prompt, size, seed, tier} → parallel dispatch)
- Frame dedup and best-of-N selection
- Seed drift triage (3 attempts → I2I fallback → manual flag)
- Safety filter fallback for ancestor characters
- Mixing providers per character/environment

### Phase 3 — Per-Frame Validation Gate

Each generated frame passes through two-stage validation BEFORE entering the composite:

**Stage 1 — Automatic Heuristics (free, instant):**

| Check | Method | Fail If |
|-------|--------|---------|
| File exists | `os.path.getsize()` | 0 bytes |
| Min resolution | Pillow `image.size` | < 512×512 |
| Not corrupt | Pillow `Image.open()` | Can't open |
| Has content | Color variance | Solid color / all black / all white |
| Face present | Face width >10% of frame | No face (character frames only) |

These catch ~80% of obvious failures instantly at $0 cost.

**Stage 2 — AI Review (Gemini Flash, ~$0.001/frame):**

| Domain | Max | Checks |
|--------|-----|--------|
| Subject Present | 10 | Expected subject visible? Face/character clear? |
| Prompt Match | 10 | Expression, position, lighting match prompt? |
| Artifact Freedom | 10 | No deformities, merges, extra anatomy? |
| Technical Quality | 10 | Sharp focus, proper exposure, clean quality? |

**Threshold:** ≥28/40 (70%) — pass/filter, not deep review.

**Iteration rules:**
- Pass (≥70%): accepted, moves to composite builder
- Fail with actionable feedback: regenerate with specific fix
- Fail unclear: regenerate with higher tier or different seed
- **Max 2 retries per frame** — best attempt used after that, flagged for human review
- **Never block the pipeline** — a single bad frame doesn't stop everything

**Gemini prompt for per-frame validation:**

```
You are validating an AI-generated reference image for film production.
The image should show: [prompt text].

Score against this rubric (40 pts):
1. SUBJECT (10 pts): Is the expected subject visible? Face/character clear?
2. PROMPT MATCH (10 pts): Does expression/position/lighting match prompt?
3. ARTIFACTS (10 pts): Any deformities, merges, extra anatomy, corruption?
4. TECHNICAL (10 pts): Sharp focus, proper exposure, clean quality?

Threshold: 28/40 (70%).

Return JSON:
{
  "frame_id": "",
  "scores": {
    "subject": {"score": 0, "max": 10, "notes": ""},
    "prompt_match": {"score": 0, "max": 10, "notes": ""},
    "artifacts": {"score": 0, "max": 10, "notes": ""},
    "technical": {"score": 0, "max": 10, "notes": ""}
  },
  "total": 0,
  "passed": false,
  "actionable_feedback": ""
}
```

**Selective validation (save cost):**

| Frame Type | Auto | Gemini |
|-----------|------|--------|
| Environment wide shots | ✅ | ❌ Skip |
| Environment lighting variants | ✅ | ❌ Skip |
| Character front face | ✅ | ✅ Always |
| Character alt angles | ✅ | ✅ Spot-check 30% |
| Character expressions | ✅ | ✅ First 3, then spot-check |
| Detail insets | ✅ | ❌ Skip |
| Scale reference | ✅ | ✅ Once |

**Still missing (needs build):**
- Per-frame validation agent/node
- Gemini integration for AI review
- Auto-heuristic checks (Pillow color variance, face detection)
- Retry logic (max 2 retries, best-available fallback)
- Batch validation orchestration

### Phase 4 — Composite Sheet Construction

**Pre-composite normalization:**
1. Crop all frames to same dimensions (720×720 square tiles)
2. Face-center align for consistent horizontal positioning
3. Color normalize across tiles (same visual color space)
4. Scale consistency (same face-to-frame ratio)

**Layout templates:**

#### Template A — Character Identity Sheet

```
┌──────────────────────────────────────────────────────────────┐
│                  CHARACTER IDENTITY SHEET                     │
│                CHAR_01 — Leo Marchetti                        │
├──────────┬──────────┬──────────┬──────────┬──────────────────┤
│          │          │          │          │                  │
│  FRONT   │  3/4     │  PROFILE │  3/4 ALT │   DETAIL:        │
│  FACE    │  LEFT    │  RIGHT   │          │   Eyes close-up  │
│          │          │          │          │                  │
│  (LARGE) │          │          │          │                  │
│  640×640 │  320×320 │ 320×320 │ 320×320 │  DETAIL:          │
├──────────┴──────────┴──────────┴──────────┤  Hands close-up  │
│                                            │                  │
│         FULL BODY FRONT (720×400)          │                  │
│                                            │                  │
├──────────┬──────────┬──────────┬──────────┤                  │
│ NEUTRAL  │ FRUS-    │ TIRED    │ PEACEFUL │  DETAIL:         │
│          │ TRATED   │          │          │  Paint texture   │
│          │          │          │          │                  │
├──────────┴──────────┴──────────┴──────────┴──────────────────┤
│  Costume alt: clean shirt  |  Height: 1.78m (5'10")         │
│  Labels in margin area (outside tiles) to prevent bleed      │
└──────────────────────────────────────────────────────────────┘
```

#### Template B — Environment Board

```
┌──────────────────────────────────────────────────────────────┐
│                  ENVIRONMENT BOARD                            │
│                ENV_01 — Modern Studio                         │
├────────────────────────────┬─────────────────────────────────┤
│                            │                                  │
│     WIDE ESTABLISHING      │  ALT VIEW — Desk perspective    │
│     (LARGE — 960×540)      │  (540×540)                      │
│                            │                                  │
│     "THE CANONICAL VIEW"   │  ALT VIEW — Corner perspective  │
│                            │  (540×540)                      │
├────────────────────────────┴─────────────────────────────────┤
│  LIGHTING: Cool Night        LIGHTING: Golden Afternoon      │
│  (720×320)                    (720×320)                       │
├──────────────────────────────────────────────────────────────┤
│  DETAIL:       DETAIL:       TEXTURE:      COLOR PALETTE:     │
│  Canvas        Laptop glow   Paint         █ █ █ █ █          │
│  texture       close-up      splatter      #1A1A2E #E94560    │
│                                            #16213E #0F3460    │
└──────────────────────────────────────────────────────────────┘
```

#### Template C — Scale Reference Sheet

```
┌──────────────────────────────────────────────────────────────┐
│                 SCALE REFERENCE SHEET                         │
│          Leo vs Ancestors — Relative Proportions              │
├───────────────────┬──────────────────┬───────────────────────┤
│                   │                  │                        │
│    LEO            │    ARTISAN      │  SCALE MARKER          │
│    1.78m          │    ~1.65m       │  1m | 1.5m | 1.8m     │
│    FULL BODY      │    FULL BODY    │  reference bar         │
│                   │                  │                        │
├───────────────────┼──────────────────┼───────────────────────┤
│    STORYTELLER    │    SHAMAN       │  FIRST PAINTER         │
│    ~1.70m         │    ~1.75m       │  ~1.60m                │
├───────────────────┴──────────────────┴───────────────────────┤
│  Primal: ~1.50m (earliest hominid proportions)               │
│  Scale reference bar with 0.5m increments                   │
└──────────────────────────────────────────────────────────────┘
```

**Build rules:**
- Grid borders: 1–2px
- Spacing: 8px between tiles
- Labels in MARGIN areas ONLY (never on tiles — prevents typography bleed into generation)
- Visual hierarchy: face 2× scale > body 1× > expressions 0.5×
- Output: 2048×2048 (character), 3840×2160 (environment)
- Partial rebuild: `--replace-tile <name> <path>` swaps a single tile without rebuilding entire sheet

**Still missing (needs build):**
- Composite builder agent/node (Pillow/OpenCV image processing)
- Template system (Identity, Costume, Environment, Scale, Prop, Style boards)
- Auto-layout from manifest of frames
- Partial rebuild (delta replacement)
- Color normalization engine
- Label-in-margins typsetting

### Phase 5 — Composite Validation

AI review of the **complete composite sheet** (not just individual tiles).

**Rubric — Character Sheet (50 pts):**

| Domain | Max | Checks |
|--------|-----|--------|
| Identity Accuracy | 15 | Same person across all tiles? Age matches? Features consistent? |
| Expression Fidelity | 10 | Each expression matches label? No ambiguity? |
| Composition Quality | 10 | Visual hierarchy clear? Largest = most important? Labels in margins? |
| Technical Quality | 10 | No artifacts? Consistent lighting? Color-matched? Clean edges? |
| Usability as Reference | 5 | Would this stabilize generation across 60+ shots? |

**Threshold: ≥40/50 (80%)**

**Rubric — Environment Board (50 pts):**

| Domain | Max | Checks |
|--------|-----|--------|
| Spatial Consistency | 15 | Same geometry across angles? No new walls/furniture? |
| Lighting Accuracy | 10 | Lighting matches target? Consistent direction? |
| Mood Encoding | 10 | Mood matches scene description? |
| Technical Quality | 10 | No artifacts? Clean composites? Consistent exposure? |
| Usability as Reference | 5 | Would this stabilize environment across shots? |

**Threshold: ≥40/50 (80%)**

**Rubric — Scale Sheet (20 pts):**

| Domain | Max | Checks |
|--------|-----|--------|
| Relative Proportion | 10 | Characters correctly scaled relative to each other? |
| Context Clarity | 5 | Scale reference bar clear and usable? |
| Technical Quality | 5 | Consistent perspective across all characters? |

**Threshold: ≥16/20 (80%)**

**Validation statuses:**
- `approved` — usable and locked
- `approved_with_notes` — usable but needs careful prompt support
- `needs_delta_fix` — specific tile needs replacement
- `needs_regeneration` — sheet cannot safely guide generation
- `human_review_required` — model judgment uncertain, creative tradeoff exists
- `rejected` — harmful or unusable

**Multi-model review (for critical anchors):**
- Main character identity sheets should get 2+ different models reviewing
- Consensus report preserves disagreements (model A says beautiful, model B says poor for AI continuity — that tension matters)

**Still missing (needs build):**
- Composite validation agent/node
- Gemini prompt + rubric integration
- JSON-structured validation reports
- Multi-model validation orchestration
- Human review package generation

### Phase 6 — Delta Regeneration

On validation failure (< threshold), replace ONLY the failing tiles, not the whole batch.

**Examples:**
- Face drift in side angle → regenerate that side angle only
- Wrong expression → regenerate that expression tile only
- Environment geometry conflict → replace contradictory angle
- Bad label placement → rebuild sheet layout, not image frames

**Rules:**
- Parse Gemini report for specific failing tiles
- Max 3 validation iterations per sheet
- After 3 iterations, best score wins — no blocking
- Script logs: `{sheet_name}: best={score}/{max} after {n} iterations`

**Cost savings:** 30–40% reduction in iteration costs vs full-batch regeneration.

**Still missing (needs build):**
- Delta-regeneration loop logic
- Tile-level failure parsing from validation reports
- Max-iterations enforcement
- Best-score tracking

### Phase 7 — Registration

**File structure:**
```
references/
├── index/
│   ├── reference-index.json
│   └── reference-validation-summary.json
├── characters/
│   └── CHAR_001/
│       ├── identity-sheet.png
│       ├── costume-sheet.png
│       ├── expression-sheet.png
│       ├── master-frames/
│       └── validation-report.json
├── environments/
│   └── ENV_001/
│       ├── environment-board.png
│       ├── lighting-board.png
│       ├── material-details.png
│       ├── master-frames/
│       └── validation-report.json
├── props/
│   └── PROP_001/
│       ├── prop-sheet.png
│       ├── state-variants.png
│       └── validation-report.json
├── style/
│   ├── visual-style-board.png
│   ├── camera-style-board.png
│   └── color-palette.png
├── scale/
│   └── scale-sheet.png
└── review-packages/
    └── reference-review-package-v1.md
```

**Reference Index Core Schema:**

```json
{
  "reference_id": "ref:char:leo:identity:v1",
  "project_id": "project:example",
  "type": "character_identity_sheet",
  "subject_id": "char:leo",
  "path": "references/characters/CHAR_001/identity-sheet.png",
  "source_frames": [],
  "provider": "imagen-fast",
  "prompt_refs": [],
  "approved_for": ["prompt_anchor", "clip_validation", "re_anchor"],
  "not_approved_for": [],
  "validation": {
    "status": "approved",
    "score": 84,
    "reports": []
  },
  "ai_usability": {
    "score": 86,
    "risks": [],
    "notes": ""
  },
  "version": 1,
  "locked": true
}
```

**Existing code already ported:**
- `artifacts/store.py` — ArtifactStore with save/load
- `artifacts/index.py` — ArtifactIndex with lookup/query
- `artifacts/paths.py` — PathTemplate for project paths
- `artifacts/manifest.py` — ArtifactManifest file listing
- `artifacts/metadata.py` — ArtifactMetadata schema (note: needs reference-image-specific fields)
- `artifacts/versioning.py` — Versioning with VERSION slots, MAX_VERSIONS

**Still missing (needs build):**
- Reference-specific metadata schema (reference_id, type, subject_id, approved_for, ai_usability, etc.)
- Validation report storage schema
- Review package generation
- Continuity ledger integration reference

### Phase 8 — Matrix & Continuity Integration

The master film matrix and continuity ledger reference approved images.

Each shot can point to:
- Character sheet
- Environment board
- Prop sheet
- Style board
- Camera board
- Previous frame anchor
- Re-anchor frame

**Still missing (needs build):**
- Shot-to-reference mapping in shot matrix
- Continuity ledger linkage
- Reference consumption in prompt assembly

---

## 4. Provider Architecture (What's Ported vs What's Missing)

### Already Ported to `film-pipeline-langgraph`

| Component | Location | Status |
|-----------|----------|--------|
| `BaseProviderAdapter` ABC | `src/film_pipeline/providers/base.py` | ✅ Complete |
| `ProviderJob` dataclass | `src/film_pipeline/providers/base.py` | ✅ Complete |
| `Imagen4GeminiProvider` | `src/film_pipeline/providers/adapters/imagen4_gemini.py` | ✅ Complete (build_payload, submit, poll, download, extract_metadata, estimate_cost) |
| `SeedanceOpenRouterProvider` | `src/film_pipeline/providers/adapters/seedance_openrouter.py` | ✅ Complete |
| `VeoFastProvider` | `src/film_pipeline/providers/adapters/veo_fast.py` | ✅ Complete |
| `MockVideoProvider` | `src/film_pipeline/providers/mock_provider.py` | ✅ Complete |
| `MockImageProvider` | `src/film_pipeline/providers/mock_image_provider.py` | ✅ Complete |
| `ProviderRegistry` | `src/film_pipeline/providers/registry.py` | ✅ Complete |
| `build_provider_adapter()` factory | `src/film_pipeline/providers/factory.py` | ✅ Complete (with default capabilities + cost profiles) |
| `ProviderHealthTracker` | `src/film_pipeline/providers/health.py` | ✅ Complete |
| Artifact system (store, index, paths, manifest, versioning) | `src/film_pipeline/artifacts/` | ✅ Complete |
| KB system (curator, paths, manifest, retrieval, conflicts) | `src/film_pipeline/kb/` | ✅ Complete |
| Validation rubrics doc | `docs/reference-image-flow.md` | ✅ Existing doc, needs integration with code |

### Still Missing (Needs Implementation)

| Feature | Priority | Notes |
|---------|----------|-------|
| **Reference Strategy Agent** (Phase 0) | High | Creates reference matrix from film profile + bibles |
| **Prompt Block Lock service** (Phase 1) | High | Versions and locks prompt blocks before generation |
| **Batch Generator** (Phase 2 orchestration) | **Critical** | Parallel dispatch of base frames, per-provider routing, best-of-N selection |
| **Seed Drift Triage** (Phase 2 fallback) | High | 3 attempts → I2I → manual flag |
| **Ancestor Safety Filters** (Phase 2 edge case) | Medium | Tiered fallback (museum → bust → overlay) |
| **Per-Frame Validation** (Phase 3) | **Critical** | Auto heuristics + Gemini review, retry loop |
| **Composite Builder** (Phase 4) | **Critical** | Pillow-based template compositor, partial rebuild |
| **Composite Validation** (Phase 5) | **Critical** | Gemini review + structured scoring per rubric |
| **Multi-Model Validator** (Phase 5 enhancement) | Medium | 2+ models review critical anchors |
| **Delta-Regeneration Loop** (Phase 6) | High | Tile-level replacement + max 3 iterations |
| **Reference Index structure** (Phase 7) | High | Schema, validation reports, provider tracking |
| **Shot bibles reference integration** (Phase 8) | High | Map refs → shots in master film matrix |
| **Human review package** | Medium | Bundled reference + validation + dependencies for human sign-off |

---

## 5. Validation Score Philosophy

**80% is the pass threshold for reference sheets.** Reference sheets only need to be
*representative*, not production-perfect. A 90%+ threshold leads to infinite iteration
loops on minor artifacts (tiny edge jitter, subtle color difference) that don't affect
downstream generation.

**What 80% achieves:**
- Character identity is clearly the same person across tiles
- Environment geometry is coherent and usable
- Expression range is unambiguous
- Technical quality is good enough for a video model to read

**What 80% accepts:**
- Minor edge artifacts between tiles
- Small color differences within acceptable range
- Slight expressions that are "close enough"
- Good-but-not-perfect composition

---

## 6. Cost Model

| Stage | Frames | Cost/Frame | Subtotal |
|-------|--------|-----------|----------|
| Character frames (per character) | 5–15 | $0.02–0.10 | $0.30–1.50 |
| Environment frames (per env) | 6 | $0.02 | $0.12 |
| Detail frames | 30 | $0.02–0.10 | $0.60–3.00 |
| Scale reference | 6 | $0.02 | $0.12 |
| Per-frame validation (Gemini) | ~50% of frames | ~$0.001 | ~$0.10 |
| Composite validation (Gemini) | ~5 sheets | ~$0.005 | ~$0.025 |

**Budget ceiling: $10** (including retries and premium frames).

---

## 7. Execution Sequence (Legacy — The Primordial Stroke)

```
Step 1:  Leo identity frames (15 frames, ~$0.30) → Auto-check → Gemini validate anchor
Step 2:  Build Leo identity sheet
Step 3:  Gemini validate Leo sheet → fix/partial-rebuild if needed
Step 4:  Lock Leo identity in reference index
Step 5:  Run env frames for ENV_01 (6 frames) → Auto-check
Step 6:  Build ENV_01 board
Step 7:  Gemini validate ENV_01 board
Step 8:  Lock ENV_01
Step 9:  Repeat Steps 5–8 for remaining environments
Step 10: Run ancestor character frames (50 frames) → Auto-check + Gemini spot-check 30%
Step 11: Build ancestor identity sheets
Step 12: Gemini validate ancestor sheets → partial-rebuild if needed
Step 13: Build scale reference sheet
Step 14: Gemini validate scale sheet
Step 15: Lock all ancestors
Step 16: Run detail frames (30 frames) → Auto-check only
Step 17: Build env boards with detail insets
Step 18: Final validation pass on env boards
Step 19: Lock reference index
Step 20: Register in continuity ledger
```

**Cost checkpoint after Step 1:** If Leo's anchor face fails validation ×2+, pause
pipeline — the character prompt needs fixing first.

---

## 8. Error Recovery Matrix

| Failure Mode | Trigger | Recovery Action | Cost |
|---|---|---|---|
| Face drift across angles | Validation fail on identity_accuracy | I2I seed drift fallback all tiles | +$5–10 retries |
| Single tile artifact | Validation fail on technical_quality | Delta-regenerate that tile only | +$0.90 |
| Expression mismatch | Fail on expression_fidelity | Regenerate expression tile with corrected prompt | +$0.90 |
| Image provider blocks | Safety filter on ancestor images | Switch to different provider (looser filters) | +$0.05 retry |
| Quality too low | Fail on technical_quality | Switch to higher tier (standard/ultra) | +$0.03–0.08 |
| Leo sheet fails ×2+ | Fail Steps 1–4 | **PAUSE PIPELINE**, fix CHAR_DESC block | Prevents waste |
| Provider swap mid-pipeline | Need to change backend | Restart with `--image-provider new` | $0 |
| Image corrupt/broken | Auto-heuristics fail | Regenerate with same seed + higher tier | +$0.05 |
| Composite layout error | Script crash | Check frame naming, rebuild | $0 |

---

## 9. Design Rules & Anti-Patterns

### Rules
- ✅ Use image providers for reference frames (NOT video providers)
- ✅ Labels go in margin areas (never over tile content)
- ✅ Dominant tile should be the most important anchor (face 2×)
- ✅ Lock prompt blocks before any generation starts
- ✅ Version-lock everything in the reference index
- ✅ 80% threshold for sheets (not 90%)
- ✅ Multi-model review for critical anchors
- ✅ Human review before locking main character + recurring environment sheets
- ✅ RCTCO for all prompts (Role, Core Task, Context, Constraints, Output Format)

### Anti-Patterns
- ❌ Generating references before story/character intent is stable
- ❌ Using concept art as production reference without validation
- ❌ Every shot having a unique style reference
- ❌ Overloading one sheet with too many ideas
- ❌ Labels/typography inside image tiles
- ❌ Accepting beautiful images that fail identity/geometry checks
- ❌ Treating references as optional after generation starts
- ❌ Using the same model to generate and validate (one gate to start: different models)

---

## 10. RCTCO Template for Reference Prompts

```
Role: [reference art director / production usability validator / continuity reviewer]

Core Task: [generate a character identity sheet / validate an environment board /
            repair a failing composite tile / summarize a reference review]

Context:
- Film constitution: [link]
- Character bible: [link]
- Environment bible: [link]
- Camera bible: [link]
- Master film matrix rows: [relevant shots]
- Provider constraints: [max resolution, supported aspects]

Constraints:
- Exact frame requirements: [angles, expressions, lighting]
- Global negatives: [standardized negative list]
- No text over tiles (margins only)
- Provider limits: [max_tiles, aspect_ratio, resolution caps]

Output Format:
- For generation: composite sheet at [resolution] as PNG
- For validation: structured JSON with scores per domain
- For regeneration: delta plan with tile names + replacement prompts
```

---

## 11. Bad Reference Signs (For Production Validator)

A reference may be visually attractive but bad for generation.

**Tagging:**
- `too_noisy` — too many competing subjects
- `identity_unclear` — inconsistent face across tiles
- `geometry_unclear` — cluttered environment, layout confused
- `style_conflict` — strong mismatch with desired output style
- `moderation_risk` — contains elements likely to trigger provider filter
- `low_resolution` — too small for the generation model to read
- `text_bleed_risk` — labels encroach on tile content
- `contradictory` — conflicting signals (e.g., two different palettes)

---

## 12. Stop Rule

Stop generating more references when:

1. **Required validators pass** for all critical sheets
2. **Human review passes** for main character + recurring environments
3. **Missing references no longer create generation risk** (all high-drift scenes covered)
4. **Additional references would add noise** or contradictory signals

More references can make results WORSE if they confuse the model.
Quantity is not quality. Be ruthless about pruning.

---

## 13. Mapping to Legacy Sources

| Legacy File | Content | Ported to LangGraph? |
|------------|---------|---------------------|
| `skills/reference-image-pipeline/SKILL.md` | Pipeline overview, phases, providers | Partially (agent nodes missing) |
| `skills/reference-image-pipeline/references/PIPELINE.md` | Full 20-step pipeline spec | Partially (doc exists, code missing) |
| `skills/reference-image-pipeline/references/GEMINI-REVIEW-v1.md` | Reviewer v1: conditional pass, 14 recommendations | ✅ (all v1 recommendations incorporated into this doc) |
| `skills/reference-image-pipeline/references/GEMINI-REVIEW-v2.md` | Reviewer v2: approved, all v1 fixes verified | ✅ |
| `skills/reference-image-pipeline/references/GEMINI-REVIEW-v3.md` | Reviewer v3: provider-agnostic architecture | ✅ (provider ABC in base.py + factory.py) |
| `skills/reference-image-pipeline/scripts/providers.py` | GoogleVeoLiteProvider, GoogleImagenProvider, OpenRouterSeedanceProvider | ✅ (ported to adapters/) |
| `skills/film-production-pipeline/SKILL.md` | Unified 8-phase pipeline (Phase 2 = Pre-Pro = reference images) | Partially |
| `skills/film-production-pipeline/references/validation-rubric.md` | 5-domain rubric, per-type metrics | ❌ Not ported |
| `~ai-movies/the-primordial-stroke/references/` | Actual production reference sheets + index | ❌ Not ported |
| `docs/reference-image-flow.md` | LangGraph reference image flow doc | ✅ (doc exists, aligns with this spec) |
| `src/film_pipeline/providers/adapters/imagen4_gemini.py` | Imagen 4 image provider | ✅ Complete |
| `src/film_pipeline/artifacts/` | Artifact store, index, paths, versioning | ✅ Complete (needs ref-specific schema) |
