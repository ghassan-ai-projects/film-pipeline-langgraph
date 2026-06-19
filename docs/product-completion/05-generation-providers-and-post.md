# 05 Generation, Providers, And Post

---

## Goal

Make generation safe and make post-production produce real outputs.

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

## Required Post Behavior

- assemble a real review cut from generated assets
- produce subtitle outputs
- export a delivery package
- validate delivery completeness

Planning-only post agents are not sufficient for final product completion.

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
- review cut assembly consumes persisted clip artifacts
- delivery export reports missing required assets correctly

### Final Acceptance Tests

- generated assets can be assembled into a review cut
- no duplicate submit occurs in ambiguous network-failure scenarios
- provider-block resolution resumes the correct job sequence

---

## Acceptance Criteria

This area is done only when all of the following are true:

- generation is idempotent and recoverable
- provider failures do not corrupt project state
- budget and approval policy gate expensive generation
- review cut is a real artifact built from generated assets
- delivery package export is real and completeness-validated
