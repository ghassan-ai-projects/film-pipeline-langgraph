# Reference Data Storage — What We Store, Where, and What's Missing

> **Audience:** Coding agent implementing the reference image flow in `film-pipeline-langgraph`.
> This analyzes the existing storage system against what the legacy pipeline actually produced.

---

## TL;DR

The LangGraph project has a **strong schema foundation** (`reference.py`, `matrix.py`,
`artifact.py`, `validation.py`) but the **actual storage isn't wired up** for reference
images. Specifically:

1. **Images (PNGs)** have no home in the artifact store — it writes `.json` only
2. **The `AssetManifest` exists but is disconnected** from the artifact store and reference index
3. **No reference-specific save/load pipeline** — `ReferenceIndexEntry` has `asset_path` as a string but nothing writes/reads it
4. **Composite sheet binary data** doesn't flow through the artifact system at all

---

## What We Already Store

### 1. `artifacts/store.py` — `ArtifactStore`

The canonical write path. Everything flows through here.

**What it stores:** Pydantic models as `.json` files.

**On-disk layout:**
```
projects/{project_id}/
├── 04-visual-dev/
│   ├── reference_strategy.v1.json
│   └── reference_strategy.v1.json.meta.json
├── 05-shot-bible/
│   ├── master_film_matrix.v1.json
│   └── continuity_ledger.v1.json
├── 07-generated-assets/
│   └── shots/
│       └── S001/
│           └── (generated clips)
├── references/
│   ├── characters/
│   ├── environments/
│   ├── props/
│   ├── style/
│   └── scale/
```

**Phase mapping (from `paths.py`):**
```
visual_dev   → 04-visual-dev   ← Reference strategy, reference index
shot_bible   → 05-shot-bible   ← Master film matrix, continuity ledger
gen_planning → 06-generation-plan
generation   → 07-generated-assets
qc           → 08-validation   ← Validation reports
```

### 2. Artifact schemas already defined

| Schema | File | Has everything we need? |
|--------|------|------------------------|
| `ReferenceIndexEntry` | `schemas/reference.py` | ✅ **Yes.** Has `reference_id`, `asset_path`, `asset_type`, `subject_type`, `subject_id`, `approved_for`, `quality_score`, `provider`, `tier`, `frame_role`, `expression`, `lighting`, `prompt_text`, `source_frames`, `moderation_risk`, `generation_status`, `validation`, `ai_usability`, `issues`, `locked`, `version` |
| `ReferenceIndex` | `schemas/reference.py` | ✅ Aggregate of entries |
| `ReferenceStrategy` | `schemas/reference.py` | ✅ Priorities + provider plan + cost estimate |
| `MasterFilmMatrixRow` | `schemas/matrix.py` | ✅ `reference_strategy_ref`, character + environment + camera refs, chaining config, validation refs |
| `MasterFilmMatrix` | `schemas/matrix.py` | ✅ Aggregate of rows + coverage groups |
| `ContinuityLedgerEntry` | `schemas/continuity.py` | ✅ Per-shot state in/out, character/prop/wardrobe/environment/lighting state, risks |
| `ContinuityLedger` | `schemas/continuity.py` | ✅ Aggregate of entries |
| `ValidationReport` | `schemas/validation.py` | ✅ Validator output with scores, issues, actions |
| `ConsensusReport` | `schemas/validation.py` | ✅ Multi-model aggregation |
| `RCTCOPrompt` | `schemas/prompt.py` | ✅ Role/Core Task/Context/Constraints/Output |
| `PromptRegistryEntry` | `schemas/prompt.py` | ✅ With artifact_refs, shot_id |
| `GenerationRequest` | `schemas/generation.py` | ✅ With `reference_refs`, `idempotency_key` |
| `GenerationLedgerRow` | `schemas/generation.py` | ✅ With `output_refs`, cost tracking |
| `ArtifactMetadata` | `schemas/artifact.py` | ✅ Type, phase, version, status, parents, validation_refs |
| `ArtifactType` | `schemas/_base.py` | ✅ Has `REFERENCE_SHEET`, `REFERENCE_INDEX`, `MATRIX_ROW`, `VALIDATION_REPORT`, etc. |

### 3. `AssetManifest` — flat file list

`artifacts/manifest.py` provides a simple flat list of `AssetEntry` per project with `kind`
values: `reference_sheet`, `generated_clip`, `last_frame`, `mid_frame`, `audio_stem`.

Stored as `asset-manifest.json` in project root.

---

## What's Missing (Gaps to Fill)

### Gap 1: Binary image files have no artifact path

**Problem:** `ArtifactStore.save()` writes `.json` files only. Reference sheets are binary
PNGs. The store has no `save_image()` method, and there's no convention for where binaries
go relative to the JSON artifact.

