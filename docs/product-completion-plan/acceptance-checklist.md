# Product Completion Plan - Acceptance Checklist

Updated: 2026-06-20
Purpose: Master checklist for the execution program in this folder.

---

## Release Rule

The product may be called complete only when every item below is green and the evidence exists in code, tests, and docs.

---

## Phase 00 - Program Rules

- [x] Hard acceptance language is in place
- [x] Allowed stub policy is explicit
- [x] Validation commands are defined
- [x] Checklist-to-phase traceability exists

## Phase 01 - Model Routing And Prompt Framework

- [x] No hard-coded model defaults remain in core agent execution paths
- [x] Critical agents resolve models through config and routing policy
- [x] Dedicated prompt templates exist for all critical-path agents
- [x] Prompt template version is observable in runtime evidence
- [x] Secret-redaction tests prove keys are not leaked

## Phase 02 - Core Agent Execution

- [x] Constitution, development, screenwriting, visual dev, shot bible, generation planning, QC, and assembly produce real artifacts
- [x] Downstream phases consume persisted upstream artifacts
- [x] Review packages reference real artifacts
- [x] Approval and checkpoint evidence references those artifacts

## Phase 03 - Dynamic Routing

- [ ] Routing is capability-based and state-aware
- [ ] Review and repair use specialized agents
- [ ] Handoffs are persisted
- [ ] Routing explanations are backed by stored records

## Phase 04 - Validation Runtime Control

- [ ] Validators inspect real artifacts
- [ ] Blocking findings stop downstream work
- [ ] Repairable findings route to repair behavior
- [ ] Validation tools expose real stored findings

## Phase 05 - MCP Surface And Generation Runtime

- [ ] Remaining important MCP stubs are replaced with real behavior
- [ ] Non-video generation lifecycle is real and behavior-tested
- [ ] Resume/polling avoids duplicate submit
- [ ] Rollback behavior is meaningful
- [ ] Final-cut assembly is operator-visible and non-placeholder

## Phase 06 - E2E And Operator Proof

- [ ] All required E2E scenarios pass
- [ ] Smoke checks validate the documented workflow
- [ ] Operator docs are complete and reproducible
- [ ] Release checks are green
- [ ] `make ci-check` passes

---

## Final Ship Checklist

- [ ] product gate green
- [ ] lint green
- [ ] mypy green
- [ ] tests green
- [ ] coverage >= 90%
- [ ] build green
- [ ] docs match commands and product behavior
- [ ] no core functionality missing under the allowed-stub policy
