# 05 Generation, Providers, And Clip Handoff

---

## Goal

Make generation safe and make clip handoff to downstream finishing tools real.

---

## Generation Final Result

When generation is complete:

- generation requests are ledgered durably
- submit/poll/download transitions are recoverable
- duplicate provider jobs are prevented
- provider failures pause work safely
- budget approval gates work before expensive execution

---

## Required Provider Behavior

- mock and real providers share the same runtime contract
- provider job ids are persisted before risky transitions
- quota, moderation, timeout, and ambiguous network failures are classified
- provider health changes are visible and actionable

---

## Required Clip Handoff Behavior

- persist generated clips as inspectable artifacts
- persist clip-level validation evidence
- persist the prompt and reference lineage needed for downstream finishing
- persist enough operator-visible metadata to hand clips to DaVinci Resolve safely

---

## Concrete Tests

### Unit Tests

- provider payload construction
- generation ledger transitions
- duplicate-prevention rules
- subtitle generation
- assembly manifest validation

### Integration Tests

- provider accepts job id and network fails afterward -> resume polls existing job
- quota exhaustion pauses queue safely
- generation resumes from latest safe snapshot
- generated clip artifacts remain inspectable after resume and rollback
- clip handoff evidence reports missing required inputs correctly

### Final Acceptance Tests

- generated assets become a validated clip artifact chain
- no duplicate submit occurs in ambiguous network-failure scenarios
- provider-block resolution resumes the correct job sequence

---

## Acceptance Criteria

This area is done only when all of the following are true:

- generation is idempotent and recoverable
- provider failures do not corrupt project state
- budget and approval policy gate expensive generation
- clip outputs are real artifacts built from the supported workflow
- clip handoff evidence is real and completeness-validated
