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
| 01 | Complete | Model-routing and prompt-framework tests are green; core execution no longer depends on the old direct default path |
| 02 | Complete | Core artifact-producing spine is implemented and was previously advanced to complete status |
| 03 | Complete | Dynamic routing evidence is green: `tests/integration/test_dynamic_routing.py` passes |
| 04 | Complete | All 4 validation-runtime integration tests pass; `_run_validators` loads upstream artifacts for QC phase; MCP tools read stored `_validation_reports` and `issues` |
| 05 | Planned | Product gate is green, but important MCP/product-surface items still remain |
| 06 | Planned | E2E/operator-proof phase still depends on finishing validation and MCP completion |

---

## Current Verified Snapshot

- `make product-gate` is green
- `make ci-check` is green (format, lint, mypy, 644 tests, 92.42% coverage, build)
- `tests/integration/test_validation_runtime.py` — 4/4 passing
- `tests/integration/test_dynamic_routing.py` — green
- Model-routing and prompt-runner unit tests — green

Phase 04 was completed by:

1. Fixing `_run_validators()` in `src/film_pipeline/graph/nodes.py` to scan upstream phases (script, visual_dev, etc.) when running in the QC phase, instead of only the current phase
2. Making `get_validation_report()` and `list_validation_issues()` in `src/film_pipeline/mcp/tools/__init__.py` serve stored data even when `current_phase` is not set, falling back to the phase check only for live validation
3. Turning `tests/integration/test_validation_runtime.py` fully green

---

## Immediate Next Slice

Phase 05 — MCP Surface and Generation Runtime:

- Replace remaining important MCP stubs with real behavior
- Non-video generation lifecycle: real and behavior-tested
- Resume/polling idempotency
- Rollback behavior
- Final-cut assembly operator-visible and non-placeholder
