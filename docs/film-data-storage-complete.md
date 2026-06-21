# Film Pipeline Data Storage — Complete Artifact Map

> **Purpose:** A single-source-of-truth listing every file/artifact type the pipeline
> produces, in what format, where it lives on disk, and what Pydantic schema governs it.
>
> This covers all 11 phases from intake through delivery. Use this as the reference for
> building storage operations and checking completeness.

---

## Quick Summary

| Format | Where | What |
|--------|-------|------|
| `.json` | `projects/{slug}/{phase-dir}/` | All structured artifacts via `ArtifactStore` |
| `.png` | `projects/{slug}/references/` | Reference images, composite sheets, master frames |
| `.mp4` | `projects/{slug}/07-generated-assets/shots/{shot_id}/` | Generated video clips |
| `.png` (frames) | `projects/{slug}/07-generated-assets/shots/{shot_id}/` | Last frames, mid frames |
| `.json` | `projects/{slug}/asset-manifest.json` | Flat file listing all binary assets |
| `.meta.json` (sidecar) | Next to every `.png` or `.mp4` | `ArtifactMetadata` + type-specific metadata |
| `.wav` / `.mp3` | `projects/{slug}/09-post/audio/` | Audio stems |
| `.srt` | `projects/{slug}/09-post/subtitles/` | Subtitle files |
| `.mp4` | `projects/{slug}/10-delivery/` | Final export |

**Key rule:** JSON artifacts go through `ArtifactStore.save()` which writes both
`{id}.v{version}.json` and `{id}.v{version}.json.meta.json` sidecar. Binary files go
through type-specific helpers that write the binary + `.meta.json` sidecar.

---

## Phase-by-Phase Artifact Map

### Phase: Intake (`01-intake/`)

| Artifact | Schema | Format | File Pattern | Notes |
|----------|--------|--------|--------------|-------|
| Project Profile | `ProjectProfile` | JSON | `project_profile.v1.json` | Identity + runtime + aspect + budget + provider prefs |
| Project Config | `ProjectConfig` | JSON | `project_config.v1.json` | Resolved config after intake (locked contract) |

**State refs set:** `project_id`, `profile_ref`, `resolved_config`

**Current status:** ✅ `intake_node` produces profile. Config gets resolved downstream.

---

### Phase: Constitution (`02-constitution/`)

| Artifact | Schema | Format | File Pattern | Notes |
|----------|--------|--------|--------------|-------|
| Film Constitution | `FilmConstitution` | JSON | `film_constitution.v1.json` | Theme, tone, emotional promise, visual language, camera philosophy, character truths, taboo mistakes |

**State refs set:** `constitution_ref`

**Current status:** ✅ `constitution_node` produces this.

---

### Phase: Development (`03-development/`)

| Artifact | Schema | Format | File Pattern | Notes |
|----------|--------|--------|--------------|-------|
| Logline | `Logline` | JSON | `logline.v1.json` | One-sentence + optional hook |
| Premise | `Premise` | JSON | `premise.v1.json` | Central dramatic question |
| Act Map | `ActMap` | JSON | `act_map.v1.json` | 3-act summary |
| Treatment | `Treatment` | JSON | `treatment.v1.json` | Long-form prose + themes + act map |
| Scene List | `SceneList` | JSON | `scene_list.v1.json` | Ordered list of `SceneIntent` with dramatic function, emotional shift, conflict, outcome |
| Story Bible | `StoryBible` | JSON | `story_bible.v1.json` | Aggregate: logline + premise + treatment + act map + scene list + setup/payoff map + unresolved threads |

**State refs set:** `treatment_ref`, `scene_list_ref`, `story_bible_ref`

**Current status:** ✅ `development_node` produces treatment + scene list.
`story_bible` is saved later during script phase.

---

### Phase: Script (`04-script/`)

| Artifact | Schema | Format | File Pattern | Notes |
|----------|--------|--------|--------------|-------|
| Script | `Script` | JSON | `script.v1.json` | Full screenplay: scenes with action lines + dialogue + intent refs |
| Dialogue lines | `DialogueLine` (inline) | JSON | (inside Script) | character_id + line + direction |
| Scene intents | `SceneIntent` (inline) | JSON | (inside SceneList) | Already saved in development phase |

**State refs set:** `script_ref`

**Current status:** ✅ `script_node` produces story bible + script.

---

