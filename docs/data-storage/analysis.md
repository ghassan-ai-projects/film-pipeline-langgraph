# Data Storage Document — Review & Analysis

> Review of `docs/film-data-storage-complete.md` against the actual codebase
> as of 2026-06-21 (commits through `be7d75a`).

---

## What's Right

The document correctly captures:

- **Schema inventory** — Every Pydantic schema is correctly listed per phase.
- **Phase structure** — Intake → Constitution → Development → Script → Visual Dev →
  Shot Bible → Gen Planning → Generation → QC → Post → Delivery. This matches
  `src/film_pipeline/schemas/_base.py:FilmPhase`.
- **Storage rules** — ArtifactStore.save() for JSON, raw file writes for binaries.
- **State refs** — `constitution_ref`, `treatment_ref`, `script_ref`, etc. all
  match the actual LangGraph state keys.
- **Node maturity assessment** — Most nodes from `shot_bible_node` onward are
  flag-only skeletons. This is accurate. `visual_dev_node` is correctly
  identified as partial (only saves `reference_index`).

## What's Wrong or Outdated

### 1. Reference Image Output Structure (Critical)

The document describes the output as:

```
references/characters/CHAR_001/
├── identity-sheet.png
├── identity-sheet.png.meta.json
├── identity-sheet.sheet.json
├── costume-sheet.png
├── expression-sheet.png
└── master-frames/
    ├── leo-front.png
    ├── leo-front.png.meta.json
    └── ...
```

What the actual code produces (`generate_reference_images` MCP tool):

```
references/
├── index/
│   ├── reference-index.json
│   └── reference-validation-summary.json
├── characters/
│   └── {id}/                           # uses subject_id, not CHAR_001
│       ├── master-frames/
│       │   ├── char-{id}-front-face.png  # reference_id, not generic name
│       │   └── ...
│       └── identity-sheet.png
└── environments/
    └── {id}/
        ├── master-frames/
        └── environment-board.png
```

Differences:
- **Plural directory names**: `characters/` not `characters/CHAR_001/`
- **No CHAR_001/ENV_001 abstraction**: Uses actual subject_id values
- **No `.meta.json` sidecars**: Individual frames have no metadata sidecar
- **No `.sheet.json` manifests**: Composite layout not persisted as JSON
- **No `costume-sheet.png` or `expression-sheet.png`**: Only character identity
  sheet and environment board are implemented
- **No `index.json` at root**: Instead `references/index/reference-index.json`
- **No `props/`, `style/`, `scale/` directories**: Not yet implemented
- **Frame names derive from `reference_id`**: Not short names like `leo-front.png`

### 2. "Current Status" Markers Are Stale

Several artifacts marked "Schema exists, no agent writes it yet" are now
partially operational:

| Artifact | Document says | Reality |
|----------|--------------|---------|
| Reference index | "Schema exists, no agent writes" | `visual_dev_node` saves it. `generate_reference_images` MCP tool enriches it with asset_path, validation, provider. |
| Reference images (binary) | "No binary save/load functions" | `generate_reference_images` writes PNGs via provider adapter + compositor |
| Composite sheets | "Missing" | `build_character_identity_sheet()` and `build_environment_board()` produce them |
| Validation report | ""Schema exists, no writer" | Gemini per-frame review writes scores to entry dicts; composite validation runs during generation |
| Color palette | "Missing" | `_render_color_palette()` renders swatches from `EnvironmentBible.color_palette` |

### 3. Missing `CharacterBible` / `EnvironmentBible` Production

The document correctly notes that `visual_dev_node` doesn't save these bibles.
This is still true — the schemas exist but no agent produces them. The
reference image pipeline relies on them as *input* (for prompt construction)
but they must exist before `generate_reference_images` is called.

### 4. Storage Method Confusion

The document says "JSON artifacts go through `ArtifactStore.save()`" but the
reference index is saved via `store.save_dict()` (not `store.save()`). The
distinction matters: `save()` expects a Pydantic BaseModel and calls
`.model_dump_json()`, while `save_dict()` accepts plain dicts. The reference
image pipeline uses `save_dict()` because entries are mutated dicts, not
strict Pydantic models at save time.

### 5. File Tree Has Aspirational Items Mixed With Real Ones

The "Complete File Tree" section mixes implemented and aspirational paths
without clear markers. For example:
- `costume-sheet.png`, `expression-sheet.png`, `camera-style-board.png` don't exist
- `style_bible.v1.json`, `generation_plan.v1.json` have no schemas yet
- `.meta.json` and `.sheet.json` sidecars are aspirational

### 6. No Mention of the MCP Tool-Generated Assets

The document focuses on the LangGraph node → artifact store path, but the
reference image pipeline runs entirely through the `generate_reference_images`
MCP tool, bypassing the graph nodes. This is a significant architectural
detail that should be documented.

## Recommendations

### High Priority
1. **Fix the reference image output structure** — Update paths, add plural
   directory names, remove non-existent files
2. **Add MCP tool path** — Document `generate_reference_images` as the
   alternative artifact production path for visual development
3. **Mark aspirational items** — Use `(planned)` or `(TODO)` tags for
   items that don't exist yet

### Medium Priority
4. **Distinguish storage methods** — `save()` vs `save_dict()` for JSON
   artifacts
5. **Update current status markers** — Reflect what's actually produced
6. **Add completeness tiers** — "Implemented", "Schema-only", "Planned"

### Low Priority
7. **Remove or isolate aspirational file tree** — Keep the aspirational
   tree as a separate section clearly marked as "Target State"
8. **Add Known Gaps section** — Explicitly list what schemas exist but
   have no writer

---

## Summary

The document is structurally sound and 70% accurate. The primary issue is
that the reference image output structure is completely wrong (documented an
aspirational layout instead of what the code actually produces). Secondary
issues are stale status markers and mixed aspirational/real content without
clear labeling.

The fix is to produce a corrected version that:
- Uses actual output paths verified against the code
- Marks aspirational items clearly
- Documents the MCP tool path alongside the graph node path
- Distinguishes between `save()` and `save_dict()` storage methods
