# Reference Image Pipeline — Gap Analysis

> **Date:** 2026-06-21
> **Sources compared:**
> - `docs/reference-image-generation-and-validation.md` (legacy 9-phase spec from The Primordial Stroke)
> - `docs/reference-image-flow.md` (existing LangGraph doc)
> - `src/film_pipeline/` (current codebase)

---

## Summary

The current LangGraph pipeline has solid **schema, provider, and artifact infrastructure** but
is missing the **execution layer** that made the legacy pipeline produce actual production-ready
reference sheets. We can generate individual images through `generate_reference_images`, but
those are raw provider outputs — not validated, not composited, and not organized. The gap
between "generate individual PNGs" and "produce AI-usable reference sheets" is ~80% of the
legacy spec.

---

## 1. What We Have (Done)

| Component | What it does | File |
|-----------|-------------|------|
| `ReferenceIndex` / `ReferenceIndexEntry` | Typed Pydantic schema matching the legacy reference index contract | `schemas/reference.py` |
| `ReferenceStrategy` | Schema for the strategy plan (priorities, costs, providers) | `schemas/reference.py` |
| `VisualDevAgent` | LLM agent that creates `ReferenceIndex` from script + constitution | `agents/impl/visual_dev_agent.py` |
| `visual_dev_node` | Graph node wiring the agent into LangGraph pipeline | `graph/nodes.py` |
| `Imagen4GeminiProvider` | Full image provider adapter (build_payload → submit → poll → download) | `providers/adapters/imagen4_gemini.py` |
| `generate_reference_images` MCP tool | Iterates reference index entries, calls image provider, saves PNGs | `mcp/tools/__init__.py` |
| `inspect_reference` MCP tool | Looks up a reference entry by ID | `mcp/tools/__init__.py` |
| `ReferenceUsabilityValidator` | Metadata-only validator (resolution, moderation, subject type) | `validation/impl/reference_usability.py` |
| `GenerationLedger` / manager | Full CRUD for generation lifecycle (plan → approve → submit → poll) | `generation/ledger.py` |
| Artifact system | Versioned storage, indexing, paths, manifests | `artifacts/` |

---

## 2. What's Missing — Mapped to Legacy Phases

### Phase 0 — Reference Strategy (PARTIALLY DONE)

**Have:** `ReferenceStrategy` schema, `VisualDevAgent` produces `ReferenceIndex` entries.

**Missing:**
- No dedicated strategy agent that answers the legacy spec's key questions:
  - Which characters need hard identity locking?
  - Which environments need geometry locking?
  - Which props are story-critical?
  - Which scenes are high drift risk?
  - Which references may trigger provider moderation?
  - Which references are needed before shot bible approval?
- The `VisualDevAgent` prompt template produces entries but doesn't reason about priorities,
  provider tier assignments, or cost estimates per entry.

### Phase 1 — Prompt Block Lock (MISSING)

Nothing exists. No mechanism to:
- Version-lock prompt blocks before generation starts
- Invalidate all previously generated frames when CHAR_DESC changes
- Apply global negative prompt consistently

### Phase 2 — Base Frame Generation (PARTIALLY DONE)

**Have:** `generate_reference_images` MCP tool calls a single image provider per entry and
downloads the result.

**Missing:**
- **Batch orchestrator** — no parallel dispatch. Entries are iterated sequentially in a
  for-loop.
- **Best-of-N selection** — generates exactly 1 image per entry. The legacy spec generates
  multiple frames per angle/expression and selects the best.
- **Seed drift triage** — no I2I fallback (strength 0.3–0.5) for angle consistency
- **Ancestor safety filter fallback** — no tiered fallback for moderation-triggering content
- **Multi-provider routing** — all entries use the same provider. The legacy spec uses fast
  ($0.02) for bulk, standard ($0.05) for anchors, ultra ($0.10) for detail insets.
- **Provider tier selection per entry** — no `tier` field on entries to control which
  provider/cost level to use.

### Phase 3 — Per-Frame Validation (MOSTLY MISSING)