### Phase: Character, Environment, Camera Bibles (`04-visual-dev/`)

These are **not yet saved as separate artifacts** in the node code. Currently
`visual_dev_node` saves only a `reference_index`. The bibles should be produced
before or alongside references.

| Artifact | Schema | Format | File Pattern | Notes |
|----------|--------|--------|--------------|-------|
| Character Bible | `CharacterBible` | JSON | `character_bible.v1.json` | Per-character: identity (with locked prompt block), voice, wardrobe, emotional arc, relationships, reference assets |
| Environment Bible | `EnvironmentBible` | JSON | `environment_bible.v1.json` | Per-environment: locked prompt block, invariants, zones, viewpoints, lighting states, palette, fingerprint |
| Camera Language Bible | `CameraLanguageBible` | JSON | `camera_language_bible.v1.json` | Profiles: lens, framing, movement, DOF, composition rules, emotional meaning |
| Style Bible | (not yet a schema) | JSON | `style_bible.v1.json` | ❌ Missing schema — color palette, texture, grain, visual mood |
| Reference Strategy | `ReferenceStrategy` | JSON | `reference_strategy.v1.json` | Priorities, provider plan, cost estimate |

**State refs set:** `visual_refs` (only `reference_index` currently)

**Current status:** ⚠️ Partial. `visual_dev_node` saves `reference_index` but not
the individual bibles. Need to add `character_bible_ref`, `environment_bible_ref`,
`camera_bible_ref`.

---

### Phase: Visual Development — References (`04-visual-dev/` continued)

| Artifact | Schema | Format | File Pattern | Notes |
|----------|--------|--------|--------------|-------|
| Reference Index | `ReferenceIndex` | JSON | `reference_index.v1.json` | Aggregate registry of all approved references |
| Reference Index Entry | `ReferenceIndexEntry` | JSON | (inside index) | Per-sheet: id, path, type, subject, validation, AI usability, provider, locked |
| Reference Image (binary) | none (raw PNG) | PNG | `references/{type}/{subject}/{sheet}.png` | The actual composite sheet image |
| Master Frame (binary) | none (raw PNG) | PNG | `references/{type}/{subject}/master-frames/{frame}.png` | Individual base frame before compositing |
| Frame Metadata | `ReferenceFrame` (❌ missing) | JSON | `.png.meta.json` sidecar | Provider, tier, seed, prompt, validation score, retries |
| Composite Sheet Manifest | `CompositeSheetManifest` (❌ missing) | JSON | `{sheet}.sheet.json` beside PNG | Tile layout, template type, frame sources |
| Validation Report | `ValidationReport` | JSON | `08-validation/validation_ref_sheet.v1.json` | Per-sheet scores, blocking issues, recommended actions |
| Consensus Report | `ConsensusReport` | JSON | `08-validation/consensus_ref_sheet.v1.json` | Multi-model review aggregation |
| Review Package | `ReviewPackage` | JSON | `08-validation/review_package_sheet.v1.json` | Human review: sheet + validation + risks + recommendation |

**Current status:** ⚠️ Schemas exist for index, validation, consensus, review
package. Missing: `ReferenceFrame`, `CompositeSheetManifest`. No binary save/load
functions. No sidecar writer.

---

### Phase: Shot Bible (`05-shot-bible/`)

| Artifact | Schema | Format | File Pattern | Notes |
|----------|--------|--------|--------------|-------|
| Master Film Matrix | `MasterFilmMatrix` | JSON | `master_film_matrix.v1.json` | Every shot as a row: scene, characters, env, camera, refs, chaining, validation |
| Matrix Row | `MasterFilmMatrixRow` | JSON | (inside matrix) | Per-shot: duration, priority, risk, prompt_ref, provider_plan_ref, generation_order |
| Coverage Group | `CoverageGroup` | JSON | (inside matrix) | Multi-angle coverage of same story moment |
| Chaining Config | `ChainingConfig` | JSON | (inside matrix row) | input_frame_ref, re_anchor, return_last_frame |
| Continuity Ledger | `ContinuityLedger` | JSON | `continuity_ledger.v1.json` | Per-shot state_in/state_out: character, prop, wardrobe, environment, lighting |
| Prompt Registry | `PromptRegistry` | JSON | `prompt_registry.v1.json` | All RCTCO prompt packages indexed by shot_id |
| RCTCO Prompts | `RCTCOPrompt` / `PromptRegistryEntry` | JSON | (inside registry) | Role, Core Task, Context, Constraints, Output format |

