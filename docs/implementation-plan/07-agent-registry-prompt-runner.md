# Phase 07 — Agent Registry & Prompt Runner

**Depends on:** Phase 05 (LangGraph Skeleton), Phase 06 (KB Context Builder)
**Blocks:** Phases 08, 09, 10

---

## Goal

Implement the agent registry and the RCTCO prompt runner. The registry makes agents discoverable by capability. The prompt runner executes agent prompts using the RCTCO framework (Role, Core Task, Context, Constraints, Output), injecting KB context packets, collecting structured outputs, and recording handoffs.

This phase implements the **MVP agent set** (19 agents) from `agent-architecture.md`.

---

## Deliverables

### Files to Create

#### Agent Registry (`src/film_pipeline/agents/`)

- [ ] `registry.py` — `AgentRegistry` class: register, lookup by id, lookup by capability, lookup by family
- [ ] `contract.py` — `AgentContract` (from Phase 01 schema): agent_id, family, role, capabilities, input/output artifacts, allowed KB domains, prompt framework, reviewed_by, failure_modes
- [ ] `runner.py` — `PromptRunner` class: build RCTCO prompt, inject KB context, call model, parse output, validate output schema
- [ ] `handoff.py` — `HandoffManager`: create handoff records, track input/output artifacts, validation required
- [ ] `base.py` — `BaseAgent` abstract class: standard agent lifecycle (prepare → execute → validate → return)
- [ ] `__init__.py`

#### MVP Agents (`src/film_pipeline/agents/mvp/`)

- [ ] `orchestrator_agent.py` — owns flow, routing, arbitration
- [ ] `intake_classifier_agent.py` — classifies user input, extracts signals
- [ ] `config_inference_agent.py` — infers missing config values
- [ ] `film_constitution_agent.py` — creates film constitution (theme, tone, visual language)
- [ ] `treatment_agent.py` — creates treatment, act map, scene list
- [ ] `screenwriter_agent.py` — writes script, scene intents
- [ ] `character_dossier_agent.py` — creates character bibles
- [ ] `environment_bible_agent.py` — creates environment bibles
- [ ] `reference_strategy_planner.py` — creates reference strategy
- [ ] `shot_design_agent.py` — creates shot bible, master film matrix
- [ ] `prompt_composition_agent.py` — composes RCTCO prompt packages
- [ ] `continuity_ledger_agent.py` — tracks continuity state
- [ ] `provider_planning_agent.py` — creates provider plan, cost estimate
- [ ] `generation_scheduler_agent.py` — creates generation schedule
- [ ] `clip_validator.py` — validates clip quality, prompt adherence, identity
- [ ] `scene_continuity_validator.py` — validates scene-level continuity
- [ ] `full_movie_flow_validator.py` — validates full-movie coherence
- [ ] `failure_handling_agent.py` — classifies errors, decides recovery action
- [ ] `kb_curator_agent.py` — manages KB ingestion, promotion, conflicts

#### Tests

- [ ] `tests/unit/agents/test_registry.py` — register, lookup by id/capability/family
- [ ] `tests/unit/agents/test_runner.py` — RCTCO prompt construction, output parsing
- [ ] `tests/unit/agents/test_handoff.py` — handoff record creation
- [ ] `tests/unit/agents/test_base_agent.py` — lifecycle (prepare → execute → validate)
- [ ] `tests/integration/agents/test_mvp_agents.py` — each MVP agent produces correct output schema

---

## Task Checklist

- [ ] Implement `AgentRegistry` with register, lookup_by_id, lookup_by_capability, lookup_by_family
- [ ] Implement `AgentContract` schema validation (all required fields from agent-architecture.md)
- [ ] Implement `BaseAgent` abstract class:
  - [ ] `prepare(state, kb_context)` — assemble inputs
  - [ ] `execute(model)` — run RCTCO prompt
  - [ ] `validate(output)` — check output schema
  - [ ] `return_artifact()` — produce typed artifact with metadata
