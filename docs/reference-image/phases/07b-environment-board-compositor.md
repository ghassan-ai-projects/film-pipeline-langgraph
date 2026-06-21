# Phase 7b — Environment Board Compositor

**Status:** Not started  
**Depends on:** Phase 7 (same compositor architecture), Phase 4 (geometry-consistent environment frames)  
**Blocks:** Phase 8 (composite validation covers environment rubric)  

---

## Goal

Build Environment Board composites from generated master frames.

## Why

Environment Board is the second most important reference type. Without it, there's no spatial anchor for environment consistency across shots. The architecture is the same as Character Identity Sheet (Phase 7) — different template, same engine.

## Template

```
┌──────────────────────────────────────────────────────────────┐
│                  ENVIRONMENT BOARD                            │
│                <subject_id> — <environment_name>              │
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

## Build Rules

- Canvas: 3840×2160 (16:9 — wider than character sheet for spatial content)
- Grid borders: 1px, #333
- Spacing: 8px between tiles
- Labels in margins only
- Wide establishing is the canonical anchor (largest tile)
- Lighting variants share the same wide composition
- Color palette strip: rendered as colored rectangles with hex labels below
- Output: `references/environments/<subject_id>/environment-board.png`

## Input

```python
frames = [
    {"role": "wide-establishing", "path": "master-frames/ref-010-wide.png"},
    {"role": "alt-angle-desk", "path": "master-frames/ref-010-desk.png"},
    {"role": "alt-angle-corner", "path": "master-frames/ref-010-corner.png"},
    {"role": "lighting-cool-night", "path": "master-frames/ref-010-night.png"},
    {"role": "lighting-golden-afternoon", "path": "master-frames/ref-010-afternoon.png"},
    {"role": "detail-texture", "path": "master-frames/ref-010-texture.png"},
    {"role": "color-palette", "path": None},  # generated from FilmConstitution colors, not a frame
]
```

## Color Palette Generation

If no `color-palette` frame exists, extract palette from `FilmConstitution.visual_language` or generate a default from the environment description. Rendered as a horizontal strip of colored rectangles with hex codes below.

## Files

| File | Action |
|------|--------|
| `generation/compositor.py` | Add `build_environment_board(subject_id, env_name, frames) -> Path` |
| `mcp/tools/__init__.py` | After generating all frames for an environment, call compositor |

## Effort

~120 lines. Reuses Phase 7 infrastructure.

## Tests

| Type | What |
|------|------|
| Unit | `build_environment_board()` produces valid PNG of correct dimensions (3840×2160) |
| Unit | Color palette rendered correctly from FilmConstitution data |
| Unit | Missing frame → placeholder rendered, no crash |
