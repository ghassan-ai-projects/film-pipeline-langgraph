# Phase 01 - Model Routing, Prompt Framework, And Secret-Safe Config

Depends on: Phase 00
Blocks: Phases 02-06

---

## Goal

Remove hard-coded model behavior from execution paths and make the prompt framework a real runtime dependency for core agents.

This phase goes first because the product should not build more agent behavior on top of:

- baked-in model strings such as Gemini Flash defaults
- generic prompt rendering
- prompt execution that is optional rather than required

---

## Current Gaps To Close

- `src/film_pipeline/agents/runner.py` still builds generic RCTCO text in the real execution path, not dedicated phase-specific prompt packages
- core agents are registered with `default_model_profile`, but real execution does not yet prove that profile resolution governs calls
- dedicated prompt templates exist, but the runtime path does not yet require or consume them
- several template `agent_id` values do not match the actual registered agent ids
- `film-knowledge-base/promt.md` exists as reference material only and is not wired into runtime prompt execution

---

## Product Result

When this phase is complete:

- no core execution path depends on a hard-coded provider model string
- active profile and model-routing policy determine model choice
- prompt templates are dedicated, versioned, and agent-specific
- the prompt framework is used in real core-agent execution, not just in schemas and tests
- `.env` support works without leaking keys into logs, errors, docs, snapshots, or artifacts

---

## Implementation Work

### 1. Model Policy Refactor

- replace hard-coded model defaults in:
  - `src/film_pipeline/agents/model_adapter.py`
  - `src/film_pipeline/agents/model_routing/__init__.py`
- move model policy into explicit config/profile data
- distinguish:
  - provider model id
  - logical model profile
  - routing fallback chain
  - allowed use by role
- require a resolvable profile for every real agent call
- fail fast with actionable errors when model policy cannot be resolved

### 2. Prompt Framework Refactor

- create dedicated prompt-template definitions for critical agents:
  - constitution creator
  - development/treatment creator
  - screenwriter
  - visual development creator
  - shot bible creator
  - generation planner
  - QC synthesizer
  - post/assembly agent
- make prompt rendering explicit about:
  - role
  - task
  - input artifacts
  - KB packet
  - constraints
  - output schema contract
- align dedicated template ids to the actual runtime agent ids
- prevent generic fallback prompt usage on critical-path execution
- version prompt packages so changes are inspectable and testable
- document whether a KB prompt asset is runtime-governed, manual-reference-only, or obsolete

### 3. Secret Safety

- keep model/provider keys sourced from environment or local `.env`
- ensure redaction in:
  - model adapter failures
  - provider failures
  - audit messages
  - smoke/release checks
- add tests proving keys are not exposed

---

## Files To Create Or Modify

### Production

- `src/film_pipeline/agents/model_adapter.py`
- `src/film_pipeline/agents/model_routing/__init__.py`
- `src/film_pipeline/agents/runner.py`
- `src/film_pipeline/config/`
- `src/film_pipeline/schemas/prompt.py`
- `src/film_pipeline/agents/impl/`
- new prompt-template storage module under `src/film_pipeline/agents/`

### Tests

- `tests/unit/agents/test_model_adapter.py`
- `tests/unit/agents/test_model_routing.py`
- `tests/unit/agents/test_runner.py`
- `tests/unit/config/`
- `tests/integration/agents/test_prompt_framework_execution.py`
- `tests/integration/providers/test_secret_redaction.py`

### Docs

- `docs/product-completion-plan/status-tracker.md`
- any operator docs that mention model setup

---

## Mandatory Behavior Tests

- a core agent call must fail when no model profile resolves
- a core agent call must use profile-driven model selection rather than a hard-coded default
- each critical-path agent must render its own dedicated prompt template
- the prompt template version used for execution must be observable in persisted runtime data
- provider/model errors must redact secrets
- `.env` loading must work without printing raw key values

---

## Acceptance Criteria

- [x] no hard-coded provider model strings remain in core agent execution paths
- [x] critical-path agents resolve models through config and routing policy
- [x] dedicated prompt templates exist for all critical-path agents
- [ ] real critical-path execution must use the dedicated prompt templates instead of generic `build_rctco()` assembly
- [ ] template `agent_id` values must match the actual registered/runtime agent ids
- [ ] generic fallback prompts must be forbidden in real critical-path execution
- [ ] prompt template version and selected model profile must be observable in runtime state, handoff, or audit evidence
- [x] secret-redaction tests prove keys are not leaked
- [ ] unit and integration tests prove the runtime behavior above

---

## Exit Condition

This phase is done when model selection and prompt execution are both governed by runtime policy, not hidden code defaults or generic prompt assembly.

## Implementation Notes

- `ModelAdapter.chat()` and `.chat_json()` no longer have default `model` values — `model` is required
- `ModelRouter.select()` and `.resolve_or_raise()` raise `ModelResolutionError` for unknown profiles (no silent fallback)
- `PromptRunner` now requires `model_router` when `model_adapter` is set; resolves model + params through router
- 8 dedicated prompt templates were created in `agents/prompt_templates/defaults.py` with v1 versioning
- `PromptTemplateRegistry.get_required()` exists, but this is not yet enough because runtime execution still uses `PromptRunner.build_rctco()` directly
- Secret redaction tests added for: HTTP error bodies, OpenRouter key patterns, Google key patterns, .env loading silence
- Model router profiles renamed to qualified OpenRouter ids (e.g. `openrouter/gpt-4o-mini` vs old `gpt-5-mini`)