- [ ] Implement `PromptRunner`:
  - [ ] Build RCTCO prompt from agent contract + task + KB context
  - [ ] Call model (abstracted — mock for testing, real model in production)
  - [ ] Parse output as JSON
  - [ ] Validate against expected output schema
  - [ ] Record handoff
- [ ] Implement `HandoffManager`:
  - [ ] Create `AgentHandoff` records (from Phase 01 schema)
  - [ ] Track input_artifact_refs, kb_context_ref, expected_output_schema, validation_required
- [ ] Register all 19 MVP agents with their contracts:
  - [ ] `orchestrator-agent` (role: orchestrator, family: operations)
  - [ ] `intake-classifier-agent` (role: creator, family: producer)
  - [ ] `config-inference-agent` (role: creator, family: producer)
  - [ ] `film-constitution-agent` (role: creator, family: development)
  - [ ] `treatment-agent` (role: creator, family: development)
  - [ ] `screenwriter-agent` (role: creator, family: screenwriting)
  - [ ] `character-dossier-agent` (role: creator, family: visual-dev)
  - [ ] `environment-bible-agent` (role: creator, family: visual-dev)
  - [ ] `reference-strategy-planner` (role: creator, family: reference)
  - [ ] `shot-design-agent` (role: creator, family: directing)
  - [ ] `prompt-composition-agent` (role: creator, family: prompt-planning)
  - [ ] `continuity-ledger-agent` (role: creator, family: directing)
  - [ ] `provider-planning-agent` (role: creator, family: prompt-planning)
  - [ ] `generation-scheduler-agent` (role: creator, family: prompt-planning)
  - [ ] `clip-validator` (role: validator, family: qc)
  - [ ] `scene-continuity-validator` (role: validator, family: qc)
  - [ ] `full-movie-flow-validator` (role: validator, family: qc)
  - [ ] `failure-handling-agent` (role: operator, family: operations)
  - [ ] `kb-curator-agent` (role: curator, family: memory)
- [ ] Implement mock model adapter for testing (returns canned JSON)
- [ ] Write RCTCO prompt templates for each MVP agent
- [ ] Write unit tests for registry, runner, handoff, base agent
- [ ] Write integration tests for each MVP agent (mock model → correct output)
- [ ] Run `make ci-check`

---

## MVP Agent Contract Example

```json
{
  "agent_id": "dialogue-agent",
  "family": "screenwriting",
  "role": "creator",
  "capabilities": ["dialogue", "voice_consistency", "subtext"],
  "input_artifacts": ["scene_intent", "character_bible", "script_draft"],
  "output_artifacts": ["dialogue_pass"],
  "allowed_kb_domains": ["creative-writing", "dialogue", "character"],
  "blocked_kb_domains": ["provider", "cost"],
  "prompt_framework": "RCTCO",
  "default_model_profile": "creative_writer",
  "reviewed_by": ["dialogue-voice-validator"],
  "failure_modes": ["generic_voice", "overwriting_character_truth", "tone_drift"]
}
```

---

## Acceptance Criteria

- [ ] All 19 MVP agents are registered with valid contracts
- [ ] `lookup_by_capability("dialogue")` returns the correct agent
- [ ] `PromptRunner` builds RCTCO prompts with KB context injected
- [ ] `PromptRunner` parses and validates model output against expected schema
- [ ] `HandoffManager` creates handoff records with all required fields
- [ ] Each MVP agent produces correctly-typed artifacts when run with mock model
- [ ] KB context is correctly scoped per agent (no cross-domain leakage)
- [ ] Creator and validator roles are separate (no agent is both for same artifact)
- [ ] All tests pass
- [ ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| Model output doesn't match schema | Strict JSON parsing + retry on parse failure; mock model for tests |
| Agent contracts drift from docs | Generate contracts from agent-architecture.md; validate on registration |
| Too many agents too early | MVP is 19; add specialized agents only after E2E mock passes |