**State refs set:** `shot_matrix_ref`

**Current status:** ⚠️ `shot_bible_node` exists (flag-only). Schemas complete.
No actual agent writes these yet.

---

### Phase: Generation Planning (`06-generation-plan/`)

| Artifact | Schema | Format | File Pattern | Notes |
|----------|--------|--------|--------------|-------|
| Generation Plan | (not yet a schema) | JSON | `generation_plan.v1.json` | ❌ Missing — ordered list of shots with provider assignment |
| Cost Estimate | `CostEstimate` | JSON | `cost_estimate.v1.json` | Estimated cost per batch |
| Budget State | `BudgetState` | JSON | `budget_state.v1.json` | Running spend tracker: cap, spent, per-phase caps |

**Current status:** ⚠️ `gen_planning_node` exists (flag-only). No actual agent writes.

---

### Phase: Generation (`07-generated-assets/`)

| Artifact | Schema | Format | File Pattern | Notes |
|----------|--------|--------|--------------|-------|
| Generation Request | `GenerationRequest` | JSON | `shots/{shot_id}/generation_request.v1.json` | Contains idempotency_key to prevent duplicate paid submissions |
| Generation Ledger | `GenerationLedger` | JSON | `generation_ledger.v1.json` | Aggregate: every submit + poll + cost |
| Ledger Row | `GenerationLedgerRow` | JSON | (inside ledger) | Per-submit: provider, model, status, cost, output_refs, resume_token |
| Generated Video Clip | `none` (raw MP4) | MP4 | `shots/{shot_id}/S{id}.v{take}.mp4` | The actual AI-generated clip |
| Last Frame (from video) | none (raw PNG) | PNG | `shots/{shot_id}/S{id}.v{take}.last_frame.png` | Last frame used for chaining to next shot |
| Mid Frame (from video) | none (raw PNG) | PNG | `shots/{shot_id}/S{id}.v{take}.mid_frame.png` | Optional mid-frame for re-anchoring |
| Clip Metadata Sidecar | (inline in ledger) | JSON | `.mp4.meta.json` | Duration, resolution, provider, model, actual cost |
| Resume Token | `ResumeToken` | JSON | `shots/{shot_id}/resume_token.v1.json` | Runtime checkpoint for interruption recovery |

**Current status:** ⚠️ Schema-only. No actual generation agent writes these yet.

---

### Phase: QC / Validation (`08-validation/`)

| Artifact | Schema | Format | File Pattern | Notes |
|----------|--------|--------|--------------|-------|
| Validation Report | `ValidationReport` | JSON | `validation_report_{scope}.v1.json` | Structured: validator_id, scope, modalities, score, status, blocking_issues, actions |
| Validation Issue | `ValidationIssue` | JSON | (inside report) | code + message + severity |
| Consensus Report | `ConsensusReport` | JSON | `consensus_report_{scope}.v1.json` | Multiple reviewer scores, agreement level, disagreements |
| Reviewer Score | `ReviewerScore` | JSON | (inside consensus) | model_id + validator_id + score + status |
| Validation Ledger | `ValidationLedgerEntry` | JSON | `validation_ledger.v1.json` | Stored validation record with consensus |
| Issue Record | (not yet a schema) | JSON | `issue_record.v1.json` | ❌ Missing — cross-cutting issue tracking |

**Current status:** ⚠️ Schema-only. No actual validator writes these yet.

---

### Phase: Post-Production (`09-post/`)

| Artifact | Schema | Format | File Pattern | Notes |
|----------|--------|--------|--------------|-------|
| Assembly Manifest | `AssemblyManifest` | JSON | `assembly_manifest.v1.json` | Clip order, transitions, audio plan, color plan, missing assets |
| Clip Order Entry | `ClipOrderEntry` | JSON | (inside manifest) | shot_id → source_asset_ref, in/out timecodes, coverage role |
| Transition Plan | `TransitionPlan` | JSON | (inside manifest) | Between-shot transitions: type, duration |
| Audio Plan | `AudioPlan` | JSON | (inside manifest) | Music/SFX/dialogue tracks, cue points |
| Color Plan | `ColorPlan` | JSON | (inside manifest) | Per-scene grading |
| Audio Stem (binary) | none (raw WAV/MP3) | WAV/MP3 | `audio/music_{id}.wav`, `audio/sfx_{id}.wav` | Individual audio tracks |
| Subtitle Cues | none | SRT | `subtitles/{lang}.srt` | Generated subtitle file |
| Review Cut (binary) | none | MP4 | `review_cut.v1.mp4` | Assembled but not finalized cut |

