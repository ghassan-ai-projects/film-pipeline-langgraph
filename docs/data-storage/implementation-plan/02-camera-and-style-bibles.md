# Phase 02 — Camera + Style Bible Writers

> **Status:** 🟢 Ready to start | **Depends on:** —

## Problem

Two visual development artifacts have no writer:

1. **CameraLanguageBible** — schema exists (`camera.py`). Defines lens, framing,
   movement, DOF, composition rules, emotional meaning per camera profile.
   Consumed by the shot bible and generation planning phases for camera prompts.

2. **StyleBible** — no schema exists. Should define color palette, texture, grain,
   visual mood, reference stills. Needed for style boards and composite templates.

## What to Build

### Part A: CameraLanguageBible Writer

- MCP tool: `generate_camera_bible`
- Agent reads `FilmConstitution.camera_philosophy` + `Script` to produce camera profiles
- Storage: `ArtifactStore.save()` → `04-visual-dev/camera_language_bible.v1.json`

### Part B: StyleBible Schema + Writer

- Create `StyleBible` schema in `src/film_pipeline/schemas/style.py` (or add to
  existing visual dev schema file)
- Fields: `project_id`, `color_palette: list[str]`, `texture: str`, `grain: str`,
  `visual_mood: str`, `reference_stills: list[str]`, `must_not_change: list[str]`
- MCP tool: `generate_style_bible`
- Agent reads `FilmConstitution.visual_language` + `EnvironmentBible.color_palette`
  to produce the style bible
- Storage: `ArtifactStore.save()` → `04-visual-dev/style_bible.v1.json`

## Files to Create

- `src/film_pipeline/schemas/style.py` — StyleBible schema
- `src/film_pipeline/agents/impl/camera_bible_agent.py`
- `src/film_pipeline/agents/impl/style_bible_agent.py`
- `tests/unit/agents/test_camera_bible_agent.py`
- `tests/unit/agents/test_style_bible_agent.py`
- `tests/unit/schemas/test_style_bible.py`

## Files to Modify

- `src/film_pipeline/schemas/__init__.py` — Export StyleBible
- `src/film_pipeline/mcp/tools/__init__.py` — Register two new tools
- `src/film_pipeline/mcp/contract.py` — Register in ToolRegistry

## Acceptance Criteria

1. `generate_camera_bible` writes CameraLanguageBible to artifact store
2. `generate_style_bible` writes StyleBible to artifact store
3. StyleBible schema passes mypy strict + round-trip JSON test
4. Camera profiles include at least: lens, framing, movement, DOF, composition
   rules, emotional meaning
5. Style bible includes at least: color palette, texture, grain, visual mood,
   reference stills, immutable rules
6. Unit + integration tests

## Risks

- **StyleBible scope creep**: Visual style is subjective. Keep the schema focused
  on machine-consumable fields (hex colors, texture keywords) not prose essays.
- **Camera profiles are technical**: Agent may hallucinate lens specs. Validate
  against a known vocabulary or constrain via prompt template.
- **Dependency on Phase 01**: StyleBible may reference EnvironmentBible.color_palette.
  Make this optional — fall back to FilmConstitution.visual_language if no
  EnvironmentBible exists yet.