**The `reference_dir()` function in `paths.py` returns:**
```python
def reference_dir(project_slug: str, ref_type: str) -> Path:
    return project_dir(project_slug) / "references" / ref_type
```

This points to `projects/{slug}/references/{ref_type}/` but **nothing writes to it**. The
reference index entries store `asset_path` as a string, but there's no code that actually
saves a PNG there and links it.

**What we need:**
```python
# In ArtifactStore or a new ReferenceImageStore:
def save_reference_image(project_id: str, image_bytes: bytes,
                          ref_type: str, filename: str) -> str:
    """Save a PNG to references/{ref_type}/{filename} and return path."""
    dest = reference_dir(project_id, ref_type) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(image_bytes)
    return str(dest.relative_to(project_dir(project_id)))
```

### Gap 2: No wire-up between reference index and artifact store

**Problem:** There's a rich `ReferenceIndexEntry` schema but no `save_reference_index()`
or `load_reference_index()` that connects the JSON data to the binary images.

**The pipeline needs these functions:**
```python
# Save the reference index as an artifact
def save_reference_index(project_id: str, index: ReferenceIndex,
                         version: int, created_by: str) -> None

# Save a single reference sheet + register it
def register_reference_sheet(project_id: str, entry: ReferenceIndexEntry,
                             image_bytes: bytes, created_by: str) -> None

# Validate a sheet and store the report
def save_validation_report(project_id: str, report: ValidationReport,
                           reference_id: str) -> None
```

### Gap 3: Validation reports need to reference specific reference entries

**Problem:** `ValidationReport` has `artifact_refs: list[str]` but there's no helper to
generate proper references to `ReferenceIndexEntry` objects. The validation system should
link back to the specific reference sheet and its constituent frames.

### Gap 4: No continuity ledger — the shot-matrix integration

**Problem:** The legacy TPS pipeline had a `continuity-ledger.json` with per-shot state_in,
state_out, reference_images[], character_state, prop_state, etc. The schema
`ContinuityLedger` exists but hasn't been wired to the reference index.

**MasterFilmMatrixRow** already has `reference_strategy_ref` but not a direct
`reference_refs: list[str]` for which sheets each shot actually uses. The legacy used
`reference_images` as a flat list of file paths.

### Gap 5: AssetManifest is disconnected

**Problem:** `AssetManifest` stores a flat list of `AssetEntry` but:
- No one reads it after writing
- No cross-reference with `ReferenceIndexEntry`
- No lifecycle (versioning, supersede) — it's a static snapshot
- `kind` values are loose strings, not constrained by `ArtifactType`

### Gap 6: No per-frame tracking

**Problem:** `ReferenceIndexEntry` has `source_frames: list[str]` but no schema exists for
individual base frames before they're composited into a sheet. The legacy pipeline tracked
frames like `leo-front.png`, `leo-3quarter-left.png` etc. as individual artifacts with
their own provider, tier, validation status.

We need a `ReferenceFrame` schema:
```python
class ReferenceFrame(SchemaBase):
    """One base frame before composite assembly."""
    frame_id: str        # e.g. "leo-front"
    subject_id: str      # e.g. "char:leo"
    role: str            # e.g. "front-face", "3-4-left", "expression-neutral"
    asset_path: str      # relative path under references/
    provider: str
    tier: str            # fast | standard | ultra
    seed: int | None
    prompt_text: str
    validation_score: float
    validation_report_ref: str | None
    retries_used: int
    status: str          # generated | validated | failed | used_in_composite
```

### Gap 7: No composite sheet template artifacts

**Problem:** The composite sheet is a layout — it's not just the output image. The legacy
pipeline described templates (identity, environment, scale) but these were hardcoded in the
compositing script. No template metadata was saved alongside the output.

We could save a `CompositeSheetManifest` with each output:
```json
{
  "sheet_id": "CHAR_01-leo-identity-sheet",
  "template": "character_identity",
  "tiles": [
    {"slot": "front_face", "frame_id": "leo-front", "position": [0, 0], "size": [640, 640]},
    {"slot": "three_quarter_left", "frame_id": "leo-3q-left", "position": [640, 0], "size": [320, 320]},
    ...
  ],
  "output_path": "references/characters/CHAR_001/identity-sheet.png",
  "resolution": "2048x2048"
}
```

The legacy pipeline never saved this — we can add it.

### Gap 8: No review package artifacts

**Problem:** Human review is required before locking main character sheets. The legacy
pipeline had review practices but no structured review package schema. The new pipeline
should produce a `ReviewPackage` artifact that bundles:
- The reference sheet image(s)
- Validation scores from each model
- Disagreements between models
- What shots/scenes depend on it
- Orchestrator recommendation
- A `human_review_required` flag

---

## Storage Structure Recommendation

### Proposed on-disk layout

