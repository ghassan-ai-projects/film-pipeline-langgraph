# Phase 06 - End-To-End Recovery, Operator Workflow, And Release Proof

Depends on: Phase 05
Blocks: final completion only

---

## Goal

Prove the system works as a product for another operator, not just for the current development context.

---

## Product Result

When this phase is complete:

- the required E2E scenarios pass with meaningful assertions
- operator docs are sufficient to bootstrap and run the system
- smoke and release checks validate the supported workflow
- the project can honestly be called product-complete

---

## Required E2E Scenarios

- happy path: idea to validated clips
- script revision loop
- reference validation failure
- quota exhausted pause/resume
- network error after job id with no duplicate submit
- continuity drift stop and repair
- rollback after bad style change
- KB conflict resolution
- project ambiguity handling
- dynamic blocked and available path routing

These must prove behavior, not just response shape.

---

## Operator Readiness Work

- complete:
  - `documentation/operations-guide.md`
  - `documentation/runbook-first-film.md`
  - `documentation/release-process.md`
  - `documentation/demo-guide.md`
- make docs match real commands, tool names, and supported profiles
- ensure a fresh operator can:
  - bootstrap
  - start MCP
  - create a project
  - run the mock-mode path
  - inspect failures
  - recover or rollback
  - inspect validated clips and handoff evidence

---

## Validation Commands

- `make ci-check`
- `make product-gate`
- smoke checks
- release checks
- command-to-doc consistency checks

---

## Files To Create Or Modify

- `tests/e2e/`
- `tests/smoke/`
- `documentation/operations-guide.md`
- `documentation/runbook-first-film.md`
- `documentation/release-process.md`
- `documentation/demo-guide.md`
- `README.md`
- release/smoke command implementation as needed

---

## Mandatory Behavior Tests

- each required scenario must assert:
  - MCP-driven actions
  - stored artifacts
  - stored approvals
  - stored validation reports
  - visible checkpoint behavior where applicable
  - audit explanation of the outcome
- a fresh operator path must be reproducible from docs

---

## Acceptance Criteria

- [ ] all required E2E scenarios pass with behavior-level assertions
- [ ] smoke checks validate the documented operator workflow
- [ ] release checks validate code, docs, and runtime readiness
- [ ] operator docs are complete and reproducible
- [ ] mock-mode supported path is reproducible by another operator from docs alone
- [ ] all non-video product claims are backed by behavior tests
- [ ] `make ci-check` passes

---

## Exit Condition

This phase is done when another operator can run the product safely and the test evidence proves the product claims.
