# Phase 05 — Additional Composite Templates

> **Status:** 🟡 Blocked by 00, 01, 02 | **Depends on:** CharacterBible (00), EnvironmentBible (01), Camera/Style Bibles (02)

## Problem

Only two composite templates exist:
- `character_identity_sheet.png` — 20 tiles, 2048×2048
- `environment_board.png` — 8 tiles, 3840×2160

Missing templates needed for a complete visual development package:
- Costume sheet (wardrobe variants per character)
- Expression sheet (emotional range per character)
- Prop board (key props)
- Style board (visual style reference)
- Camera board (camera language reference)
- Scale sheet (character scale comparison)

## What to Build

### Template 1: Costume Sheet (`costume-sheet.png`)

- **Input:** `CharacterBible.wardrobe` entries
- **Layout:** 2-4 costume variants, full-body renders
- **Dimensions:** 2048×2048 or 2560×1440
- **Generator:** `build_costume_sheet()` in compositor

### Template 2: Expression Sheet (`expression-sheet.png`)

- **Input:** Expression frames from master-frames/
- **Layout:** Grid of expression close-ups (neutral, frustrated, tired, peaceful, angry, surprised)
- **Dimensions:** 2048×2048
- **Generator:** `build_expression_sheet()` in compositor
- **Note:** May be folded into the existing Character Identity Sheet or kept separate

### Template 3: Prop Board (`prop-board.png`)

- **Input:** Prop reference frames
- **Layout:** Grid with scale reference
- **Dimensions:** 2560×1440
- **Generator:** `build_prop_board()` in compositor

### Template 4: Style Board (`style-board.png`)

- **Input:** StyleBible data (color palette, texture references, mood images)
- **Layout:** Color swatches + texture samples + mood reference
- **Dimensions:** 3840×2160
- **Generator:** `build_style_board()` in compositor

### Template 5: Camera Board (`camera-board.png`)

- **Input:** CameraLanguageBible profiles
- **Layout:** Per-profile: lens diagram, framing example, DOF illustration
- **Dimensions:** 3840×2160
- **Generator:** `build_camera_board()` in compositor

### Template 6: Scale Sheet (`scale-sheet.png`)

- **Input:** Full-body frames from all characters
- **Layout:** Side-by-side comparison at consistent scale
- **Dimensions:** 3840×2160
- **Generator:** `build_scale_sheet()` in compositor

### Implementation Strategy

Not all templates need frame generation. Some are pure composite assembly from
existing frames or data:

| Template | Needs generation? | Pure compositor? |
|----------|-------------------|------------------|
| Costume sheet | ✅ Needs costume frames | ✅ Compositor |
| Expression sheet | Already have expression frames | ✅ Compositor |
| Prop board | ✅ Needs prop frames | ✅ Compositor |
| Style board | ❌ Pure data + swatches | ✅ Compositor |
| Camera board | ❌ Pure data + diagrams | ✅ Compositor |
| Scale sheet | Already have full-body frames | ✅ Compositor |

Implement the pure-data templates first (style, camera, scale) since they
don't need additional frame generation.

## Files to Create

- `tests/unit/generation/test_compositor_templates.py` — One test class per template

## Files to Modify

- `src/film_pipeline/generation/compositor.py` — Add 6 new builder functions
- `src/film_pipeline/mcp/tools/__init__.py:_build_composites()` — Call new builders
- `src/film_pipeline/schemas/reference.py` — Add reference types for new templates

## Acceptance Criteria

1. All 6 templates produce valid PNGs at correct dimensions
2. Data-only templates (style, camera, scale) render without frame generation
3. Costume and prop templates have placeholder support for missing frames
4. Each template has a corresponding validation rubric in `sheet_reviewer.py`
5. Unit tests: one per template, verifying dimensions and content
6. `make ci-check` passes

## Risks

- **Template proliferation**: 6 more compositor functions = 6 more test files.
  Keep each template function focused (layout + paste + label) using shared
  helpers.
- **Frame generation dependency**: Costume and prop boards need new frame roles
  added to the VisualDevAgent output. This may require template updates.
- **Validation rubric complexity**: Each template type needs its own rubric in
  `sheet_reviewer.py`. Start with simplified rubrics (30pt) for non-identity sheets.
