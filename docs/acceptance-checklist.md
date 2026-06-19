# Acceptance Checklist — film-pipeline-langgraph

Updated: 2026-06-20
Purpose: Current verified acceptance state. This file should reflect checked evidence only, not aspirational status.

---

## Current Verdict

Current state: `Partially accepted`

What this means:

- code quality is strong
- several core product pieces are real and tested
- the repository is not yet accepted as a working product

The main blockers today are:

- `make test` is not green because one unit test fails and coverage is below the required threshold
- `make product-gate` is not green because critical MCP tools still return stubs
- the product still does not satisfy the hard completion standard in `docs/product-completion/`

---

## Verified Now

### Code Quality Gates

- [x] `ruff check .` passes
- [x] `mypy src tests` passes
- [ ] `make test` passes
  Current evidence: one unit test currently fails in `tests/unit/app/test_product_gate.py`, and total coverage is `86.18%`, below the required `90%`.
- [ ] Coverage ≥ 90%
  Current evidence: `86.18%`
- [ ] `make build` re-verified locally
  Current note: still not re-verified in this restricted environment

### Runtime And Core Infrastructure

- [x] Runtime approval flow advances phases
- [x] Runtime creates git-backed checkpoints on approval
- [x] Graph routes from current phase
- [x] `.env` support exists for provider keys
- [x] `.env` is git-ignored
- [x] Product-gate enforcement exists

### Architecture And Structural Foundations

- [x] Sub-package boundaries match the architecture direction
- [x] Typed schema layer exists and is extensive
- [x] MCP registry and tool contract surface exist
- [x] Agent registry exists
- [x] Validator registry exists
- [x] KB manifest and retrieval infrastructure exist
- [x] Mock provider infrastructure exists
- [x] Checkpoint and invalidation infrastructure exist
- [x] Post-production planning infrastructure exists

---

## Product Gate

- [ ] `make product-gate` passes

Current failing reason:

Critical MCP tools still stubbed:

- `approve_generation_spend`
- `cancel_generation_request`
- `get_generation_status`
- `list_active_generations`
- `plan_generation_batch`
- `resume_generation_polling`

Interpretation:

- the gate is working correctly
- the repo is not yet allowed to claim working-product status

---

## MCP Acceptance

### Verified Implemented

- [x] Project management core: create, select, active project
- [x] Idea submission entry path
- [x] Review actions: approve phase, request revision
- [x] Orchestrator summary, next actions, blockers
- [x] KB lookup/context surfaces
- [x] Checkpoint listing/creation/inspection and invalidation report access
- [x] Audit inspection surfaces
- [x] Provider health inspection surfaces
- [x] Review-cut and delivery-export helper surfaces

### Not Yet Accepted

- [ ] Generation MCP path complete
- [ ] Validation MCP path complete
- [ ] Artifact inspection path complete
- [ ] Critical state inspection path complete
- [ ] Rollback mutation path fully complete under the hard product standard

---

## Agent And Validation Acceptance

### Verified Implemented

- [x] Core agent framework exists
- [x] Real agent implementation files now exist for part of the creative path
- [x] Validation implementation files now exist for part of the critical path
- [x] Prompt/model adapter layer exists

### Not Yet Accepted

- [ ] All critical-path agents produce real persisted artifacts end to end
- [ ] All core agents adopt dedicated prompt-framework templates in real execution
- [ ] Dynamic agent routing is fully proven in the supported workflow
- [ ] Validation governs all major downstream runtime behavior

---

## E2E Acceptance

### Verified Now

- [x] All 10 E2E scenario files exist
- [x] E2E suite structure exists in `tests/e2e/`
- [x] E2E tests execute within the full test run
- [x] Product-gate critical stub count reduced from 12 to 6

### Not Yet Accepted As Product Proof

- [ ] Happy path accepted as real product proof
- [ ] Script revision accepted as real product proof
- [ ] Reference failure accepted as real product proof
- [ ] Quota exhausted accepted as real product proof
- [ ] Network error / no duplicate submit accepted as real product proof
- [ ] Continuity drift accepted as real product proof
- [ ] Rollback accepted as real product proof
- [ ] KB conflict accepted as real product proof
- [ ] Project ambiguity accepted as real product proof
- [ ] Dynamic flow accepted as real product proof

Reason:

- existence of scenario files is not enough by itself
- final acceptance still depends on the harder product criteria and a passing product gate

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

### Not Yet Accepted

- [ ] `docs/operations-guide.md`
- [ ] `docs/runbook-first-film.md`
- [ ] `docs/release-process.md`
- [ ] `docs/demo-guide.md`
- [ ] operator workflow proven from docs alone

---

## Not Accepted Yet

These remain hard blockers to calling the project a working product:

- critical MCP tools still stubbed
- current unit suite is not fully green
- coverage gate below required threshold
- full product completion criteria in `docs/product-completion/` still unmet
- core artifact-producing workflow is not yet fully complete across all critical phases
- full agent/prompt/dynamic-routing adoption is not yet complete
- validation is not yet complete enough to certify the whole product

---

## Acceptance Rule

This file must stay subordinate to the harder standards in:

- `docs/product-completion/00-product-standard.md`
- `docs/product-completion/04-validation-and-mcp-product-surface.md`
- `docs/product-completion/06-e2e-acceptance-and-release.md`
- `docs/product-completion/acceptance-manifest.yaml`

If this checklist is ever more optimistic than those files or the current validation results, this checklist is wrong and must be corrected.
