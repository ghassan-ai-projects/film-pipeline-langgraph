# Phase 7 — Character Identity Sheet Compositor

**Status:** Not started
**Depends on:** Phase 0 (organized directories) + Phase 4 (identity-consistent frames) + Phase 2 (structured prompts)
**Blocks:** Phase 8 (composite validation needs a sheet to review)

---

## Goal

Build Character Identity Sheet composite from generated master frames using Pillow.

## Why

Individual images are raw provider outputs. Composite sheets are what downstream video models actually consume as reference anchors. A Character Identity Sheet with front face (2×), 3/4 angles, profile, full body, expressions, and detail insets is the minimum viable reference product.

## Template

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

## Build Rules

- Canvas: 2048×2048, white or neutral background
- Grid borders: 1px, #333
- Spacing: 8px between tiles
- Labels: rendered in margin areas only — 12px font, below or beside tiles
- Visual hierarchy: face 2× scale (640×640) > body 1× (720×400) > expressions 0.5× (320×320)
- Tiles are cropped/resized from master frames to fit their grid cells
- Output: `references/characters/<subject_id>/identity-sheet.png`

## Input

List of master frames with roles:

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

## Graceful Degradation

- If a role is missing, render placeholder (gray with label) — partial sheets are better than nothing
- Missing anchor (front-face) → warn but still build with available frames
- All frames missing → skip this subject, log warning

## Implementation

- Pure Pillow — `Image.paste()`, `Image.resize()`, `ImageDraw` for borders and labels
- Template function: `build_character_identity_sheet(subject_id, character_name, frames) -> Path`
- `replace_tile(sheet_path, tile_name, new_frame_path) -> Path` for partial rebuild (Phase 9)

## Files

| File | Action |
|------|--------|
| **NEW** `generation/compositor.py` | `build_character_identity_sheet()` + `replace_tile()` |
| `schemas/reference.py` | Add `frame_role: str` field |
| `agents/prompt_templates/defaults.py` | Update visual-dev template to include `frame_role` |
| `agents/impl/visual_dev_agent.py` | Parse `frame_role` from model output |
| `mcp/tools/__init__.py` | After generating all frames for a character, call compositor |

## Effort

~200 lines. One new file + ~30 lines across 4 files.

## Tests

| Type | What |
|------|------|
| Unit | `build_character_identity_sheet()` produces valid PNG of correct dimensions (2048×2048) |
| Unit | Missing frame → placeholder rendered, no crash |
| Unit | `replace_tile()` swaps a single tile without rebuilding all tiles |