**Have:** `ReferenceUsabilityValidator` checks metadata fields (quality_score, moderation_risk,
subject_type). It does NOT inspect actual image files.

**Missing:**
- **Auto-heuristic checks** (Pillow-based, free):
  - File exists and non-zero (`os.path.getsize()`)
  - Min resolution ≥ 512×512
  - Not corrupt (can open with Pillow)
  - Has content (color variance — not solid black/white)
  - Face present (face width >10% of frame for character frames)
- **AI review** (Gemini Flash, ~$0.001/frame):
  - Subject Present (10 pts) — expected subject visible? face clear?
  - Prompt Match (10 pts) — expression, position, lighting match?
  - Artifact Freedom (10 pts) — no deformities, merges, extra anatomy?
  - Technical Quality (10 pts) — sharp focus, proper exposure?
  - Threshold: ≥28/40 (70%)
- **Retry logic** — max 2 retries per frame, best-available fallback, never block pipeline
- **Selective validation strategy** — skip Gemini for environment lighting variants, detail
  insets; spot-check 30% of alt angles; always validate character front face

### Phase 4 — Composite Sheet Construction (MISSING)

Nothing exists. This is the largest gap. The legacy spec describes:

- **Pre-composite normalization:** crop to 720×720, face-center align, color normalize,
  scale consistency
- **Template system:** Character Identity Sheet, Costume & State Sheet, Environment Board,
  Prop Sheet, Scale Sheet, Style & Color Board, Camera Reference Board
- **Layout engine:** grid borders (1–2px), 8px spacing, labels in margins only (never on
  tiles), visual hierarchy (face 2× > body 1× > expressions 0.5×)
- **Output:** 2048×2048 for character sheets, 3840×2160 for environment boards
- **Partial rebuild:** `--replace-tile <name> <path>` swaps a single tile

The current `generate_reference_images` saves individual provider outputs to
`references/sheets/` — flat directory, no composition.

### Phase 5 — Composite Validation (MISSING)

Nothing exists. The legacy spec describes Gemini-based validation of complete composite
sheets with domain-specific rubrics:

| Sheet Type | Max Score | Threshold | Key Domains |
|-----------|-----------|-----------|-------------|
| Character | 50 | ≥40 (80%) | Identity accuracy, expression fidelity, composition, technical, usability |
| Environment | 50 | ≥40 (80%) | Spatial consistency, lighting, mood, technical, usability |
| Scale | 20 | ≥16 (80%) | Proportion, context clarity, technical |

Also missing: multi-model review for critical anchors (2+ models), consensus reports,
validation statuses (`approved`, `approved_with_notes`, `needs_delta_fix`, etc.)

### Phase 6 — Delta Regeneration (MISSING)

Nothing exists. The legacy spec describes:
- Parse Gemini report for specific failing tiles
- Regenerate only those tiles, not the whole batch
- Max 3 validation iterations per sheet
- After 3 iterations, best score wins — no blocking
- Script logs: `{sheet_name}: best={score}/{max} after {n} iterations`
- 30–40% cost reduction vs full-batch regeneration

### Phase 7 — Registration (PARTIALLY DONE)

**Have:** `ReferenceIndex` schema, artifact persistence, `inspect_reference` MCP tool.

**Missing:**

**File organization.** The legacy spec prescribes:
```
references/
├── index/
│   ├── reference-index.json
│   └── reference-validation-summary.json
├── characters/
│   └── CHAR_001/
│       ├── identity-sheet.png
│       ├── costume-sheet.png
│       ├── master-frames/
│       └── validation-report.json
├── environments/
│   └── ENV_001/
│       ├── environment-board.png
│       └── master-frames/
├── props/
├── style/
├── scale/
└── review-packages/
```

The current code saves everything flat to `references/sheets/`. The `asset_path` in
`ReferenceIndexEntry` is just a relative path to a provider output — no type-based
subdirectory, no `master-frames/`, no `validation-report.json` per entry.

