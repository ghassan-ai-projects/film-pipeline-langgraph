# OpenClaw MCP Operator Guide

This guide covers the aligned MCP behavior for OpenClaw.

The key rule is now:

- server mode is the source of truth
- project mode must match server mode

## Modes

Use one of these startup commands:

```bash
make run-mcp-mock
make run-mcp-real
```

Notes:

- `make run-mcp` still exists as a legacy mock alias
- `FILM_PIPELINE_MCP_MODE=real` now drives the runtime construction
- real mode uses the real prompt-runner path, not canned mock responses
- the server now speaks stdio MCP directly for `initialize`, `tools/list`, and `tools/call`

## Before Starting Real Mode

Set:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
export GOOGLE_API_KEY="AIza..."
```

Real-mode bootstrap expects `OPENROUTER_API_KEY`.
Real-mode project creation with the real provider stack also expects `GOOGLE_API_KEY`
because the image lane now uses Gemini Imagen 4 instead of `mock-image-provider`.

## What MCP Supports Now

OpenClaw can now:

- discover profiles with `list_profiles`
- inspect profiles with `inspect_profile`
- create a project with explicit `runtime_mode`
- verify mode alignment with `get_runtime_mode`
- inspect registered providers after project creation with `list_providers`
- generate persisted reference images with `generate_reference_images` — a full 12-phase pipeline:
  - structured prompts from CharacterBible + FilmConstitution
  - per-frame heuristic checks (5 Pillow checks, $0)
  - per-frame Gemini review (40-pt rubric, selective to control cost)
  - identity consistency via seed locking + I2I drift detection
  - retry loop (3 attempts with feedback injection)
  - provider tier routing (fast / standard / ultra)
  - Pillow-based composite sheets (Character Identity 2048×2048, Environment Board 3840×2160)
  - Gemini composite validation (50pt character, 50pt environment)
  - delta regeneration for failing composite tiles
  - index persistence (`references/index/reference-index.json`)

Real-mode project creation now aligns with the actual server mode:

- real server mode + real project mode: allowed
- mock server mode + mock project mode: allowed
- any mismatch: rejected

## Profile Naming

Use actual file stems:

- `provider.seedance_primary`
- `provider.free_or_low_cost`
- `quality.studio`
- `quality.draft`
- `quality.festival`
- `film-type.narrative`
- `film-type.visual_poetry`
- `film-type.experimental`
- `review.strict_continuity`
- `mock-demo`
- `local-real-provider`

## Step 1. Start The Correct Server Mode

For OpenClaw production use:

```bash
make run-mcp-real
```

Do not use `make run-mcp-mock` for real operator work.

## Step 2. Discover And Inspect Profiles

Call:

```text
list_profiles
inspect_profile
```

For real mode, inspect the profiles you plan to use and confirm they do not reference:

- `mock-*` providers
- `mock-*` models

Current real image lane:

- `provider.seedance_primary` registers `gemini-imagen-4` for image generation
- `local-real-provider` also uses `gemini-imagen-4`

Example profile ids:

```json
{ "profile_id": "provider.seedance_primary" }
```

```json
{ "profile_id": "quality.studio" }
```

## Step 3. Create The Project In The Same Mode As The Server

Example:

```json
{
  "project_id": "after-the-fall-001",
  "title": "After the Fall",
  "slug": "after-the-fall",
  "runtime_mode": "real",
  "provider_profile": "provider.seedance_primary",
  "quality_profile": "quality.studio",
  "film_type_profile": "film-type.narrative",
  "review_profile": "review.strict_continuity"
}
```

Behavior:

- if the server is running in `real`, the project must be `real`
- if the server is running in `mock`, the project must be `mock`
- if `runtime_mode` is omitted, it defaults to the server mode
- in real mode, mock provider/model profiles are rejected
- the selected profile stack is resolved and stored with the project
- providers are registered from the selected profile stack during project creation

## Step 4. Verify Alignment

Call:

```text
get_runtime_mode
```

Expected real-mode shape:

```json
{
  "ok": true,
  "server_mode": "real",
  "runtime_mode": "real",
  "project_runtime_mode": "real",
  "aligned": true,
  "profile_stack": {
    "film_type_profile": "film-type.narrative",
    "quality_profile": "quality.studio",
    "provider_profile": "provider.seedance_primary",
    "review_profile": "review.strict_continuity"
  }
}
```

If project mode and server mode differ, the tool returns an error.

## Step 5. Generate Reference Images In Visual Dev

After the script phase reaches `visual_dev`, the `generate_reference_images`
MCP tool executes a full 12-phase pipeline that turns the planned
`reference_index` entries into validated image assets.

### 5a. Invoke Generation

```json
{
  "reference_ids": ["char-leo-front-face", "env-studio-wide"],
  "force": false
}
```

Both `reference_ids` and `force` are optional:
- `reference_ids` — filter to specific entries; omit to generate all.
- `force` — regenerate even if an `asset_path` already exists.

### 5b. Pipeline (what happens inside)

The single MCP call runs sequentially:

| Phase | What happens | Key detail |
|-------|-------------|------------|
| Prompt build | Structured prompt from CharacterBible / FilmConstitution | 7-block character prompt, 7-block environment prompt |
| Provider routing | tier field → fast ($0.02) / standard ($0.05) / ultra ($0.10) | seed propagated across same-subject frames for identity consistency |
| Identity consistency | Anchor frame first (front-face for chars, wide-establishing for envs) | seed locked; I2I fallback when Gemini detects subject drift `< 7` |
| Heuristic checks | 5 free Pillow checks per frame | file_exists, not_corrupt, min_resolution ≥ 512, has_content (color variance), face_present (character-only) |
| Gemini per-frame review | 40-pt rubric: Subject (10) + Prompt Match (10) + Artifacts (10) + Technical (10) | threshold ≥ 28 (70%); selective — skips env lighting variants, spot-checks alt angles |
| Retry loop | Max 3 attempts per frame | actionable_feedback injected into retry prompt; best_score tracked |
| Composite sheets | Pillow builds Character Identity Sheets (2048×2048, 20 tiles) and Environment Boards (3840×2160, 8 tiles) | center-crop + resize, labels in margins, gray placeholders for missing frames |
| Composite validation | Gemini reviews complete sheets — character 50pt, environment 50pt rubric | ≥ 80% threshold; generates failing_tiles and bad_reference_tags |
| Delta regeneration | Tile-level retry for failing tiles only | max 3 iterations, best composite score retained |
| Index persistence | `references/index/reference-index.json` + `reference-validation-summary.json` | human-readable |

### 5c. Response Shape

```json
{
  "ok": true,
  "generated": 14,
  "skipped": 0,
  "failed": 0,
  "results": [
    {
      "reference_id": "char-leo-front-face",
      "status": "validated",
      "asset_path": "references/characters/leo/master-frames/char-leo-front-face.png",
      "quality_score": 85.0
    },
    {
      "reference_id": "env-studio-lighting-ambient",
      "status": "generated",
      "asset_path": "references/environments/studio/master-frames/env-studio-lighting-ambient.png"
    }
  ],
  "reference_index_ref": "artifact:reference_index:v1"
}
```

Status values:
- `validated` — Gemini review passed (≥28/40).
- `generated` — review skipped (acceptable per selective validation rules).
- `failed` — heuristic checks failed on final retry.
- `needs_regeneration` — Gemini review failed on final retry.
- `skipped` — asset already existed and `force` was false.

### 5d. Output Directory Structure

```
references/
├── index/
│   ├── reference-index.json          # All entries with asset_path, validation, locked
│   └── reference-validation-summary.json  # Counts and average scores
├── characters/
│   └── {id}/
│       ├── master-frames/            # Individual frame PNGs
│       │   ├── char-{id}-front-face.png
│       │   ├── char-{id}-profile-right.png
│       │   └── ...
│       └── identity-sheet.png        # Composite Character Identity Sheet
└── environments/
    └── {id}/
        ├── master-frames/            # Individual frame PNGs
        │   ├── env-{id}-wide.png
        │   ├── env-{id}-alt-angle-01.png
        │   └── ...
        └── environment-board.png     # Composite Environment Board
