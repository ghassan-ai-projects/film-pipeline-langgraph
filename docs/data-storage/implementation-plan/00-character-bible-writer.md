# Phase 00 — CharacterBible Writer

> **Status:** 🟢 Ready to start | **Depends on:** —

## Problem

`CharacterBible` schema exists in `src/film_pipeline/schemas/character.py` but no
agent or node produces it. The reference image pipeline (`generate_reference_images`)
needs `CharacterBible.identity_block` for the CHAR_DESC block in structured prompts.
Without it, the 4-level fallback chain bottoms out at the LLM-generated `prompt_text`
on the reference index entry — losing the locked, invariant character description.

## What to Build

### 1. Agent or Node That Produces CharacterBible

Two options:

**Option A: LangGraph node** — wire `visual_dev_node` to call a character-bible
agent before the reference-strategy-planner. The agent reads `Script` +
`FilmConstitution` and produces one `CharacterBible` per character.

**Option B: MCP tool** — `generate_character_bible` MCP tool that OpenClaw calls
before `generate_reference_images`. Stores CharacterBible via `ArtifactStore.save()`.

**Recommendation:** Option B (MCP tool) — matches the existing pattern. The
reference image pipeline already runs through MCP tools. Adding a bible-generation
tool before image generation keeps the flow explicit and gives OpenClaw control.

### 2. Storage

- **Method:** `ArtifactStore.save(character_bible, metadata)` — BaseModel, not dict.
- **Phase:** `visual_dev` (same as reference_index — both are visual development artifacts)
- **Path:** `projects/{slug}/04-visual-dev/character_bible.v{version}.json`
- **State ref:** `character_bible_ref` in LangGraph state

### 3. Wire Into Prompt Builder

Update `_reference_prompt()` in `src/film_pipeline/mcp/tools/__init__.py` to
load the CharacterBible from the artifact store instead of accepting `None`.
This removes the fallback chain for the CHAR_DESC block — the locked bible
becomes the authoritative source.

## Files to Create

- `src/film_pipeline/agents/impl/character_bible_agent.py` — Agent that produces CharacterBible from Script + FilmConstitution
- `tests/unit/agents/test_character_bible_agent.py`

## Files to Modify

- `src/film_pipeline/mcp/tools/__init__.py` — Add `generate_character_bible` MCP tool
- `src/film_pipeline/mcp/contract.py` — Register the new tool in ToolRegistry
- `src/film_pipeline/graph/nodes.py` — Optionally wire into visual_dev_node
- `src/film_pipeline/mcp/tools/__init__.py:_reference_prompt()` — Load CharacterBible from store

## Acceptance Criteria

1. `generate_character_bible` MCP tool exists and returns `ok: true` with `character_bible_ref`
2. `ArtifactStore` contains `character_bible.v1.json` under `04-visual-dev/`
3. `_reference_prompt()` loads CharacterBible from store; CHAR_DESC block uses `identity_block`
4. Unit test: agent produces valid CharacterBible from mock Script + FilmConstitution input
5. MCP integration test: tool writes to artifact store, prompt builder reads it back
6. `make ci-check` passes

## Risks

- **Agent quality**: The character bible agent needs to extract durable character
  descriptions from the script. Bad output → bad prompts → bad images.
  Mitigation: require human approval gate after bible generation.
- **Schema round-trip**: CharacterBible uses nested Pydantic models
  (CharacterIdentity, CharacterVoice, Wardrobe, EmotionalArc, Relationship).
  Agent output must parse correctly through all nested models.
