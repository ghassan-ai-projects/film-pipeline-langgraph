# Phase 01 — EnvironmentBible Writer

> **Status:** 🟢 Ready to start | **Depends on:** —

## Problem

`EnvironmentBible` schema exists in `src/film_pipeline/schemas/environment.py` but
no agent or node produces it. The reference image pipeline needs it for:

- **Prompt ENV_BASE block**: `locked_prompt_block` + `fingerprint.text` provide the
  authoritative environment description
- **Compositor color palette**: `color_palette: list[str]` is already consumed by
  `_render_color_palette()` in `src/film_pipeline/generation/compositor.py`

Without it, the 4-level fallback chain bottoms out at LLM `prompt_text` and the
color palette renders as a placeholder.

## What to Build

### 1. MCP Tool: `generate_environment_bible`

Same pattern as Phase 00. The agent reads `Script` + `FilmConstitution` and produces
one `EnvironmentBible` per distinct environment.

### 2. Storage

- **Method:** `ArtifactStore.save(environment_bible, metadata)`
- **Phase:** `visual_dev`
- **Path:** `projects/{slug}/04-visual-dev/environment_bible.v{version}.json`
- **State ref:** `environment_bible_ref`

### 3. Wire Into Pipeline

Update `_build_composites()` to load EnvironmentBible from artifact store (already
partially done — current code tries `artifact_store.load()` with error swallowing).
Make the load path robust and surface errors instead of silently falling back.

Update `_reference_prompt()` to load EnvironmentBible for the ENV_BASE block.

## Files to Create

- `src/film_pipeline/agents/impl/environment_bible_agent.py`
- `tests/unit/agents/test_environment_bible_agent.py`

## Files to Modify

- `src/film_pipeline/mcp/tools/__init__.py` — Add `generate_environment_bible` tool; make `_build_composites()` palette loading robust
- `src/film_pipeline/mcp/contract.py` — Register tool

## Acceptance Criteria

1. `generate_environment_bible` MCP tool produces valid EnvironmentBible
2. `color_palette` renders correctly in environment board when bible exists
3. `_reference_prompt()` uses `locked_prompt_block` for ENV_BASE
4. No silent fallback — missing bible is a surfaced error, not a degraded prompt
5. Unit + integration tests

## Risks

- **Multiple environments per film**: The agent must produce one EnvironmentBible
  per distinct environment (e.g., "studio", "rooftop", "alley"). The tool needs to
  accept an environment_id parameter or produce all at once. Recommend: produce
  all at once, keyed by environment_id.
- **Color palette format**: `color_palette: list[str]` expects hex colors. Agent
  may produce color names ("navy blue"). The compositor already handles invalid
  hex gracefully (falls back to placeholder), but we should validate early.
