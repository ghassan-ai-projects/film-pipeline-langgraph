# Phase 12 — End-to-End Mock Mini-Film

**Depends on:** Phases 05–11 (all core systems)
**Blocks:** Phases 13, 14, 15
**Human Gate:** Yes (mock human actor)

---

## Goal

Run the complete studio spine end-to-end with zero provider cost. A mini-film goes from idea to review cut through every phase, every approval gate, every validation layer, using mock provider, mock model, and mock human. This proves the entire architecture works before any paid provider is connected.

This phase implements and passes the **10 E2E test scenarios** from `e2e-test-scenarios.md`.

---

## Deliverables

### Files to Create

#### E2E Test Suite (`tests/e2e/`)

- [ ] `conftest.py` — shared test setup (project, mock provider, mock human, mock model, KB)
- [ ] `test_scenario_01_happy_path.py` — full pipeline: idea → review cut
- [ ] `test_scenario_02_script_revision.py` — revision at script gate
- [ ] `test_scenario_03_reference_failure.py` — bad reference caught before generation
- [ ] `test_scenario_04_quota_exhausted.py` — provider block during generation
- [ ] `test_scenario_05_network_error.py` — ambiguous provider failure, no duplicate submit
- [ ] `test_scenario_06_continuity_drift.py` — clip fails validation, no auto-regeneration
- [ ] `test_scenario_07_rollback.py` — rollback after bad style change
- [ ] `test_scenario_08_kb_conflict.py` — old KB rule doesn't override current policy
- [ ] `test_scenario_09_project_ambiguity.py` — ambiguous project resolution
- [   ] `test_scenario_10_dynamic_flow.py` — blocked path + available path simultaneously

#### Test Film Setup

- [ ] `tests/e2e/fixtures/memory_in_rain/` — test project:
  - [ ] `seed_idea.md` — "A lonely watchmaker hears the rain stop..."
  - [ ] `project_config.yaml` — narrative short, 30s, mock mode
  - [ ] `expected_artifacts.json` — list of artifacts that must exist after happy path
  - [   ] `expected_matrix.json` — 4 shots, 2 scenes, 1 act, 1 character, 1 environment

---

## Task Checklist

### Scenario 1: Happy Path (MUST PASS)

- [ ] Create test project via MCP `create_film_project`
- [ ] Submit idea via MCP `submit_idea`
- [ ] Mock human approves project config
- [   ] Orchestrator creates film constitution
- [ ] Mock human approves constitution
- [ ] Orchestrator creates treatment + scene intents
- [ ] Mock human approves treatment
- [   ] Orchestrator creates script
- [ ] Mock human approves script
- [   ] Orchestrator creates character + environment bibles + reference strategy
- [ ] Mock human approves visual bible + references
- [   ] Orchestrator creates shot bible + continuity ledger + master film matrix
- [ ] Mock human approves shot bible
- [   ] Orchestrator creates prompt packages + generation plan
- [ ] Mock human approves prompt readiness + generation spend ($0 mock)
- [   ] Mock provider generates 4 clips sequentially with last-frame chaining
- [   ] Validators run at clip and scene level
- [   ] Orchestrator assembles review cut
- [   ] Mock human approves review cut
- [   ] Orchestrator exports project lessons
- [   ] Verify: all expected artifacts exist
- [   ] Verify: every phase has approval record
- [   ] Verify: every shot maps to one matrix row
- [   ] Verify: each shot after first has input_frame_ref
- [   ] Verify: continuity ledger has state in/out for every shot
- [   ] Verify: validation reports pass or pass with notes
- [   ] Verify: audit log explains agents, KB context, provider actions

### Scenario 2: Script Revision (MUST PASS)

- [ ] Run happy path until script review
- [ ] Mock human requests revision ("dialogue too explanatory")
- [   ] Orchestrator creates revision issue
- [ ] Screenwriter revises affected scenes
- [   ] Validators re-check dialogue, character voice, theme
- [   ] Mock human approves revised script
- [   ] Verify: old script version remains available
- [   ] Verify: revised script has new version
- [   ] Verify: no shot bible exists before revised script approval

### Scenario 3: Reference Failure (MUST PASS)

- [   ] Run until visual bible/reference review
- [   ] Mock reference validator blocks character identity sheet
- [   ] Orchestrator creates reference issue
- [   ] Reference agent regenerates failed sheet
- [   ] Validator re-checks
- [   ] Mock human approves fixed references
- [   ] Verify: no prompt package uses rejected reference
- [   ] Verify: reference index marks only approved assets as usable

### Scenario 4: Quota Exhausted (MUST PASS)

