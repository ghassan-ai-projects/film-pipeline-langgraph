# Film Pipeline — Artifact Map

> **Status legend:**
> - ✅ Implemented — agent writes, tests pass
> - ⚠️ Schema-only — Pydantic model exists, no writer
> - ❌ Missing — no schema, no writer
> - 🛠️ MCP tool — produced by MCP tools, not LangGraph nodes
>
> **Last verified:** 2026-06-21 (commits through `be7d75a`)

---

## Storage Methods

| Method | Used for | Example |
|--------|----------|---------|
| `ArtifactStore.save(schema)` | Pydantic BaseModel artifacts | `film_constitution`, `script`, `treatment` |
| `ArtifactStore.save_dict(dict)` | Dict-based artifacts (mutated post-creation) | `reference_index` |
| Direct `Path.write_text()` | Human-readable index files | `references/index/reference-index.json` |
| Provider `.download()` | AI-generated binary assets | PNG frames, composite sheets |
| Pillow `.save()` | Programmatic image composition | `identity-sheet.png`, `environment-board.png` |

**Note:** `save()` expects a Pydantic v2 BaseModel and calls `.model_dump_json()`.
`save_dict()` accepts plain dicts — used when entries are mutated in a generation
loop and don't round-trip cleanly through the schema at save time.

---

## Phase-by-Phase Artifact Map

### Phase: Intake (`01-intake/`)

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Project Profile | `ProjectProfile` | ✅ | `intake_node` writes to artifact store |
| Project Config | *(state-only)* | ⚠️ | Resolved config stored in LangGraph state, not persisted to artifact store |

---

### Phase: Constitution (`02-constitution/`)

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Film Constitution | `FilmConstitution` | ✅ | Theme, tone, visual language, camera philosophy |

---

### Phase: Development (`03-development/`)

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Treatment | `Treatment` | ✅ | Long-form prose + themes |
| Scene List | `SceneList` | ✅ | `SceneIntent` entries |
| Story Bible | `StoryBible` | ✅ | Saved during script phase |

---

### Phase: Script (`04-script/`)

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Script | `Script` | ✅ | Full screenplay with dialogue |
| Story Bible | `StoryBible` | ✅ | Aggregate: logline + premise + treatment + scenes |

---

### Phase: Visual Development (`04-visual-dev/`)

This phase has two artifact production paths:

1. **LangGraph `visual_dev_node`** — saves `reference_index` to artifact store
2. **MCP `generate_reference_images` tool** — generates images, composite
   sheets, index files, and enriches the reference index artifact

#### Bible Artifacts (input, not produced here)

These bibles are consumed by `generate_reference_images` for structured prompt
construction, but no LangGraph node currently produces them.

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Character Bible | `CharacterBible` | ⚠️ | Schema exists. No writer. Needed for prompt CHAR_DESC block. |
| Environment Bible | `EnvironmentBible` | ⚠️ | Schema exists. No writer. `color_palette` consumed by compositor. |
| Camera Language Bible | `CameraLanguageBible` | ⚠️ | Schema exists. No writer. |
| Style Bible | *(missing)* | ❌ | No schema. Color palette, texture, grain, visual mood. |

#### Reference Index (artifact store)

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Reference Index | `ReferenceIndex` | ✅ | `visual_dev_node` saves via `_run_agent()`. `generate_reference_images` enriches with `asset_path`, `provider`, `generation_status`, `quality_score`, `validation`, `ai_usability`. |

#### Reference Images (file system — MCP tool)

| Artifact | Format | Path | Notes |
|----------|--------|------|-------|
| Master frame | PNG | `references/{type}s/{id}/master-frames/{reference_id}.png` | Individual generated frame. Named by `reference_id`. |
| Character Identity Sheet | PNG | `references/characters/{id}/identity-sheet.png` | 2048×2048 composite, 20 tile positions |
| Environment Board | PNG | `references/environments/{id}/environment-board.png` | 3840×2160 composite, 8 tile positions + color palette |
| Reference index (human-readable) | JSON | `references/index/reference-index.json` | All entries with asset_path, validation, locked |
| Validation summary (human-readable) | JSON | `references/index/reference-validation-summary.json` | Counts and average scores |

**Not yet implemented:**
- ❌ `.meta.json` sidecars for individual frames
- ❌ `.sheet.json` layout manifests for composite sheets
- ❌ `costume-sheet.png`, `expression-sheet.png` — additional composite templates
- ❌ `props/`, `style/`, `scale/` — other reference types

#### Validation (generated during image pipeline)

| Artifact | Where | Notes |
|----------|------|-------|
| Per-frame heuristic results | Entry dict (`passed`/`failures` fields) | 5 Pillow checks, $0 cost |
| Per-frame Gemini review | Entry dict (`validation`, `ai_usability` fields) | 40-pt rubric, selective |
| Composite validation | Console log (Gemini response) | Not persisted as artifact |
| Delta regeneration history | Internal to generation loop | Not persisted |

