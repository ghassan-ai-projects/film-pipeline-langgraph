# 04 Validation And MCP Product Surface

---

## Goal

Make validation and MCP the real operational control system.

Validation must change behavior.
MCP must expose complete operator workflows.

---

## Validation Final Result

When validation is complete:

- scripts, references, prompts, clips, and continuity are validated by real logic
- blocking findings stop downstream work
- warnings are preserved without pretending they are blockers
- validation reports are stored and inspectable

---

## Required Real Validators

- script quality and structure validator
- dialogue/voice validator
- reference usability validator
- prompt readiness validator
- clip quality validator
- prompt adherence validator
- scene continuity validator

Registry entries alone are not enough.

---

## MCP Final Result

When MCP productization is complete:

- an operator can run the full supported workflow through MCP only
- critical-path tools return real data and mutate real state
- approvals, validation, generation, rollback, and clip inspection are all available through MCP
- no operator needs hidden direct runtime access

---

## Required MCP Coverage

### Must Be Fully Implemented

- project creation and selection
- idea submission
- state inspection
- review package inspection
- phase approval and revision
- validation report inspection
- generation planning and execution
- checkpoint creation and inspection
- rollback request and execution
- provider health
- audit inspection
- clip output inspection
- downstream handoff evidence inspection

### Must Not Remain Stubbed

- generation tools
- validation tools
- rollback mutation tools
- core artifact inspection tools

The one exception is the expensive external video-rendering call itself, which may be mocked in
test mode. The MCP behavior around it must still be fully implemented and tested.

---

## Concrete Tests

### Unit Tests

- validator scoring and issue extraction
- MCP tool schema outputs
- confirmation-required tool behavior
- error contract behavior

### Integration Tests

- failed validation blocks next phase
- MCP approval creates checkpoint and advances state
- MCP rollback restores project state
- MCP validation tools reflect stored reports
- MCP artifact tools reflect stored artifacts

### Final Acceptance Tests

- an operator can drive `idea -> script approval -> validation review` only through MCP
- no critical-path MCP tool returns `stub: true`
- behavior tests assert real outcomes, not just response shape

---

## Acceptance Criteria

This area is done only when all of the following are true:

- validation results influence runtime behavior
- all critical-path MCP tools are fully wired
- operators can complete supported workflows entirely through MCP
- rollback, validation, and generation state are inspectable through MCP
- no critical-path acceptance test depends on stubbed tool responses
- non-video MCP claims are rejected unless covered by behavior tests
