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
- [x] Real critical-path execution uses the dedicated prompt templates instead of generic prompt assembly
- [x] Template `agent_id` values match the actual registered/runtime agent ids
- [x] Prompt template version is observable in runtime evidence
- [x] Generic fallback prompts are impossible in critical-path execution
- [x] `film-knowledge-base/promt.md` is explicitly classified as runtime input, manual reference, or obsolete
- [x] Secret-redaction tests prove keys are not leaked

## Phase 02 - Core Agent Execution

- [x] Constitution, development, screenwriting, visual dev, shot bible, generation planning, and QC produce real artifacts
- [x] Downstream phases consume persisted upstream artifacts
- [x] Review packages reference real artifacts
- [x] Approval and checkpoint evidence references those artifacts
- [x] Real agent execution is prompt-governed (dedicated templates, not generic assembly)
- [x] Prompt template version, model profile, and KB context ref are persisted in runtime evidence
- [x] Clip-producing workflow artifacts are sufficient for validated external handoff

## Phase 03 - Dynamic Routing

- [x] Routing is capability-based and state-aware
- [x] Review and repair use specialized agents
- [x] Handoffs are persisted
- [x] Routing explanations are backed by stored records

## Phase 04 - Validation Runtime Control

- [x] Validators inspect real artifacts
- [x] Blocking findings stop downstream work
- [x] Repairable findings route to repair behavior
- [x] Validation tools expose real stored findings

Verification evidence:

- `tests/integration/test_validation_runtime.py` — 4/4 passing (validators fire in QC, blocking findings in state, MCP report/issue tools read stored data)
- `_run_validators()` in `src/film_pipeline/graph/nodes.py` scans upstream phases when phase=qc and persists `_validation_reports` + `issues`
- `get_validation_report()` and `list_validation_issues()` in MCP tools serve stored data sans current-phase precondition

## Phase 05 - MCP Surface And Generation Runtime

- [x] Remaining important MCP stubs are replaced with real behavior (get_project_summary, promote_test_to_production)
- [x] Non-video generation lifecycle is real and behavior-tested (plan, approve, submit, status, list, cancel, resume, promote)
- [x] Resume/polling avoids duplicate submit (checks SUBMITTED status + provider_job_id before re-submit)
- [x] Rollback behavior is meaningful (git checkpoint-based artifact restore)
- [x] Clip handoff evidence is operator-visible and non-placeholder (assemble_review_cut via AssemblyAgent, inspectable artifacts)
- [x] Coverage/stub tools (plan_coverage_group, etc.) are video-generation-adjacent per allowed-stub policy

## Phase 06 - E2E And Operator Proof

- [x] All required E2E scenarios pass
- [x] Smoke checks validate the documented workflow
- [x] Operator docs are complete and reproducible
- [ ] Release checks are green
- [x] `make ci-check` passes

---

## Final Ship Checklist

- [x] product gate green
- [x] lint green
- [x] mypy green
- [x] tests green
- [x] coverage >= 90%
- [x] build green
- [x] docs match commands and product behavior
- [ ] no core functionality missing under the allowed-stub policy
