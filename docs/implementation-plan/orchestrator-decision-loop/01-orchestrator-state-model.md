# Phase 01 — Orchestrator State Model

**Depends on:** Phase 01 (Schemas), Phase 05 (LangGraph Skeleton), Phase 07 (Agent Registry)
**Blocks:** Phases 02–07 in this folder

---

## Goal

Give the orchestrator a durable state model for decisions, review rounds, revision intent,
and approved baselines.

This phase should add state and records first. It should not change all routing behavior yet.

---

## Scope

Add explicit orchestration data for:

- current candidate artifacts by artifact family
- latest approved artifacts by artifact family
- active review cycle per phase
- pending revision requests
- orchestrator routing decisions
- convergence signals and escalation hints
- failure decisions from the failure-handling agent
- provider health snapshot (cached, refreshed on provider interaction)
- budget state awareness (current spend vs cap, blocking thresholds)

Keep the current dict-based graph state if that avoids a wider refactor.

---

## Files To Touch

- `src/film_pipeline/schemas/`
  Add narrow schemas only if the existing ones are insufficient.
- `src/film_pipeline/graph/`
  Add helpers for orchestrator state initialization and updates.
- `src/film_pipeline/app/runtime.py`
  Persist the new state fields cleanly.
- `tests/unit/graph/` and `tests/unit/app/`
  Verify state transitions and serialization.

---

## Checklist

- [ ] Define a small orchestrator state domain with stable keys
- [ ] Add a record shape for routing decisions
- [ ] Add a record shape for active review cycles
- [ ] Add a record shape for pending revision requests
- [ ] Add fields for candidate refs vs approved refs
- [ ] Add fields for convergence tracking signals
- [ ] Add a record shape for failure decisions (reusing the architecture blueprint's `FailureDecision` schema)
- [ ] Add a provider health snapshot field (status, blocked_reason, last_health_check)
- [ ] Add budget state fields for routing awareness (current spend, cap, blocking threshold exceeded)
- [ ] Ensure runtime persistence keeps these fields intact
- [ ] Add unit tests for state creation, update, and persistence

---

## Acceptance Criteria

- [ ] A project state can distinguish candidate refs from approved refs
- [ ] A project state can represent an active review cycle for a phase
- [ ] A revision request is represented as durable state, not just a warning issue
- [ ] Routing decisions can be stored and later inspected
- [ ] Failure decisions from the failure-handling agent are persisted and inspectable
- [ ] Provider health state is cached and used for routing decisions (not re-queried on every action)
- [ ] Budget state reflects current spend and blocking thresholds
- [ ] State survives runtime persistence and reload
- [ ] Existing happy-path project creation and phase progression tests still pass

---

## Risks

| Risk | Mitigation |
|------|------------|
| Too many new fields too early | Keep the state model minimal and directly tied to routing decisions |
| Schema churn spills across the repo | Prefer additive fields and helper functions over broad schema rewrites |