---

### Phase: Shot Bible (`05-shot-bible/`)

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Master Film Matrix | `MasterFilmMatrix` | ⚠️ | Schema exists. `shot_bible_node` is flag-only. |
| Continuity Ledger | `ContinuityLedger` | ⚠️ | Schema exists. No writer. |
| Prompt Registry | `PromptRegistry` | ⚠️ | Schema exists. No writer. |

---

### Phase: Generation Planning (`06-generation-plan/`)

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Generation Plan | *(missing)* | ❌ | No schema. Ordered shot list with provider routing. |
| Cost Estimate | `CostEstimate` | ⚠️ | Schema exists. No writer. |
| Budget State | `BudgetState` | ⚠️ | Schema exists. No writer. |

---

### Phase: Generation (`07-generated-assets/`)

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Generation Ledger | `GenerationLedger` | 🛠️ | Written by MCP tools (`plan_generation_batch`, `approve_generation_spend`, etc.) via `GenerationLedgerManager` |
| Generation Request | `GenerationRequest` | ⚠️ | Schema exists (idempotency key). No writer. |
| Video clip | MP4 | ⚠️ | No actual video generation yet. |
| Last frame / Mid frame | PNG | ⚠️ | No video generation yet. |
| Resume Token | `ResumeToken` | ⚠️ | Schema exists. No writer. |

---

### Phase: QC / Validation (`08-validation/`)

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Validation Report | `ValidationReport` | ⚠️ | Schema exists. `qc_node` is flag-only. |
| Consensus Report | `ConsensusReport` | ⚠️ | Schema exists. No writer. |
| Validation Ledger | `ValidationLedgerEntry` | ⚠️ | Schema exists. No writer. |
| Issue Record | *(missing)* | ❌ | No schema. Cross-cutting issue tracking. |

---

### Phase: Post-Production (`09-post/`)

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Assembly Manifest | `AssemblyManifest` | ⚠️ | Schema exists. Node is flag-only. |
| Audio stems | WAV/MP3 | ⚠️ | Not yet generated. |
| Subtitles | SRT | ⚠️ | Not yet generated. |
| Review Cut | MP4 | ⚠️ | Not yet assembled. |

---

### Phase: Delivery (`10-delivery/`)

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Delivery Package | `DeliveryPackage` | ⚠️ | Schema exists. Node is flag-only. |
| Final Cut | MP4 | ⚠️ | Not yet produced. |
| Delivery Stills | PNG | ⚠️ | Not yet produced. |

---

### Cross-Cutting Artifacts

| Artifact | Schema | Status | Notes |
|----------|--------|--------|-------|
| Asset Manifest | `AssetManifest` | ⚠️ | Written but never read. |
| Checkpoint | `CheckpointMetadata` | ⚠️ | Schema exists. No writer. |
| Rollback Record | `RollbackRecord` | ⚠️ | Schema exists. No writer. |
| Invalidation Report | `InvalidationReport` | ⚠️ | Schema exists. No writer. |
| Approval Record | `ApprovalRecord` | ✅ | Written at phase gates via MCP tools. |
| Revision Request | `RevisionRequest` | ⚠️ | Schema exists. No writer. |
| KB Context Packet | `KBContextPacket` | ⚠️ | Schema exists. |

---

## Actual File Tree (What Exists)

Only shows paths that are currently produced. Items with `(planned)` are
documented in schemas but not yet written.

