# Phase 11 — Checkpoint/Resume & Rollback

**Depends on:** Phase 04 (Artifact Store), Phase 05 (LangGraph Skeleton), Phase 10 (Mock Provider)
**Blocks:** Phase 12 (E2E Mock Mini-Film)

---

## Goal

Implement the versioning, checkpoint, resume, and rollback system. Every human approval creates a checkpoint. Every expensive operation is preceded by a checkpoint. Resume snapshots are written after every important generation transition. Rollback is film-aware — it understands artifact dependencies and produces invalidation reports before restoring.

Git is the underlying versioning backend. The pipeline adds semantic checkpoint metadata on top.

---

## Deliverables

### Files to Create

#### Checkpoint System (`src/film_pipeline/checkpoints/`)

- [ ] `manager.py` — `CheckpointManager`: create, list, get, compare, rollback
- [ ] `git_backend.py` — Git integration (commit, tag, branch, restore)
- [ ] `resume.py` — `ResumeManager`: create resume snapshots, find latest, resume from snapshot
- [ ] `invalidation.py` — `InvalidationEngine`: dependency graph, invalidation report
- [   ] `rollback.py` — `RollbackManager`: artifact rollback, phase rollback, project rollback
- [ ] `branches.py` — creative branch management (alternate endings, tone experiments)
- [ ] `__init__.py`

#### Tests

- [ ] `tests/unit/checkpoints/test_manager.py` — create, list, get checkpoints
- [ ] `tests/unit/checkpoints/test_git_backend.py` — git commit, tag, restore
- [ ] `tests/unit/checkpoints/test_resume.py` — snapshot creation, resume
- [   ] `tests/unit/checkpoints/test_invalidation.py` — dependency tracking, invalidation report
- [ ] `tests/unit/checkpoints/test_rollback.py` — artifact, phase, project rollback
- [ ] `tests/integration/checkpoints/test_rollback_with_deps.py` — rollback triggers invalidation

---

## Task Checklist

- [ ] Implement `CheckpointManager`:
  - [ ] `create_checkpoint(project_id, phase, reason, artifact_versions, approval_refs)` — creates git commit + tag + metadata
  - [ ] `list_checkpoints(project_id)` — returns all checkpoints
  - [ ] `get_checkpoint(checkpoint_id)` — returns checkpoint metadata
  - [   ] `compare_versions(version_a, version_b)` — diff artifacts between versions
- [ ] Implement Git backend:
  - [   ] `commit(message, files)` — stage and commit
  - [ ] `tag(name, message)` — create annotated tag (e.g., `checkpoint/script-approved-v3`)
  - [   ] `branch(name, base)` — create creative branch
  - [   ] `restore(commit, files)` — restore specific files from commit
  - [   ] `log(project_id)` — list commits for project
- [   ] Implement checkpoint metadata (from Phase 01 schema):
  - [   ] checkpoint_id, project_id, phase, created_at, reason
  - [   ] artifact_versions (dict of artifact → version)
  - [   ] graph_state_ref, approval_refs, validation_refs, budget_state_ref
  - [   ] git_commit, git_tag, git_branch
- [ ] Implement `ResumeManager`:
  - [   ] `create_snapshot(generation_id, graph_node, provider_job_id, last_safe_step, next_action)` — lightweight runtime checkpoint
  - [   ] `find_latest_snapshot(generation_id)` — find most recent resume point
  - [   ] `resume(snapshot)` — reload graph state, find non-terminal ledger rows, reacquire locks
  - [   ] Write snapshots: before submit, after job_id, after each poll, after download, after frame extraction, after failure decision
- [ ] Implement `InvalidationEngine`:
  - [   ] Build dependency graph: artifact type → dependent artifact types
  - [   ] Dependencies: character_bible → references, prompts, clip_validators; environment_bible → environment_boards, shot_prompts; script → scene_intents, shot_bible, prompts, continuity_ledger; project_config → model_routing, validators, provider_plans
  - [   ] `get_invalidation_report(rollback_target)` — produce report listing will_revert, will_invalidate, requires_regeneration, requires_human_confirmation
- [ ] Implement `RollbackManager`:
  - [ ] `rollback_artifact(artifact_id, target_version)` — revert single artifact, trigger invalidation
  - [ ] `rollback_to_checkpoint(checkpoint_id)` — revert all artifacts to checkpoint state
  - [ ] `confirm_rollback(invalidation_report)` — require human confirmation for approved artifacts or generated assets
  - [ ] Rollback creates a new commit (does not rewrite history)
- [ ] Implement creative branch management:
  - [   ] `create_branch(project_id, base_checkpoint, purpose)` — branch for creative experiment
  - [ ] `list_branches(project_id)` — list creative branches
  - [   ] `promote_branch(branch_id)` — promote branch to main
- [   ] Implement MCP tool wiring:
  - [ ] `list_checkpoints`, `create_checkpoint`, `get_checkpoint`
  - [ ] `compare_versions`, `list_artifact_versions`
  - [   ] `rollback_artifact`, `rollback_to_checkpoint`
  - [ ] `get_invalidation_report`
- [   ] Write unit tests for all components
- [ ] Write integration test: rollback triggers invalidation (E2E Scenario 7)
- [ ] Run `make ci-check`

---

## Invalidation Report Schema (from Phase 01)

```json
{
  "rollback_target": "version:script:v3",
  "will_revert": ["script"],
  "will_invalidate": [
    "scene_intents:v4",
    "shot_bible:v2",
    "prompt_registry:v2",
    "script_validation:v4"
  ],
  "requires_regeneration": false,
  "requires_human_confirmation": true
}
```

---

## Checkpoint Creation Points

| Trigger | Type | Git Tag |
|---------|------|---------|
| After human approval | Approval checkpoint | `checkpoint/<phase>-approved-v<n>` |
| Before generation batch | Pre-generation checkpoint | `checkpoint/before-gen-batch-<n>` |
| After generation batch | Post-generation checkpoint | `checkpoint/after-gen-batch-<n>` |
| After provider job_id recorded | Resume snapshot | (no tag, metadata only) |
| After provider block detected | Resume snapshot | (no tag, metadata only) |
| Before major revision | Pre-revision checkpoint | `checkpoint/before-<change>` |
| Before final export | Pre-delivery checkpoint | `checkpoint/before-delivery` |
| User manual request | Manual checkpoint | `checkpoint/manual-<n>` |

---

## Acceptance Criteria

- [ ] Checkpoints create git commits with semantic tags
- [   ] Checkpoint metadata includes all artifact versions and approval refs
- [ ] Resume snapshots are written at all required transition points
- [   ] Resume from snapshot correctly reloads state without duplicate submit
- [ ] Invalidation engine correctly identifies dependent artifacts
- [   ] Rollback produces invalidation report before executing
- [ ] Rollback requires human confirmation for approved artifacts or generated assets
- [   ] Rollback creates a new commit (does not rewrite history)
- [ ] Creative branches can be created, listed, and promoted
- [   ] All MCP checkpoint/rollback tools work
- [ ] All tests pass
- [   ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| Git operations in tests create noise | Use temp directories or isolated git repos per test |
| Invalidation graph is incomplete | Start with documented dependencies; add edges as discovered |
| Resume after crash misses state | Persist after every transition; test crash recovery explicitly |