- [   ] Run happy path until generation starts
- [   ] First 2 shots complete successfully
- [   ] Third shot submit returns quota_exhausted
- [   ] Failure-handling agent classifies as provider_account
- [   ] Generation queue pauses
- [   ] Verify: completed shots remain active
- [   ] Verify: third shot not retried
- [   ] Verify: provider health = blocked_quota
- [   ] Mock human resolves provider block
- [   ] Provider health check passes
- [   ] Generation resumes from shot 3 without resubmitting 1-2
- [   ] Verify: no duplicate job ids

### Scenario 5: Network Error After Job ID (MUST PASS)

- [   ] Submit shot S001-02
- [   ] Provider accepts, creates job id
- [   ] Client receives network error after accept
- [   ] Ledger already contains provider job id
- [   ] Orchestrator resumes
- [   ] System polls existing job id (no resubmit)
- [   ] Output downloaded and ingested
- [   ] Chain continues to next shot
- [   ] Verify: no second submit for S001-02
- [   ] Verify: provider job id reused

### Scenario 6: Continuity Drift (MUST PASS)

- [   ] Generate clips until S002-01 completes
- [   ] Clip validator flags severe environment drift
- [   ] Scene continuity validator blocks continuation
- [   ] Orchestrator creates issue
- [   ] Verify: no automatic regeneration
- [   ] Verify: dependent chain paused
- [   ] Mock human chooses re-anchor
- [   ] Re-anchor plan created, prompt/reference revised
- [   ] Pipeline resumes from affected shot

### Scenario 7: Rollback (SHOULD PASS)

- [   ] Run until visual bible approval
- [   ] Create checkpoint
- [   ] Request style revision (neon cyberpunk)
- [   ] User dislikes, requests rollback
- [   ] System creates invalidation report
- [   ] User confirms rollback
- [   ] Artifacts restore to checkpoint
- [   ] Verify: checkpoint discoverable via MCP
- [   ] Verify: invalidation report lists affected artifacts
- [   ] Verify: current state uses restored artifacts

### Scenario 8: KB Policy Conflict (SHOULD PASS)

- [   ] Run quota exhaustion scenario
- [   ] KB context builder finds conflicting rules (old fallback vs current stop policy)
- [   ] Canonical policy wins
- [   ] Orchestrator records excluded KB ref
- [   ] Verify: old rule in excluded_refs with reason
- [   ] Verify: no automatic provider switch
- [   ] Verify: `kb_explain_context_choice` explains decision

### Scenario 9: Project Ambiguity (SHOULD PASS)

- [   ] Create two projects: "memory-in-rain" and "memory-in-snow"
- [   ] User says "approve references for memory"
- [   ] MCP returns ambiguous match
- [   ] No state mutation occurs
- [   ] User selects project via `set_active_project`
- [   ] Approval proceeds only for selected project
- [   ] Verify: no approval during ambiguity
- [   ] Verify: audit log records blocked ambiguous request

### Scenario 10: Dynamic Flow (SHOULD PASS)

- [   ] Run until visual development
- [   ] Character reference validator blocks main character identity sheet
- [   ] Environment bible validation passes
- [   ] Verify: `get_next_actions` shows blocked + available actions
- [   ] Verify: shot bible creation disabled (references not approved)
- [   ] Verify: environment bible approval available while character repair pending
- [   ] Mock human approves environment bible
- [   ] Character reference repaired, validated, approved
- [   ] Shot bible creation becomes available

---

## Acceptance Criteria

### MUST PASS (Acceptance Baseline)

- [ ] Scenario 1: Happy path — full pipeline coherence
- [ ] Scenario 4: Provider quota exhausted — safe blocking
- [   ] Scenario 5: Network error after job id — duplicate prevention
- [   ] Scenario 6: Clip continuity failure — validation-driven stop

### SHOULD PASS

- [   ] Scenario 2: Script revision gate
- [   ] Scenario 3: Reference validation failure
- [   ] Scenario 7: Rollback after bad style change
- [   ] Scenario 8: KB policy conflict
- [   ] Scenario 9: Active project ambiguity
- [   ] Scenario 10: Dynamic flow

### Universal Checks

- [   ] All state changes through MCP tools
- [   ] Every artifact has metadata
- [   ] Every generated artifact has kb_context_ref
- [   ] Every phase gate creates review package
- [   ] Approvals are persisted
- [   ] Mock human approvals marked as test approvals
- [   ] Checkpoints created after approvals
- [   ] Mock generation writes ledger rows
- [   ] No duplicate provider submissions
- [   ] Audit log can explain final state
- [   ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| E2E tests are slow | Use mock provider (fast); keep mini-film to 4 shots, 2 scenes |
| Integration bugs surface late | Run Scenario 1 first; fix before attempting others |
| Mock human too permissive | Test with multiple decision profiles (approve_all, revise_script_once, reject_bad_reference) |
| State persistence issues | Test interrupt/resume explicitly in Scenario 5 |
