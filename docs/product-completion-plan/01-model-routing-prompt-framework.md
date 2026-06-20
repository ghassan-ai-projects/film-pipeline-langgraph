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

- `src/film_pipeline/agents/model_adapter.py` contains hard-coded OpenRouter model defaults
- `src/film_pipeline/agents/model_routing/__init__.py` contains baked model names and fallback values
- `src/film_pipeline/agents/runner.py` builds generic RCTCO text, not phase-specific prompt packages
- core agents are registered with `default_model_profile`, but real execution does not yet prove that profile resolution governs calls
- prompt templates are not yet versioned and enforced per critical-path agent

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
- prevent generic fallback prompt usage on critical-path execution
- version prompt packages so changes are inspectable and testable

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

- [ ] no hard-coded provider model strings remain in core agent execution paths
- [ ] critical-path agents resolve models through config and routing policy
- [ ] dedicated prompt templates exist for all critical-path agents
- [ ] generic fallback prompts are forbidden for critical-path execution
- [ ] prompt template version and selected model profile are observable in runtime state, handoff, or audit evidence
- [ ] secret-redaction tests prove keys are not leaked
- [ ] unit and integration tests prove the new behavior

---

## Exit Condition

This phase is done when the repo can honestly say model selection and prompt execution are governed by runtime policy rather than hidden code defaults.
