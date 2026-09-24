# Acceptance Checklist — film-pipeline-langgraph

Updated: 2026-06-29
Purpose: Current verified acceptance state. This file should reflect checked evidence only, not aspirational status.

---

## Current Verdict

Current state: `Accepted for validated-clips workflow with operator review`

What this means:

- code quality gates pass (`make ci-check` is green)
- critical-path MCP tools are wired, behavior-tested, and enforce confirmation
- the graph routes dynamically via `compute_actions()` / `after_phase()`
- declared MVP agents have implementation classes, prompt templates, and model profiles
- validation uses the four-status contract and governs generation readiness
- every artifact stores a real `kb_context_ref`; checkpoints are persisted
- rollback requires confirmation and produces invalidation artifacts
- mid-project profile changes are versioned and require human approval
- E2E scenarios for idea-to-validated-clips and operator recovery paths pass

The remaining gaps are in live-provider execution, full rendered delivery, and deeper multi-model parallelism — these are outside the current validated-clips acceptance target.

---

## Verified Now

### Code Quality Gates

- [x] `ruff check .` passes
  Current evidence: `make lint` passes
- [x] `mypy src tests` passes
  Current evidence: `make typecheck` passes
- [x] `make test` passes
  Current evidence: full `pytest` behavior run is green (`1658 passed, 2 skipped`)
- [x] Coverage ≥ 90%
  Current evidence: `90.05%` from `make ci-check`
- [x] `make build` re-verified locally
  Current evidence: `uv build` succeeds

### Runtime And Core Infrastructure

- [x] Runtime approval flow advances phases
- [x] Runtime creates git-backed checkpoints on approval and after graph steps
- [x] Graph routes dynamically via `compute_actions()` / `after_phase()`
- [x] Human approval gates cannot be silently bypassed
- [x] `.env` support exists for provider keys
- [x] `.env` is git-ignored
- [x] Product-gate enforcement exists
- [x] Mid-project profile changes are versioned, approved, and invalidate downstream artifacts

### Architecture And Structural Foundations

- [x] Sub-package boundaries match the architecture direction
- [x] Typed schema layer exists and is extensive
- [x] MCP registry and tool contract surface exist
- [x] Agent registry exists with capability-based routing
- [x] Validator registry exists with four-status contract
- [x] KB manifest and retrieval infrastructure exist
- [x] Mock provider infrastructure exists
- [x] Checkpoint and invalidation infrastructure exist with confirmation enforcement
- [x] Post-production planning infrastructure exists

---

## Product Gate

- [x] `make product-gate` passes

Current evidence:

- `make product-gate` returns `Product gate: PASS`
- the acceptance manifest allows only `start_generation_batch` to remain stubbed on the critical list

---

## MCP Acceptance

### Verified Implemented

- [x] Project management core: create, select, active project
- [x] Idea submission entry path
- [x] Review actions: approve phase, request revision
- [x] Orchestrator summary, next actions, blockers
- [x] KB lookup/context surfaces
- [x] Checkpoint listing/creation/inspection, rollback, and invalidation report access
- [x] Audit inspection surfaces
- [x] Provider health inspection surfaces
- [x] Review-cut and delivery-export helper surfaces
- [x] Operator comment tools: `add_operator_comment`, `list_operator_comments`
- [x] Profile change tools: `propose_profile_change`, `approve_profile_change`
- [x] All dangerous operations require `confirmed=True`

### Not Yet Accepted

- [ ] Full live-provider execution end-to-end in real mode
- [ ] Delta regeneration and composite validation surfaced as standalone MCP artifacts
- [ ] Complete rendered delivery pipeline with real providers

---

## Agent And Validation Acceptance

### Verified Implemented

- [x] Core agent framework exists
- [x] Real agent implementation files exist for the creative path
- [x] Validation implementation files exist for the critical path
- [x] Prompt/model adapter layer exists
- [x] Four-status validation contract: pass, pass_with_notes, needs_revision, blocked
- [x] Validation governs generation readiness

### Not Yet Accepted

- [ ] All agents produce fully specialized artifacts on every phase in real mode
- [ ] Multi-model parallel validation with live providers

---

## E2E Acceptance

### Verified Now

- [x] All 10 E2E scenario files exist
- [x] E2E suite structure exists in `tests/e2e/`
- [x] E2E tests execute within the full test run
- [x] The full `pytest` run is functionally green (`1658 passed, 2 skipped`)
- [x] Product-gate critical stub count reduced to `0` failing critical tools
- [x] Happy path scenario passes
- [x] Script revision scenario passes
- [x] Reference failure scenario passes
- [x] Quota exhausted scenario passes
- [x] Network error / no duplicate submit scenario passes
- [x] Continuity drift scenario passes
- [x] Rollback scenario passes
- [x] KB conflict scenario passes
- [x] Project ambiguity scenario passes
- [x] Dynamic flow scenario passes

---

## Productization Acceptance

### Verified Implemented

- [x] `app/runtime.py`
- [x] `app/bootstrap.py`
- [x] `app/health.py`
- [x] `app/smoke.py`
- [x] `app/version.py`
- [x] `make run-mcp`
- [x] `make demo-project`
- [x] `make release-check`
- [x] `make product-gate`
- [x] product-completion docs set exists
- [x] scorecard exists
- [x] `documentation/operations-guide.md`
- [x] `documentation/runbook-first-film.md`
- [x] `documentation/release-process.md`
- [x] `documentation/demo-guide.md`

### Not Yet Accepted

- [ ] Operator workflow proven from docs alone with live providers
- [ ] Full release-level delivery runbook for real-mode projects

---

## Not Accepted Yet

These remain hard blockers to calling the project a finished product for full live-provider production:

- live-provider execution proof with real API calls
- full rendered delivery pipeline with real providers
- comprehensive audit evidence from live model/provider execution

The repository is accepted as a working, tested, MCP-first implementation for the validated-clips workflow in mock/operator-review mode.

---

## Acceptance Rule

This file must stay subordinate to the harder standards in:

- `documentation/product-completion/00-product-standard.md`
- `documentation/product-completion/04-validation-and-mcp-product-surface.md`
- `documentation/product-completion/06-e2e-acceptance-and-release.md`
- `documentation/product-completion/acceptance-manifest.yaml`