```
projects/{project_id}/
├── 04-visual-dev/
│   ├── reference_strategy.v1.json
│   ├── reference_strategy.v1.json.meta.json
│   └── reference_index.v1.json         ← All registered references
│
├── 08-validation/
│   ├── validation_report_ref_strat.v1.json
│   ├── validation_report_leo_sheet.v1.json
│   ├── validation_report_environment.v1.json
│   ├── consensus_report_leo_sheet.v1.json
│   └── review_package_leo.v1.json
│
├── references/
│   ├── index.json                       ← Lightweight reference index (mirrors artifact)
│   ├── characters/
│   │   └── CHAR_001/
│   │       ├── identity-sheet.png       ← Composite sheet (binary image)
│   │       ├── costume-sheet.png
│   │       ├── expression-sheet.png
│   │       ├── master-frames/           ← Individual base frames
│   │       │   ├── leo-front.png
│   │       │   ├── leo-3quarter-left.png
│   │       │   ├── leo-front.meta.json  ← Frame metadata (provider, seed, score)
│   │       │   ├── ...
│   │       └── sheet-manifest.json      ← Tile layout metadata
│   ├── environments/
│   │   └── ENV_001/
│   │       ├── environment-board.png
│   │       ├── lighting-board.png
│   │       ├── master-frames/
│   │       └── sheet-manifest.json
│   ├── props/
│   ├── style/
│   └── scale/
│
├── asset-manifest.json                  ← Flat file list (existing)
│
└── 05-shot-bible/
    ├── master_film_matrix.v1.json
    ├── continuity_ledger.v1.json
    └── prompt_registry.v1.json
```

### File format summary

| What | Format | Where | Schema |
|------|--------|-------|--------|
| Reference strategy | `.json` | `04-visual-dev/` | `ReferenceStrategy` |
| Reference index | `.json` | `04-visual-dev/` + mirror in `references/` | `ReferenceIndex` + `ReferenceIndexEntry` |
| Master film matrix | `.json` | `05-shot-bible/` | `MasterFilmMatrix` + `MasterFilmMatrixRow` |
| Continuity ledger | `.json` | `05-shot-bible/` | `ContinuityLedger` + `ContinuityLedgerEntry` |
| Prompt registry | `.json` | `05-shot-bible/` | `PromptRegistry` |
| Validation reports | `.json` | `08-validation/` | `ValidationReport` |
| Consensus reports | `.json` | `08-validation/` | `ConsensusReport` |
| Review packages | `.json` | `08-validation/` | (new schema) |
| Reference sheets | `.png` | `references/{type}/{subject}/` | Binary image |
| Base frames | `.png` | `references/{type}/{subject}/master-frames/` | Binary image |
| Frame metadata | `.json` | Sidecar next to each frame `.png` | (new `ReferenceFrame` schema) |
| Sheet tile layout | `.json` | Next to sheet `.png` | (new `CompositeSheetManifest`) |
| Asset manifest | `.json` | project root | `AssetManifest` |

### Key principle: sidecar metadata

Every binary file (PNG) gets a `.png.meta.json` sidecar with:
- **Frame level**: provider, tier, seed, prompt_text, validation_score, retries
- **Sheet level**: template type, tile map, base frames used, overall validation scores

This keeps the artifact store JSON-only while binaries live in the `references/` tree with
self-contained metadata.

---

## Wire-up Checklist for Coding Agent

Here's what needs building, in dependency order:

### Phase 1 — Store upgrades
1. Add `save_reference_image()` to `ArtifactStore` or new `ReferenceImageStore`
2. Add `ReferenceFrame` schema to `schemas/reference.py`
3. Add `CompositeSheetManifest` schema to `schemas/reference.py`
4. Add `ReviewPackage` schema to `schemas/validation.py`
5. Add `save_frame_metadata()` / `read_frame_metadata()` sidecar helpers

### Phase 2 — Reference index wiring
6. Add `save_reference_index()` to save `ReferenceIndex` as artifact
7. Add `register_reference_sheet()` to save binary + create `ReferenceIndexEntry`
8. Add `save_validation_report()` to store validation results + link to reference
9. Update `AssetManifest` to cross-reference with `ReferenceIndex`

### Phase 3 — Matrix integration
10. Wire `MasterFilmMatrixRow.reference_strategy_ref` to actual reference entries
11. Generate `ContinuityLedger` from matrix rows + reference index
12. Save continuity ledger as artifact

### Phase 4 — Review packages
13. Build `ReviewPackage` artifact for human review
14. Wire multi-model `ConsensusReport` into review package

### Phase 5 — Cleanup
15. Remove or replace the manual `AssetManifest` with index-aware auto-discovery
16. Remove hardcoded phase dir maps in `store.py` and `paths.py` — consolidate into one
