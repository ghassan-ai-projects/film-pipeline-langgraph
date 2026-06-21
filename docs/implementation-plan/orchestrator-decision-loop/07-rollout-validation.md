# Phase 07 — Rollout Validation

**Depends on:** Phases 01–06 in this folder
**Blocks:** Completion of this orchestrator plan

---

## Goal

Prove the orchestrator-centered flow works end to end without requiring a large refactor.
Include failure-handling agent integration, provider-blocked-continue-unrelated-work, and
multi-model consensus scenarios.

---

## Scope

Add targeted tests and final checks for:

- multi-round revision behavior
- approved-baseline handoff between phases
- review package correctness
- MCP inspection surfaces
- no-regression happy path behavior
- failure-handling agent routing and decision persistence
- provider-blocked generation with continued planning/writing
- multi-model consensus report generation and disagreement surfacing
- profile-driven review strategy selection

This phase should favor a few high-signal tests over a large number of brittle tests.

---

## Files To Touch

- `tests/unit/graph/`
- `tests/unit/review/`
- `tests/unit/mcp/`
- `tests/integration/graph/`
- `tests/integration/mcp/`
- `tests/e2e/` if one scenario needs extension

---

## Checklist

- [ ] Add unit tests for orchestrator state and selected actions
- [ ] Add unit tests for revision request durability
- [ ] Add unit tests for approved-baseline resolution
- [ ] Add unit tests for failure decision persistence and routing
- [ ] Add unit tests for provider health snapshot caching
- [ ] Add integration test: human revision request -> rewrite -> re-review -> approve
- [ ] Add integration test: candidate v2 exists while approved v1 remains downstream baseline
- [ ] Add integration test: approval moves downstream baseline to the newly approved version
- [ ] Add integration test: provider error -> escalate_to_failure_handler -> structured failure decision -> graph routes accordingly
- [ ] Add integration test: provider blocked -> continue_unrelated_work (planning proceeds while generation paused)
- [ ] Add integration test: multi-model review produces consensus report with surfaced disagreements
- [ ] Add integration test: profile policy selects single-model vs multi-model review per artifact type
- [ ] Add MCP integration test for orchestrator summary and review package surfaces
- [ ] Run `make test-unit`
- [ ] Run `make test-integration`
- [ ] Run `make ci-check`

---

## Acceptance Criteria

- [ ] Multi-round review and revision work in the same phase
- [ ] No phase can silently skip required revision work
- [ ] Downstream phases consume approved baselines only
- [ ] MCP surfaces explain orchestrator decisions clearly
- [ ] Existing happy-path flow still passes after the incremental changes
- [ ] Failure-handling agent is invoked on provider errors and its decisions are persisted
- [ ] Unrelated planning/writing work continues when only generation is blocked
- [ ] Multi-model reviews produce consensus reports, not averaged scores
- [ ] Profile policy controls review strategy at decision time
- [ ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| New tests depend too much on internal structure | Test observable behavior and state transitions |
| Hard-to-debug orchestration regressions | Add high-signal audit assertions around route decisions and approvals |
