# Validator LLM Integration — Architecture

## Status

7 validators, all stubs. Registry hardcodes model IDs. Zero LLM calls.

## Target

Validators use the same infrastructure as agents: ModelRouter profiles, prompt templates, ModelAdapter for LLM calls, typed response parsing with **actionable suggestions** that flow into repair feedback.

```
ValidatorRegistryEntry.model_profile = "multimodal_reviewer"
ModelRouter.resolve("multimodal_reviewer") → "google/gemini-3-flash-preview"
Validator.validate(artifact) → builds prompt → calls LLM → parses JSON → score + issues with suggestions
```

## Scalars & Principle

- **30 hardcoded model strings** across 12 files → eliminated
- **No code path shall contain a literal model ID string** — all resolution through `ModelRouter.resolve(profile_name)`
- **Every validation issue must include a `suggestion`** — tells the agent (or human) exactly what to fix, not just what's wrong
- **Stub mode preserved** — `llm_enabled=False` by default, flip per validator when ready

## Problem Decomposition

Three categories emerged from deep analysis of all 7 validators:

| Category | Validators | LLM approach |
|----------|-----------|--------------|
| **Text evaluators** | script_structure, dialogue_voice, prompt_readiness | Send artifact text + rubric to LLM. LLM evaluates semantic quality the stubs can't: dramatic conflict, character voice, prompt clarity. |
| **Multimodal evaluators** | reference_usability, scene_continuity | Send images + text to Gemini. LLM *looks at* frames — detecting visual continuity, subject match, moderation risks — not just checking dict metadata. |
| **Structural checklists** | assembly, delivery_completeness | Keep rule-based core. LLM adds qualitative review layer: narrative flow, emotional arc, production readiness. |

## Phase Files

| # | File | What | Effort |
|---|------|------|--------|
| 1 | `02-phase-1-foundation.md` | De-hardcode 30 model strings, schema changes, model routing profiles | Medium |
| 2 | `03-phase-2-prompt-design.md` | All 7 validator prompt templates with rubric weights, context injection, suggestion output | High |
| 3 | `04-phase-3-multimodal-adapter.md` | `chat_multimodal()` in ModelAdapter for Gemini image+text | Medium |
| 4 | `05-phase-4-base-validator.md` | `_validate_llm()` lifecycle, `set_services()`, `llm_enabled` flag | Medium |
| 5 | `06-phase-5-graph-wiring.md` | Pass services through validator dispatch, suggestion in repair feedback | Small |
| 6 | `07-phase-6-pilot.md` | `script_structure` as first LLM validator — prove the full chain | Medium |
| 7 | `08-phase-7-rollout.md` | Remaining 6 validators, one at a time | Medium |

## Core Design Decisions

| Decision | Rationale |
|----------|-----------|
| Reuse ModelRouter, not a separate router | One source of truth for model resolution. |
| Reuse PromptTemplateRegistry | One registry for all prompts. Validator templates use `agent_id` matching `validator_id`. |
| Extend ModelAdapter, don't create ValidatorAdapter | The adapter is a thin HTTP wrapper. Multimodal is just a new method. |
| Stub-first, then LLM opt-in | Protects existing tests, enables incremental rollout. |
| `model_profile` replaces `models` (not alongside) | Single source of truth. No migration complexity. |
| Gemini for multimodal, DeepSeek for text | Gemini: native image+text. DeepSeek: cheaper/faster for text-only. |
| DeliveryCompletenessValidator stays mostly rule-based | File existence checking is not an LLM task. LLM adds qualitative "production readiness" review. |

## Open Questions

1. **Cost control?** 7 validators × N artifacts = up to 140 LLM calls for a 20-shot film. For now: sequential, one per artifact, with `test` mode using stubs.
2. **Should validators produce individual artifacts?** Currently only consensus reports are saved. Individual validation reports could be debug artifacts.
3. **Prompt template authoring?** The 7 templates in Phase 2 are designed for correctness, not tuned for quality. They will need iteration based on real LLM output.