```

### 5e. Inspect Individual Results

Use `inspect_reference` to read a single entry from the updated index:

```json
{ "reference_id": "char-leo-front-face" }
```

Response includes all rich metadata now:

```json
{
  "ok": true,
  "reference": {
    "reference_id": "char-leo-front-face",
    "subject_type": "character",
    "subject_id": "leo",
    "frame_role": "front-face",
    "expression": "neutral",
    "lighting": "key-light",
    "tier": "standard",
    "asset_path": "references/characters/leo/master-frames/char-leo-front-face.png",
    "provider": "gemini-imagen-4",
    "generation_status": "validated",
    "quality_score": 85.0,
    "retry_count": 0,
    "best_score": 34.0,
    "validation": {
      "score": 34.0,
      "reports": ["{\"subject\": {\"score\": 9}, ...}"],
      "status": "passed"
    },
    "ai_usability": {
      "score": 85.0,
      "notes": "Good facial detail, matches prompt well."
    },
    "locked": false
  }
}
```

### 5f. Get Validation Summary

`get_validation_report` for `visual_dev` runs the ReferenceUsabilityValidator
against the updated artifact store. It provides aggregate validation counts
and blocking issues.

The per-frame Gemini scores and composite validation results are available
through:
- `inspect_reference` — per-entry `validation` and `ai_usability` fields.
- `references/index/reference-index.json` — complete index on disk.
- `references/index/reference-validation-summary.json` — aggregate counts.

## Step 6. Continue With The Film Workflow

After project creation, the normal MCP flow is unchanged:

1. `set_active_project`
2. `submit_idea`
3. `approve_intake`
4. `approve_phase`
5. `generate_reference_images` once `visual_dev` is reached
6. inspect artifacts and validation as needed

Useful follow-up tools:

- `review_phase_artifacts`
- `inspect_artifact`
- `inspect_reference` — per-entry metadata including `validation`, `ai_usability`, `quality_score`
- `get_validation_report` — phase-level aggregate validation
- `list_validation_issues`
- `request_revision`
- `list_providers`
- `check_provider_health`

Key files on disk after reference generation (for direct inspection):

- `references/index/reference-index.json` — all entries with paths, scores, lock status
- `references/index/reference-validation-summary.json` — counts and averages
- `references/characters/{id}/identity-sheet.png` — composite Character Identity Sheet
- `references/environments/{id}/environment-board.png` — composite Environment Board

## What Is Aligned Now

These behaviors are aligned:

- runtime mode is chosen at server startup
- the global runtime is rebuilt from that mode
- real mode uses the real model adapter path
- project creation cannot contradict server mode
- `get_runtime_mode` exposes both server and project mode
- provider registration is derived from the selected project profile stack
- real-mode provider stacks reject missing credentials before the project is created
- the real profile image lane uses `gemini-imagen-4`, not `mock-image-provider`
- visual-dev references can now be generated and persisted through MCP

## What Is Still Missing

- resolved config is stored in project state, but not yet exposed as a dedicated first-class MCP artifact
- live-provider readiness and provider health are still lighter than the full target plan
- audit proof for live model/provider execution is still limited
- delta regeneration has no dedicated MCP tool — it runs internally during `generate_reference_images` but OpenClaw cannot request targeted tile-level retries independently
- composite validation results (failing tiles, bad reference tags) are computed during generation but not surfaced as a callable MCP artifact — they only appear in the Gemini response logged to the console
- `get_validation_report` for `visual_dev` uses the pre-existing ReferenceUsabilityValidator (macro-level checks) rather than the Gemini per-frame and composite review scores; individual frame scores are accessible via `inspect_reference` per-entry

## Decision Rule

Use this rule:

- if `make run-mcp-real` started the server and `get_runtime_mode` reports `aligned: true` with `server_mode=real`, OpenClaw is on the correct real-mode contract
- if either the startup mode or `get_runtime_mode` says `mock`, treat it as non-production

## Related Doc

Remaining productization work is tracked here:

- [real-model-only-mcp-plan.md](./mcp-openclaw/real-model-only-mcp-plan.md)
