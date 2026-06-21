# Phase 0 — Organize Output Directories

**Status:** Not started
**Depends on:** Nothing
**Blocks:** Phase 7 (Compositor needs organized frame directories)

---

## Goal

Save generated images into a type+subject hierarchy instead of a flat `sheets/` directory.

## Why

The legacy spec prescribes `references/characters/CHAR_001/`, `references/environments/ENV_001/`, etc. Flat output makes it impossible to find frames later, breaks the reference index, and prevents composite sheet construction (which expects frames organized by type+subject).

## Target Structure

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

## Changes

**File:** `mcp/tools/__init__.py` — `generate_reference_images()`

- Compute output path as `references/{type}s/{subject_id}/master-frames/{reference_id}.png` instead of `references/sheets/{job_id}.png`
- No schema change needed — `asset_path` already stores relative paths

**Naming convention:**
- Use the `reference_id` sanitized (replace `:` with `-`, `/` with `-`) as filename stem
- Append frame role suffix when multiple frames per entry: `{ref_id}-front.png`, `{ref_id}-3-4-left.png`

## Effort

~30 lines. One file.

## Test

| Type | What |
|------|------|
| Unit | `_reference_output_path(entry) -> Path` produces correct directory structure |
