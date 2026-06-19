# Phase 08 — Review Package Generator

**Depends on:** Phase 04 (Artifact Store), Phase 07 (Agent Registry)
**Blocks:** Phase 12 (E2E Mock Mini-Film)

---

## Goal

Implement the review package generator. Every human approval gate produces a structured review package containing: summary, artifact list, diff from last approved version, validation results, open issues, risks, cost impact, orchestrator recommendation, and available actions. The review package is what the human (or mock human) sees and acts on through MCP tools.

---

## Deliverables

### Files to Create

#### Review Package Generator (`src/film_pipeline/review/`)

- [ ] `generator.py` — `ReviewPackageGenerator` class: build packages per phase
- [ ] `templates.py` — review package templates per type (config, treatment, script, visual bible, reference, shot bible, generation plan, clip batch, final cut)
- [ ] `diff.py` — artifact diff engine (compare current vs last approved version)
- [ ] `summary.py` — orchestrator summary writer (executive summary, risks, recommendation)
- [ ] `actions.py` — available actions calculator (approve, request_revision, rollback, compare)
- [ ] `__init__.py`

#### Tests

- [ ] `tests/unit/review/test_generator.py` — package generation per phase
- [ ] `tests/unit/review/test_diff.py` — artifact diffing
- [ ] `tests/unit/review/test_actions.py` — available actions calculation
- [ ] `tests/integration/review/test_full_package.py` — full package with artifacts, validation, issues

---

## Task Checklist

- [ ] Implement `ReviewPackageGenerator`:
  - [ ] Input: project_id, phase, current artifacts, last approved artifacts, validation results, open issues, budget impact
  - [ ] Output: `ReviewPackage` (from Phase 01 schema)
- [ ] Implement review package types:
  - [ ] `config_review` — raw input, extracted signals, inferred values, proposed config
  - [ ] `treatment_review` — logline, premise, treatment, act map, theme map
  - [ ] `script_review` — script, scene intents, dialogue pass, character arc
  - [ ] `visual_bible_review` — character bibles, environment bibles, camera language, style bible
  - [ ] `reference_package_review` — reference sheets, validation scores, cross-angle consistency
  - [ ] `shot_bible_review` — master film matrix, continuity ledger, coverage groups
  - [ ] `generation_plan_review` — prompt packages, provider plan, cost estimate, schedule
  - [ ] `clip_batch_review` — generated clips, QC reports, continuity reports, cost
  - [ ] `final_cut_review` — assembly manifest, review cut, delivery package, final QC
- [ ] Implement artifact diff engine:
  - [ ] Compare current version vs last approved version
  - [ ] Show added, removed, changed fields
  - [ ] Attach diff to review package
- [ ] Implement orchestrator summary:
  - [ ] Executive summary (1-2 paragraphs)
  - [ ] Risk list (from issues + validation warnings)
  - [ ] Cost impact (from budget state)
  - [ ] Recommendation: approve, request_revision, or escalate
- [ ] Implement available actions:
  - [ ] `approve_phase` — always available if no blocking issues
  - [ ] `request_revision` — always available with note field
  - [   ] `rollback_to_checkpoint` — available if checkpoint exists
  - [ ] `compare_versions` — available if previous version exists
  - [ ] Blocked actions listed with reasons
- [ ] Implement MCP tool wiring:
  - [ ] `review_phase_artifacts` → generates and returns review package
  - [ ] `approve_phase` → records approval, creates checkpoint, advances phase
  - [ ] `request_revision` → records revision request, triggers repair loop
- [ ] Write unit tests for generator, diff, actions
- [ ] Write integration tests for full package
- [ ] Run `make ci-check`

---

## Review Package Schema (from Phase 01)

```json
{
  "review_package_id": "review:script:v3",
  "project_id": "film_2026_0001",
  "phase": "screenwriting",
  "type": "script_review",
  "summary": "Script v3 completes 2 scenes with improved dialogue...",
  "artifacts": [
    {"artifact_id": "artifact:script:S001:v3", "type": "script_scene", "status": "candidate"},
    {"artifact_id": "artifact:script:S002:v3", "type": "script_scene", "status": "candidate"}
  ],
  "diff_from_approved": {
    "added": ["artifact:script:S002:v3"],
    "changed": ["artifact:script:S001:v3"],
    "removed": []
  },
  "validation_results": [
    {"validator_id": "scene-writing-validator", "status": "pass_with_notes", "score": 85}
  ],
  "open_issues": [],
  "risks": ["Dialogue may be too dense for 30s runtime"],
  "cost_impact": {"estimated_remaining": "$2.50", "within_budget": true},
  "orchestrator_recommendation": "approve",
  "available_actions": ["approve_phase", "request_revision", "compare_versions"],
  "blocked_actions": []
}
```

---

## Acceptance Criteria

- [ ] Review packages are generated for all 9 review types
- [ ] Diff engine correctly shows added/removed/changed artifacts
- [ ] Orchestrator recommendation is present and reasoned
- [   ] Available actions are correctly calculated (blocking issues prevent approval)
- [ ] MCP tools (`review_phase_artifacts`, `approve_phase`, `request_revision`) work end-to-end
- [ ] Review packages contain enough info for mock human to make decisions
- [ ] All tests pass
- [ ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| Review packages too verbose | Summary first, details collapsible; mock human only needs summary + recommendation |
| Diff engine complexity | Start with field-level JSON diff; nested diff only for critical artifacts |