### Phase 8 — Matrix & Continuity Integration (MISSING)

Nothing exists. The shot bible doesn't link to references. The prompt assembly doesn't consume
reference images. The continuity ledger has no reference awareness.

---

## 3. Architectural Gaps (Cross-Cutting)

### 3.1 No image processing capability

The codebase has zero image processing dependencies or code. The legacy spec requires:
- Pillow/OpenCV for composite construction
- Color normalization across tiles
- Face-center alignment
- Label rendering in margins
- Resolution validation and cropping

### 3.2 No Gemini image review integration

The legacy spec uses Gemini Flash (~$0.001/image) to review generated images. The current
`ReferenceUsabilityValidator` only reads metadata fields. We have no Gemini image review
prompt, no rubric scoring, and no integration with the existing model adapter for
image-inclusive calls.

### 3.3 The `generation_node` is a no-op

```python
def generation_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    new_state["current_phase"] = "generation"
    new_state["approved"] = False
    new_state["human_approval_required"] = True
    new_state["human_approval_phase"] = "generation_batch"
    return new_state
```

The graph's generation phase sets flags but doesn't call any agent. The MCP
`generate_reference_images` tool bypasses the graph entirely — it directly calls the provider
and mutates state. This means reference image generation can't be triggered through the
graph flow; it requires an external MCP client.

### 3.4 Generation ledger is video-centric

`GenerationLedger` and its manager (`plan_batch`, `approve_spend`, `start_generation_batch`)
are designed for video clip generation (shot_id, duration, coverage groups). They don't model
image-only reference generation — no concept of frame batches, per-angle entries, composite
sheet assembly, or the reference-specific lifecycle.

---

## 4. Prioritized Implementation Order

### Tier 1 — Launch Blockers (must have to produce usable references)

| # | Item | Phase | Effort |
|---|------|-------|--------|
| 1 | **Organized file structure** — `references/characters/CHAR_001/`, `references/environments/ENV_001/`, etc. Save generated images to type+subject subdirectories instead of flat `sheets/`. | 7 | Small |
| 2 | **Per-frame auto-heuristic checks** — Pillow-based: file exists, resolution ≥ 512, not corrupt, has content, face present for character frames. | 3 | Small |
| 3 | **Batch parallel generation** — async/threaded dispatch of multiple entries instead of sequential for-loop. | 2 | Medium |
| 4 | **Provider tier routing per entry** — add `tier` field to entries (fast/standard/ultra), route to appropriate provider or provider config. | 2 | Small |
| 5 | **Composite sheet builder** — Pillow-based template composer for at minimum the Character Identity Sheet (front face + 3/4 angles + body + expressions). This is the biggest single piece of missing value. | 4 | Large |

### Tier 2 — Quality Gates (make references trustworthy)

| # | Item | Phase | Effort |
|---|------|-------|--------|
| 6 | **Gemini per-frame AI review** — image-inclusive model call with the legacy rubric (Subject/Prompt Match/Artifacts/Technical, ≥28/40). | 3 | Medium |
| 7 | **Retry + best-of-N logic** — max 2 retries per frame, keep best attempt, never block pipeline. | 3 | Medium |
| 8 | **Composite validation** — Gemini review of complete sheets with domain-specific rubrics. | 5 | Medium |
| 9 | **Delta regeneration** — tile-level replacement from validation reports, max 3 iterations. | 6 | Medium |

### Tier 3 — Strategic & Integration (make references part of the pipeline)

| # | Item | Phase | Effort |
|---|------|-------|--------|
| 10 | **Reference strategy agent** — dedicated agent that plans priorities, provider assignments, costs before generation. | 0 | Medium |
| 11 | **Prompt block lock** — version and lock prompt blocks, invalidate on change. | 1 | Medium |
| 12 | **Shot-to-reference mapping** — link shot bible entries to approved references. | 8 | Small |
| 13 | **Remaining composite templates** — Environment Board, Prop Sheet, Scale Sheet, Style Board, Camera Board. | 4 | Large |
| 14 | **Multi-model review** — 2+ models review critical anchors, consensus report. | 5 | Large |
| 15 | **Wire generation_node** — make the graph's generation phase actually run reference image generation (or at minimum, the reference generation path) instead of being a no-op. | Graph | Medium |