```
projects/{slug}/
│
├── 01-intake/
│   └── project_profile.v1.json          ✅
│
├── 02-constitution/
│   └── film_constitution.v1.json         ✅
│
├── 03-development/
│   ├── treatment.v1.json                 ✅
│   └── scene_list.v1.json               ✅
│
├── 04-script/
│   ├── story_bible.v1.json              ✅
│   └── script.v1.json                   ✅
│
├── 04-visual-dev/
│   ├── reference_index.v1.json          ✅ (from visual_dev_node)
│   ├── character_bible.v1.json          (planned — schema exists, no writer)
│   ├── environment_bible.v1.json        (planned — schema exists, no writer)
│   ├── camera_language_bible.v1.json    (planned — schema exists, no writer)
│   ├── style_bible.v1.json              (planned — no schema)
│   └── reference_strategy.v1.json       (planned — schema exists, no writer)
│
├── references/                           🛠️ MCP: generate_reference_images
│   ├── index/
│   │   ├── reference-index.json          ✅
│   │   └── reference-validation-summary.json  ✅
│   ├── characters/
│   │   └── {subject_id}/
│   │       ├── master-frames/
│   │       │   ├── char-{id}-front-face.png
│   │       │   ├── char-{id}-profile-right.png
│   │       │   └── ...
│   │       └── identity-sheet.png
│   └── environments/
│       └── {subject_id}/
│           ├── master-frames/
│           │   ├── env-{id}-wide.png
│           │   └── ...
│           └── environment-board.png
│
├── 05-shot-bible/                        (all planned)
│   ├── master_film_matrix.v1.json       ⚠️
│   ├── continuity_ledger.v1.json        ⚠️
│   └── prompt_registry.v1.json          ⚠️
│
├── 06-generation-plan/                   (all planned)
│   ├── generation_plan.v1.json          ❌
│   ├── cost_estimate.v1.json            ⚠️
│   └── budget_state.v1.json             ⚠️
│
├── 07-generated-assets/                  (all planned)
│   ├── generation_ledger.v1.json        ⚠️
│   └── shots/
│       └── S001/
│           ├── generation_request.v1.json  ⚠️
│           ├── S001.v1.mp4                 ⚠️
│           └── resume_token.v1.json        ⚠️
│
├── 08-validation/                        (all planned)
│   ├── validation_ledger.v1.json        ⚠️
│   └── validation_report_*.v1.json      ⚠️
│
├── 09-post/                              (all planned)
│   ├── assembly_manifest.v1.json        ⚠️
│   ├── audio/                            ⚠️
│   ├── subtitles/                        ⚠️
│   └── review_cut.v1.mp4                ⚠️
│
├── 10-delivery/                          (all planned)
│   ├── delivery_package.v1.json         ⚠️
│   ├── final_cut.v1.mp4                 ⚠️
│   └── stills/                          ⚠️
│
└── versions/                             (all planned)
    ├── checkpoints/                      ⚠️
    ├── rollbacks/                        ⚠️
    └── invalidations/                    ⚠️
```

---

## Target File Tree (Aspirational)

Additional paths planned but not yet implemented:

```
references/
├── characters/{id}/
│   ├── costume-sheet.png                (planned)
│   ├── expression-sheet.png             (planned)
│   └── *.png.meta.json                  (planned — frame metadata sidecar)
├── environments/{id}/
│   ├── *.png.meta.json                  (planned)
│   └── *.sheet.json                     (planned — tile layout manifest)
├── props/                               (planned)
├── style/                               (planned)
│   ├── visual-style-board.png
│   ├── camera-style-board.png
│   └── color-palette.png
└── scale/
    └── scale-sheet.png                  (planned)
```

---

## Node Maturity

| Node | Produces | Phase artifact? | Storage method |
|------|----------|----------------|----------------|
| `intake_node` | `ProjectProfile`, `ProjectConfig` | ✅ | `ArtifactStore.save()` |
| `constitution_node` | `FilmConstitution` | ✅ | `ArtifactStore.save()` |
| `development_node` | `Treatment`, `SceneList` | ✅ | `ArtifactStore.save()` |
| `script_node` | `StoryBible`, `Script` | ✅ | `ArtifactStore.save()` |
| `visual_dev_node` | `ReferenceIndex` | ⚠️ Partial | `ArtifactStore.save()` (via `_run_agent`) |
| `generate_reference_images` (MCP) | Frames, sheets, index files | 🛠️ MCP | Provider + Pillow + `save_dict()` |
| `shot_bible_node` | — | ❌ Flag-only | — |
| `gen_planning_node` | — | ❌ Flag-only | — |
| `generation_node` | — | ❌ Flag-only | — |
| `qc_node` | — | ❌ Flag-only | — |
| `post_node` | — | ❌ Flag-only | — |
| `delivery_node` | — | ❌ Flag-only | — |

---

## Known Gaps (Schemas Without Writers)

| Schema | File | Blocked by |
|--------|------|-----------|
| `CharacterBible` | `character.py` | No agent produces it; visual_dev_node is partial |
| `EnvironmentBible` | `environment.py` | No agent produces it; visual_dev_node is partial |
| `CameraLanguageBible` | `camera.py` | No agent produces it; visual_dev_node is partial |
| `StyleBible` | *(no schema)* | Schema doesn't exist yet |
| `MasterFilmMatrix` | `matrix.py` | `shot_bible_node` is flag-only |
| `ContinuityLedger` | `continuity.py` | No writer |
| `PromptRegistry` | `prompt.py` | No writer |
| `GenerationPlan` | *(no schema)* | Schema doesn't exist; `gen_planning_node` is flag-only |
| `ValidationReport` | `validation.py` | `qc_node` is flag-only |
| `BudgetState` | `budget.py` | No writer |

---

## Related Docs

- `docs/data-storage/implementation-plan/README.md` — Phased plan to close remaining gaps
- `docs/data-storage/analysis.md` — Review of the original `film-data-storage-complete.md`
- `docs/reference-image/implementation-review.md` — Reference image pipeline implementation status (12 phases)
- `docs/openclaw-mcp-operator-guide.md` — Step 5 documents the `generate_reference_images` MCP tool output structure
