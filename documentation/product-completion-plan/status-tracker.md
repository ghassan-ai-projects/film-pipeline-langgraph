# Product Completion Plan - Status Tracker

Updated: 2026-06-20
Purpose: Track program progress without weakening the acceptance standard.

---

## How To Use

- update this file only from validated evidence
- do not mark a phase complete because code exists
- mark complete only when the phase acceptance criteria and tests are satisfied

---

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| 00 | Complete | Plan folder, acceptance manifest, checklist, and tracker are in place |
| 01 | Complete | All 9 critical-path agents have dedicated templates with matching agent_ids; runtime enforces templates via `PromptTemplateRegistry.get_required()`; `promt.md` classified as manual reference |
| 02 | Complete | Artifact spine is prompt-governed; handoff records persist `template_id` + `model_profile` as runtime evidence |
| 03 | Complete | Dynamic routing evidence is green: `tests/integration/test_dynamic_routing.py` passes |
| 04 | Complete | All 4 validation-runtime integration tests pass; `_run_validators` loads upstream artifacts for QC phase; MCP tools read stored `_validation_reports` and `issues` |
| 05 | Complete | `get_project_summary` and `promote_test_to_production` unstubbed; 5 remaining video-adjacent stubs per allowed-stub policy |
| 06 | Complete | All 10 E2E scenarios pass; smoke workflow includes executable manual short-film test; operator docs are now grouped under `documentation/` |

---

## Current Verified Snapshot

- format, lint, mypy, pytest, and product-gate are green
- latest verified pytest run: 722 tests pass, 94.06% coverage
- latest verified build: `uv build` succeeds
- All 9 critical-path agents use dedicated prompt templates via `PromptTemplateRegistry.get_required()`
- Handoff records persist `template_id` + `model_profile` for audit
- `film-knowledge-base/promt.md` classified as manual reference (not wired to runtime)
- All 9 prompt template agent_ids match runtime registry IDs
- `get_project_summary` unstubbed — returns real project state + artifact summaries
- `promote_test_to_production` unstubbed — transitions TEST→PRODUCTION in generation ledger
- 5 video-adjacent stubs remain (coverage tools, final cut) per allowed-stub policy
- `tests/integration/test_validation_runtime.py` — 4/4 passing
- `tests/integration/test_dynamic_routing.py` — green
- 10/10 E2E scenarios pass
- New practical docs hub: `docs/README.md`
- Executable manual walkthrough: `tests/smoke/test_manual_4min_mock_short.py`

All tracked phases in this plan are now complete for the current validated-clips target.

## Maintenance Notes

Out-of-scope items that may still be implemented later:

- Coverage group tools (`plan_coverage_group`, `list_coverage_groups`, `inspect_coverage_group`, `approve_coverage_generation`) — real schemas but no provider execution
- `assemble_final_cut` — post-production assembly (may remain stub per video-adjacent policy)