**Current status:** ⚠️ `assembly_manifest_node` exists (flag-only). Schemas complete
for manifest but audio/subtitle/color agents exist as stubs only.

---

### Phase: Delivery (`10-delivery/`)

| Artifact | Schema | Format | File Pattern | Notes |
|----------|--------|--------|--------------|-------|
| Delivery Package | `DeliveryPackage` | JSON | `delivery_package.v1.json` | Top-level: final_video_ref, review_cut_ref, manifest, archive_refs |
| Delivery Manifest | `DeliveryManifest` | JSON | (inside package) | File listing: paths + kinds + subtitles + audio stems + stills |
| Final Cut (binary) | none | MP4 | `final_cut.v1.{ext}` | Final rendered film |
| Delivery stills (binary) | none | PNG | `stills/{shot_id}.png` | Selected frame stills for posters/thumbnails |

**Current status:** ⚠️ `delivery_node` exists (flag-only). Schemas complete.

---

### Cross-Cutting Artifacts

| Artifact | Schema | Format | Location | Notes |
|----------|--------|--------|----------|-------|
| Asset Manifest | `AssetManifest` | JSON | `projects/{slug}/asset-manifest.json` | Flat file listing all binary assets (images + videos + audio) |
| Checkpoint | `CheckpointMetadata` | JSON | `projects/{slug}/versions/checkpoints/` | Phase gate snapshot: artifact versions, graph state, budget |
| Rollback Record | `RollbackRecord` | JSON | `projects/{slug}/versions/rollbacks/` | Audit trail of rollbacks |
| Invalidation Report | `InvalidationReport` | JSON | `projects/{slug}/versions/invalidations/` | What gets invalidated by a change |
| Approval Record | `ApprovalRecord` | JSON | `projects/{slug}/phase-dir/` | Human approval at each phase gate |
| Revision Request | `RevisionRequest` | JSON | `projects/{slug}/phase-dir/` | Human-requested revisions |
| Handoff Record | (inline in graph state) | JSON | Runtime only (in memory) | Agent routing decisions for audit trail |
| KB Context Packet | `KBContextPacket` | JSON | `projects/{slug}/kb-packets/` | KB slices injected into agent prompts |

---

## Complete File Tree (What Should Exist)

