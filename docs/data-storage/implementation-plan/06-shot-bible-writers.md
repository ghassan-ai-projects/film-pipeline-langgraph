# Phase 06 — Shot Bible Writers

> **Status:** 🟢 Ready to start | **Depends on:** —

## Problem

Three schemas exist with no writer:
- `MasterFilmMatrix` — every shot as a row with scene, characters, env, camera, refs
- `ContinuityLedger` — per-shot state_in/state_out for characters, props, wardrobe, env, lighting
- `PromptRegistry` — all RCTCO prompt packages indexed by shot_id

The `shot_bible_node` is flag-only. Without these artifacts, generation planning
(Phase 07) has nothing to plan from.

## What to Build

### 1. MasterFilmMatrix Writer

**Agent:** `shot-design-agent` already registered but produces no output.
Wire it to produce `MasterFilmMatrix` from `Script` + `ReferenceIndex` +
`CharacterBible` + `EnvironmentBible` + `CameraLanguageBible`.

**Storage:** `ArtifactStore.save()` → `05-shot-bible/master_film_matrix.v1.json`

**State ref:** `shot_matrix_ref`

### 2. ContinuityLedger Writer

**Agent:** Reuse `shot-design-agent` or add a dedicated continuity agent.
For each shot in the matrix, compute state_in/state_out transitions.

**Storage:** `ArtifactStore.save()` → `05-shot-bible/continuity_ledger.v1.json`

### 3. PromptRegistry Writer

**Agent:** Reuse `shot-design-agent` or add a dedicated prompt agent.
For each shot, assemble an RCTCO prompt package from the script context,
character/environment bibles, and camera profile.

**Storage:** `ArtifactStore.save()` → `05-shot-bible/prompt_registry.v1.json`

### Implementation Strategy

The `shot-design-agent` should produce all three artifacts in one pass
since they share context (Script + bibles). The agent output can be a
single JSON blob with `shot_matrix`, `continuity_ledger`, and `prompt_registry`.

Alternatively, split into three tools for Granularity:
- `generate_shot_matrix`
- `generate_continuity_ledger` (depends on shot matrix)
- `generate_prompt_registry` (depends on shot matrix)

**Recommendation:** Single `generate_shot_bible` MCP tool that produces all three.

## Files to Create

- `src/film_pipeline/agents/impl/shot_design_agent.py` — Implement existing stub
- `tests/unit/agents/test_shot_design_agent.py`

## Files to Modify

- `src/film_pipeline/mcp/tools/__init__.py` — Add `generate_shot_bible` tool; wire `shot_bible_node`
- `src/film_pipeline/graph/nodes.py` — Wire `shot_bible_node` to call the agent
- `src/film_pipeline/mcp/contract.py` — Register tool

## Acceptance Criteria

1. `generate_shot_bible` produces all three artifacts
2. MasterFilmMatrix has one row per shot with all required fields
3. ContinuityLedger correctly chains state_in/state_out across consecutive shots
4. PromptRegistry has a prompt package for every shot
5. `shot_bible_node` advances state with `shot_matrix_ref`
6. Unit + integration tests

## Risks

- **Agent context size**: A full script with bibles may exceed the LLM context
  window. Mitigation: process one scene at a time, then aggregate.
- **Continuity correctness**: The continuity ledger is a chain — one error
  propagates. Mitigation: validate with Gemini after generation.
- **Prompt quality**: RCTCO prompts drive generation quality. Budget for
  human review of the prompt registry before advancing to generation planning.
