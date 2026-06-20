# 06 End-To-End Acceptance And Release

---

## Goal

Prove the system works as a real product and can be operated safely by another person.

---

## Required End-To-End Scenarios

These are mandatory product scenarios.

1. happy path: idea to validated clips
2. script revision loop
3. reference validation failure
4. quota exhausted pause/resume
5. network error after job id with no duplicate submit
6. continuity drift stop and repair
7. rollback after bad style change
8. KB conflict resolution
9. project ambiguity handling
10. dynamic blocked and available path routing

---

## Scenario Result Standard

Each scenario must prove all of the following:

- actions happen through MCP
- artifacts are created and persisted
- approvals are stored
- validation reports are stored
- checkpoint behavior is visible where required
- audit records explain the outcome

If a scenario only proves that functions compile or objects instantiate, it does not count.
If a scenario only checks response shape without checking resulting behavior, it does not count.

---

## Operator Productization

Release readiness requires:

- documented bootstrap path
- health checks
- run-mcp command
- smoke command
- release-check command
- demo profile
- operations guide
- first-film runbook
- release and rollback procedure

---

## Concrete Tests

### End-To-End Suite

- one file per scenario
- deterministic mock-mode baseline
- shared fixtures for project, KB, agents, validators, providers, and mock human
- assertions must verify behavior, stored state, and resulting artifacts

### Smoke Tests

- bootstrap succeeds on a fresh checkout
- MCP server starts successfully
- health checks report readiness and failures
- demo project flow runs in mock mode

### Release Validation

- format, lint, typecheck, test
- smoke suite
- docs and profile existence checks
- command-to-doc consistency checks

---

## Acceptance Criteria

This area is done only when all of the following are true:

- all 10 E2E scenarios pass
- the happy path produces a real validated-clip artifact chain
- failure-path scenarios prove safe stop, repair, resume, or rollback behavior
- smoke and release-check commands validate the supported operator workflow
- another operator can reproduce the documented mock-mode path from docs alone
- all non-video product claims are backed by behavior tests

---

## Final Release Gate

The product is release-ready only when:

- all prior documents in this folder meet acceptance criteria
- all 10 E2E scenarios pass
- critical-path MCP tools are non-stubbed
- mock-mode baseline is green
- docs match the real product behavior