```
projects/{slug}/
│
├── asset-manifest.json                         ← Flat binary asset list
├── state/                                       ← Graph runtime state snapshots
│
├── 01-intake/
│   ├── project_profile.v1.json
│   ├── project_profile.v1.json.meta.json
│   ├── project_config.v1.json
│   └── project_config.v1.json.meta.json
│
├── 02-constitution/
│   ├── film_constitution.v1.json
│   └── film_constitution.v1.json.meta.json
│
├── 03-development/
│   ├── logline.v1.json
│   ├── treatment.v1.json
│   ├── treatment.v1.json.meta.json
│   ├── scene_list.v1.json
│   ├── scene_list.v1.json.meta.json
│   ├── act_map.v1.json
│   └── premise.v1.json
│
├── 04-script/
│   ├── story_bible.v1.json
│   ├── story_bible.v1.json.meta.json
│   ├── script.v1.json
│   └── script.v1.json.meta.json
│
├── 04-visual-dev/
│   ├── character_bible.v1.json
│   ├── character_bible.v1.json.meta.json
│   ├── environment_bible.v1.json
│   ├── environment_bible.v1.json.meta.json
│   ├── camera_language_bible.v1.json
│   ├── camera_language_bible.v1.json.meta.json
│   ├── style_bible.v1.json               (TODO: needs schema)
│   ├── reference_strategy.v1.json
│   ├── reference_index.v1.json
│   └── reference_index.v1.json.meta.json
│
├── references/
│   ├── index.json                              ← Lightweight mirror of reference_index artifact
│   ├── characters/
│   │   └── CHAR_001/
│   │       ├── identity-sheet.png
│   │       ├── identity-sheet.png.meta.json
│   │       ├── identity-sheet.sheet.json       ← Tile layout manifest
│   │       ├── costume-sheet.png
│   │       ├── expression-sheet.png
│   │       └── master-frames/
│   │           ├── leo-front.png
│   │           ├── leo-front.png.meta.json     ← Frame metadata sidecar
│   │           ├── leo-3quarter-left.png
│   │           ├── leo-3quarter-left.png.meta.json
│   │           └── ...
│   ├── environments/
│   │   └── ENV_001/
│   │       ├── environment-board.png
│   │       ├── environment-board.png.meta.json
│   │       └── master-frames/...
│   ├── props/...
│   ├── style/
│   │   ├── visual-style-board.png
│   │   ├── camera-style-board.png
│   │   └── color-palette.png
│   └── scale/
│       └── scale-sheet.png
│
├── 05-shot-bible/
│   ├── master_film_matrix.v1.json
│   ├── master_film_matrix.v1.json.meta.json
│   ├── continuity_ledger.v1.json
│   ├── continuity_ledger.v1.json.meta.json
│   ├── prompt_registry.v1.json
│   └── prompt_registry.v1.json.meta.json
│
├── 06-generation-plan/
│   ├── generation_plan.v1.json
│   ├── cost_estimate.v1.json
│   └── budget_state.v1.json
│
├── 07-generated-assets/
│   ├── generation_ledger.v1.json
│   ├── generation_ledger.v1.json.meta.json
│   └── shots/
│       └── S001/
│           ├── generation_request.v1.json
│           ├── S001.v1.mp4
│           ├── S001.v1.mp4.meta.json
│           ├── S001.v1.last_frame.png
│           ├── S001.v1.last_frame.png.meta.json
│           ├── S001.v1.mid_frame.png
│           ├── S001.v2.mp4                       ← Retake
│           └── resume_token.v1.json
│
├── 08-validation/
│   ├── validation_ledger.v1.json
│   ├── validation_report_reference_index.v1.json
│   ├── validation_report_sheet_leo.v1.json
│   ├── consensus_report_sheet_leo.v1.json
│   ├── validation_report_clip_S001.v1.json
│   ├── review_package_leo_sheet.v1.json
│   └── issue_record.v1.json                     (TODO: needs schema)
│
├── 09-post/
│   ├── assembly_manifest.v1.json
│   ├── audio/
│   │   ├── music_bg.wav
│   │   └── sfx_ambient.wav
│   ├── subtitles/
│   │   └── en.srt
│   └── review_cut.v1.mp4
│
├── 10-delivery/
│   ├── delivery_package.v1.json
│   ├── delivery_package.v1.json.meta.json
│   ├── final_cut.v1.mp4
│   └── stills/
│       ├── S001.png
│       └── S024.png
│
└── versions/
    ├── checkpoints/
    │   └── checkpoint_constitution.v1.json
    ├── rollbacks/
    │   └── rollback_2026_06_21.v1.json
    └── invalidations/
        └── invalidation_char_desc_change.v1.json
```

---

## What Each Schema Maps To (Existence Check)

### ✅ Schemas that exist and are complete