---

## 5. File Organization — Target Structure

Current state (flat):
```
<project>/references/sheets/
  ├── ref-char-leo-identity-v1.png
  ├── ref-env-studio-board-v1.png
  └── ...
```

Target state (from legacy spec):
```
<project>/references/
├── index/
│   ├── reference-index.json
│   └── reference-validation-summary.json
├── characters/
│   └── CHAR_001/
│       ├── identity-sheet.png          ← composite (Tier 1)
│       ├── costume-sheet.png           ← composite (Tier 3)
│       ├── master-frames/              ← raw provider outputs
│       │   ├── front-face.png
│       │   ├── 3-4-left.png
│       │   ├── profile-right.png
│       │   └── full-body.png
│       └── validation-report.json      ← per-entry (Tier 2)
├── environments/
│   └── ENV_001/
│       ├── environment-board.png
│       ├── master-frames/
│       └── validation-report.json
├── props/
├── style/
├── scale/
└── review-packages/
```

---

## 6. What the Legacy Spec Gets Right That We Should Keep

These design decisions from the legacy spec are load-bearing and should be preserved:

1. **80% threshold for sheets** — not 90%. Prevents infinite iteration loops on minor
   artifacts that don't affect downstream generation.
2. **Labels in margins only** — never over tile content. Prevents typography bleed into
   generation.
3. **Dominant tile 2× scale** — face is the most important anchor, gets the most visual
   weight.
4. **Image providers for reference frames** — NOT video providers. ~18× cheaper.
5. **Selective validation** — don't pay Gemini to review environment lighting variants or
   detail insets. Save cost.
6. **Never block the pipeline** — a single bad frame doesn't stop everything. Best attempt
   used after max retries, flagged for human review.
7. **Multi-model review for critical anchors** — preserve disagreements, don't squash them
   into a fake consensus.
8. **Stop rule** — more references can make results WORSE. Quantity is not quality.

---

## 7. Files That Need Changes (Current Estimate)

| File | Change |
|------|--------|
| `schemas/reference.py` | Add `tier` field to `ReferenceIndexEntry`, add frame-level validation schema |
| `agents/impl/visual_dev_agent.py` | Minor — parse tier/provider assignments from model output |
| `agents/prompt_templates/defaults.py` | Update visual-dev template to include tier and priority reasoning |
| `mcp/tools/__init__.py` | Rewrite `generate_reference_images` — organized output dirs, batch parallelism, auto-heuristics, tier routing |
| `validation/impl/reference_usability.py` | Add Pillow-based heuristic checks, add Gemini image review path |
| **NEW** `generation/reference_compositor.py` | Composite sheet builder (Pillow templates, normalization, layout) |
| **NEW** `generation/reference_validator.py` | Per-frame + composite Gemini validation with legacy rubrics |
| **NEW** `generation/reference_regenerator.py` | Delta regeneration loop, max-iterations, best-score tracking |
| `graph/nodes.py` | Wire `generation_node` to actually do something for references |
| `generation/ledger.py` | Add reference-image-specific ledger rows or a parallel ledger |

---

## 8. Quick Wins (Can Ship This Week)

1. **Organize output directories** — change `generate_reference_images` to save into
   `references/{subject_type}s/{subject_id}/` instead of flat `references/sheets/`.
   ~20 lines changed.

2. **Auto-heuristic checks** — add Pillow checks before accepting a generated image.
   ~40 lines, instant value.

3. **Parallel dispatch** — convert the for-loop in `generate_reference_images` to use
   `asyncio.gather` or a thread pool. ~10 lines changed, ~5-10× speedup for batch generation.

4. **Provider tier field** — add `tier: str = "fast"` to `ReferenceIndexEntry`, select
   provider config based on tier in `generate_reference_images`.
