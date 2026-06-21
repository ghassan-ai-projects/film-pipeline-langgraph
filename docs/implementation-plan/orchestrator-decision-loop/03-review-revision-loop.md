# Phase 03 — Review And Revision Loop

**Depends on:** `02-action-selection-and-routing.md`, Phase 08 (Review), Phase 09 (Validation)
**Blocks:** Phases 04–07 in this folder

---

## Goal

Make review and revision rounds real, durable, and bounded. Add multi-model review synthesis
so that when multiple validators disagree, the orchestrator produces a consensus report
instead of silently averaging scores.

The orchestrator should be able to keep a phase open across multiple rounds until the work is
approved, escalated, or declared non-convergent.

---

## Scope

Implement the lifecycle for:

- reviewer output
- validator output
- multi-model consensus synthesis (when profile requires parallel independent review)
- orchestrator synthesis of reviewer disagreements
- revision requests
- targeted reruns in the same phase
- dependency invalidation (when a repair changes an artifact that downstream artifacts depend on)
- convergence and escalation decisions

This phase should fix the current gap where a revision request does not reliably force a new
artifact version and re-review cycle. It should also wire the existing `ConsensusBuilder`
(Phase 09) into the active orchestration loop.

---

## Files To Touch

- `src/film_pipeline/graph/nodes.py`
- `src/film_pipeline/graph/router.py`
- `src/film_pipeline/app/runtime.py`
- `src/film_pipeline/review/`
- `src/film_pipeline/validation/`
- `tests/unit/review/`
- `tests/unit/graph/`
- `tests/integration/graph/`

---

## Checklist

- [ ] Make human revision requests create durable revision state
- [ ] Create or persist `RevisionRequest` records during revision flows
- [ ] Ensure revision requests force a revise path before approval can happen
- [ ] Add targeted rewrite behavior for same-phase reruns
- [ ] Add review-round counters and convergence signals
- [ ] Add escalation rules for repeated failure or non-convergence
- [ ] Ensure review and validation outputs attach to the specific artifact version reviewed
- [ ] Wire `ConsensusBuilder` into the orchestration loop — produce a consensus report when multiple validators review the same artifact
- [ ] Implement profile-driven review strategy: single-model (fast) vs multi-model panel (strict) per artifact type
- [ ] Add dependency invalidation: when a repair changes an artifact, mark downstream artifacts that depend on it for re-review
- [ ] Add tests for one revision round, multiple revision rounds, and escalation behavior
- [ ] Add tests for multi-model review synthesis and consensus report generation
- [ ] Add tests for dependency invalidation chains

---

## Acceptance Criteria

- [ ] A human revision request triggers a real revise-and-re-review cycle
- [ ] A failed validation result can keep the graph in the same phase
- [ ] Repeated rounds produce durable history, not overwritten state
- [ ] The system can escalate when rounds are not converging
- [ ] Approval cannot bypass an unresolved pending revision cycle
- [ ] When profile policy requires multi-model review, a consensus report is produced before the orchestrator decides next action
- [ ] Validator disagreements are surfaced in the consensus report, not averaged away
- [ ] Repairing an upstream artifact invalidates downstream artifacts that depend on it, forcing re-review

---

## Risks

| Risk | Mitigation |
|------|------------|
| Revision loop becomes infinite | Add bounded policy and explicit convergence checks |
| Repair path becomes too generic | Prefer targeted same-phase reruns using existing creator agents |