| Schema | File | Used by artifact? |
|--------|------|-------------------|
| `ProjectIdentity` | `project.py` | ✅ `intake_node` writes profile |
| `ProjectProfile` | `project.py` | ✅ |
| `ProjectConfig` | `project.py` | ✅ |
| `FilmConstitution` | `film_constitution.py` | ✅ `constitution_node` writes |
| `Logline` | `story_bible.py` | ✅ |
| `Premise` | `story_bible.py` | ✅ |
| `ActMap` | `story_bible.py` | ✅ |
| `Treatment` | `story_bible.py` | ✅ `development_node` writes |
| `SceneList` | `story_bible.py` | ✅ |
| `StoryBible` | `story_bible.py` | ✅ `script_node` writes |
| `Script` | `script.py` | ✅ |
| `CharacterBible` | `character.py` | ⚠️ Schema exists, no agent writes it yet |
| `EnvironmentBible` | `environment.py` | ⚠️ Schema exists, no agent writes it yet |
| `CameraLanguageBible` | `camera.py` | ⚠️ Schema exists, no agent writes it yet |
| `ReferenceStrategy` | `reference.py` | ⚠️ Schema exists |
| `ReferenceIndex` | `reference.py` | ⚠️ `visual_dev_node` writes `reference_index` |
| `ReferenceIndexEntry` | `reference.py` | ✅ Inside ReferenceIndex |
| `ReferenceValidationSummary` | `reference.py` | ✅ Inside ReferenceIndexEntry |
| `ReferenceAIUsability` | `reference.py` | ✅ Inside ReferenceIndexEntry |
| `MasterFilmMatrix` | `matrix.py` | ⚠️ `shot_bible_node` is flag-only |
| `ContinuityLedger` | `continuity.py` | ⚠️ No writer |
| `PromptRegistry` | `prompt.py` | ⚠️ No writer |
| `GenerationRequest` | `generation.py` | ⚠️ No writer |
| `GenerationLedger` | `generation.py` | ⚠️ No writer |
| `ResumeToken` | `generation.py` | ⚠️ No writer |
| `ValidationReport` | `validation.py` | ⚠️ No writer |
| `ConsensusReport` | `validation.py` | ⚠️ No writer |
| `ReviewPackage` | `approval.py` | ⚠️ No writer |
| `ApprovalRecord` | `approval.py` | ✅ Written at phase gates |
| `RevisionRequest` | `approval.py` | ⚠️ No writer |
| `BudgetState` | `budget.py` | ⚠️ No writer |
| `AssemblyManifest` | `assembly.py` | ⚠️ `assembly_manifest_node` is flag-only |
| `DeliveryPackage` | `delivery.py` | ⚠️ `delivery_node` is flag-only |
| `CheckpointMetadata` | `checkpoint.py` | ⚠️ No writer |
| `AssetManifest` | `manifest.py` | ⚠️ Written but never read |

### ❌ Schemas or features that don't exist yet

| What's missing | Why it matters |
|---------------|----------------|
| `StyleBible` schema | Visual style (palette, grain, mood) has no schema at all |
| `ReferenceFrame` schema | Individual base frames have no metadata sidecar |
| `CompositeSheetManifest` schema | Tile layout and frame provenance not tracked |
| `GenerationPlan` schema | Ordered shot execution plan with provider routing |
| `IssueRecord` schema | Cross-cutting issue tracking |
| Binary image save/load functions | No `save_reference_image()` in `ArtifactStore` |
| Sidecar `.meta.json` writers | Frame metadata files never produced |
| Continuity ledger writer | Schema exists, nothing writes `ContinuityLedger` |
| Prompt registry writer | Schema exists, nothing writes `PromptRegistry` |
| Validation report writer | Schema exists, nothing writes `ValidationReport` |
| Generation ledger writer | Schema exists, nothing writes `GenerationLedger` |
| Budget state writer | Schema exists, nothing writes `BudgetState` |

### Current node maturity

| Node | Produces artifacts? | Status |
|------|-------------------|--------|
| `intake_node` | ✅ `ProjectProfile` + `ProjectConfig` | Complete |
| `constitution_node` | ✅ `FilmConstitution` | Complete |
| `development_node` | ✅ `Treatment`, `SceneList` | Complete |
| `script_node` | ✅ `StoryBible`, `Script` | Complete |
| `visual_dev_node` | ⚠️ `ReferenceIndex` only (no bibles, no binaries) | Partial |
| `shot_bible_node` | ❌ Flag only | Skeleton |
| `gen_planning_node` | ❌ Flag only | Skeleton |
| `generation_node` | ❌ Flag only | Skeleton |
| `qc_node` | ❌ Flag only | Skeleton |
| `post_node` | ❌ Flag only | Skeleton |
| `delivery_node` | ❌ Flag only | Skeleton |

---

## Storage Rules Summary

1. **JSON artifacts** → `ArtifactStore.save()` writes `{phase}/{id}.v{version}.json` +
   `{id}.v{version}.json.meta.json`
2. **Binary images (reference sheets, master frames)** → type-specific helpers write to
   `references/{subject-type}/{subject-id}/` with `.png.meta.json` sidecar
3. **Binary videos (generated clips)** → `generated_asset_dir()` writes to
   `07-generated-assets/shots/{shot-id}/` with `.mp4.meta.json` sidecar
4. **Binary audio** → `09-post/audio/`
5. **AssetManifest** is a flat index of all binaries, regenerated on each phase
6. **Sidecar metadata** always matches the `ArtifactMetadata` shape + type-specific fields
7. **State refs** (`project_id`, `constitution_ref`, `treatment_ref`, etc.) are
   maintained in LangGraph state so nodes can load upstream artifacts
8. **Versions** use `ArtifactVersion` chain: candidates → approve → supersede
