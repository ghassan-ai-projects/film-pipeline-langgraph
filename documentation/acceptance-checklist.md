# Acceptance Checklist — film-pipeline-langgraph

Updated: 2026-06-20
Purpose: Current verified acceptance state. This file should reflect checked evidence only, not aspirational status.

---

## Current Verdict

Current state: `Partially accepted`

What this means:

- code quality is strong
- several core product pieces are now real and behavior-tested
- the repository is not yet accepted as a working product

The main blockers today are:

- lint is not green
- mypy is not green
- the full test suite is functionally green, but the coverage gate still fails
- the product still does not satisfy the hard completion standard in `documentation/product-completion/`

---

## Verified Now

### Code Quality Gates

- [ ] `ruff check .` passes
  Current evidence: fails on `tests/integration/test_generation_mcp.py` and `tests/unit/app/test_app_ops.py`
- [ ] `mypy src tests` passes
  Current evidence: fails on `tests/integration/test_generation_mcp.py` and `tests/unit/app/test_app_ops.py`
- [ ] `make test` passes
  Current evidence: full `pytest` behavior run is functionally green, but the coverage gate fails at `86.82%`, below the required `90%`.
- [ ] Coverage ≥ 90%
  Current evidence: `86.82%`
- [ ] `make build` re-verified locally
  Current note: `uv build` could not be re-verified here because the build backend dependency resolution needed network access

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

- [x] `make product-gate` passes

Current evidence:

- `UV_CACHE_DIR=.uv-cache make product-gate` returns `Product gate: PASS`
- the acceptance manifest currently allows only `start_generation_batch` to remain stubbed on the critical list

Remaining non-critical MCP stubs observed in `src/film_pipeline/mcp/tools/__init__.py`:

- `find_project`
- `get_project_summary`
- `get_intake_analysis`
- `approve_intake`
- `start_generation_batch`
- `promote_test_to_production`
- `rollback_artifact`
- `plan_coverage_group`
- `list_coverage_groups`
- `inspect_coverage_group`
- `approve_coverage_generation`
- `assemble_final_cut`

Interpretation:

- the product gate is working and is now green
- critical MCP gating is materially better than the prior review state
- some product-surface gaps still remain even though they no longer fail the gate

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

- [ ] All non-video generation MCP behavior is complete under the hard product standard
- [ ] Validation MCP path complete
- [ ] Artifact inspection path complete
- [ ] Critical state inspection path complete
- [ ] Rollback mutation path fully complete under the hard product standard
- [ ] Coverage-group product surface complete
- [ ] Final-cut assembly product surface complete

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
- [x] The full `pytest` run is functionally green (`488 passed`) before the coverage gate failure is applied
- [x] Product-gate critical stub count reduced to `0` failing critical tools

### Not Yet Accepted As Product Proof

- [ ] Happy path accepted as release-level product proof
- [ ] Script revision accepted as release-level product proof
- [ ] Reference failure accepted as release-level product proof
- [ ] Quota exhausted accepted as release-level product proof
- [ ] Network error / no duplicate submit accepted as release-level product proof
- [ ] Continuity drift accepted as release-level product proof
- [ ] Rollback accepted as release-level product proof
- [ ] KB conflict accepted as release-level product proof
- [ ] Project ambiguity accepted as release-level product proof
- [ ] Dynamic flow accepted as release-level product proof

Reason:

- test presence and passing status are necessary, but the hard product docs still require end-to-end artifact, audit, recovery, and operator-proof evidence
- final acceptance still depends on the harder product criteria, green quality gates, and operator reproducibility from docs

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

- [ ] `documentation/operations-guide.md`
- [ ] `documentation/runbook-first-film.md`
- [ ] `documentation/release-process.md`
- [ ] `documentation/demo-guide.md`
- [ ] operator workflow proven from docs alone

---

## Not Accepted Yet

These remain hard blockers to calling the project a working product:

- lint is currently failing
- mypy is currently failing
- coverage gate below required threshold
- full product completion criteria in `documentation/product-completion/` still unmet
- several non-critical MCP surfaces still return stubs
- core artifact-producing workflow is not yet fully complete across all claimed critical phases
- full agent/prompt/dynamic-routing adoption is not yet complete
- validation is not yet complete enough to certify the whole product

---

## Acceptance Rule

This file must stay subordinate to the harder standards in:

- `documentation/product-completion/00-product-standard.md`
- `documentation/product-completion/04-validation-and-mcp-product-surface.md`
- `documentation/product-completion/06-e2e-acceptance-and-release.md`
- `documentation/product-completion/acceptance-manifest.yaml`

If this checklist is ever more optimistic than those files or the current validation results, this checklist is wrong and must be corrected.
