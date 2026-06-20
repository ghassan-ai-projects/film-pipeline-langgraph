# Phase 04 - Validation-Driven Runtime Control

Depends on: Phase 03
Blocks: Phases 05-06

---

## Goal

Make validation findings change runtime behavior in meaningful, operator-visible ways.

---

## Product Result

When this phase is complete:

- validators inspect real artifacts
- validators can pass, warn, block, and trigger repair paths
- runtime decisions reflect validator outcomes
- validation reports are stored, inspectable, and tied to later actions

---

## Implementation Work

### Validator Execution

- expand validator execution on stored artifacts
- ensure validators operate on the real outputs of:
  - script
  - references
  - shot plans
  - generated media metadata
  - assembly outputs

### Runtime Effects

- block downstream work on blocking findings
- route to repair agents for repairable issues
- require human review when policy thresholds demand it
- attach validation evidence to approvals, blockers, and audit events

### Product Surface

- `get_validation_report` must expose useful artifact-level detail
- `list_validation_issues` must reflect real stored findings

---

## Files To Create Or Modify

- `src/film_pipeline/validation/`
- `src/film_pipeline/graph/nodes.py`
- `src/film_pipeline/app/runtime.py`
- `src/film_pipeline/mcp/tools/__init__.py`
- validation/runtime behavior tests

---

## Mandatory Behavior Tests

- a blocking validation finding prevents downstream approval or generation
- a repairable finding routes to a repair path
- validation reports are stored against the actual artifact inspected
- MCP validation tools expose the stored findings
- audit records show that validation changed runtime behavior

---

## Acceptance Criteria

- [ ] validators inspect real artifacts in the supported path
- [ ] blocking findings stop downstream work
- [ ] repairable findings route to repair behavior
- [ ] validation findings are visible through MCP and audit surfaces
- [ ] runtime-control behavior is covered by integration/E2E tests

---

## Exit Condition

This phase is done when validation is a control system, not just a reporting subsystem.
