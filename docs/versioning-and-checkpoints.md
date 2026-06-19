# Versioning And Checkpoints

## Purpose

Creative pipelines need safe rollback. A change can improve one scene while damaging
continuity, tone, character identity, or downstream prompts.

The system should version important artifacts and create checkpoints at review gates so the
user can revert to a known-good state.

Git can be the underlying versioning backend. The film pipeline should add semantic checkpoint
metadata on top of git so users can think in film terms, such as "approved script" or "before
reference regeneration," instead of only commit hashes.

## Git As Versioning Backend

Use git for:

- text artifact history
- config history
- schema history
- prompt registry history
- matrix and ledger history
- validation reports
- checkpoint metadata
- rollback mechanics
- branch experiments

Use git carefully for generated media:

- small metadata and manifests should be committed
- large generated media may need git LFS or external asset storage
- generated clip files should be referenced by manifest even if not stored directly in git

## Semantic Layer Over Git

The system should create film-aware git commits and tags.

Examples:

```text
checkpoint/config-approved-v1
checkpoint/treatment-approved-v2
checkpoint/script-approved-v3
checkpoint/references-approved-v1
checkpoint/before-generation-batch-001
checkpoint/final-delivery-v1
```

Git handles storage and rollback. The pipeline handles meaning.

## Commit Policy

Create commits:

- after every human approval
- before every expensive generation run
- after every generation batch manifest update
- before changing project config
- before changing locked bibles
- before final export
- when the user manually asks for a checkpoint

Suggested commit message format:

```text
checkpoint: approve script v3

Project: film_2026_0001
Phase: screenwriting
Artifacts:
- script.v3
- scene-intents.v2
- continuity-ledger.v2
Validation:
- script-validation.v3
Approval: approval:script:v3
```

## Git Branches For Creative Alternatives

Use git branches for larger creative experiments.

Examples:

```text
film/memory-in-color/main
film/memory-in-color/alt-ending
film/memory-in-color/darker-tone
film/memory-in-color/reference-redesign
```

Branch when:

- exploring an alternate ending
- changing major tone or style
- redesigning main references
- trying a different act structure
- changing provider strategy in a way that may affect many artifacts

Use normal git merge/rebase only through pipeline-aware tooling where possible, because the
system must also update checkpoint metadata and run invalidation checks.

## What Must Be Versioned

Version these artifacts:

- project config
- film constitution
- story bible
- treatment
- script
- scene intent sheets
- character bible
- environment bible
- camera language bible
- reference index
- master film matrix
- continuity ledger
- prompt registry
- generation plan
- validation reports
- assembly manifest
- delivery package

Version runtime state:

- graph state
- active phase
- approvals
- issues
- budget state
- provider run state
- generation checkpoints
- provider health state
- failure decisions
- resume tokens

## Version Types

### Artifact Version

Every meaningful document or asset receives a version.

Example:

```text
script.v1
script.v2
script.v3
```

### Checkpoint

A checkpoint is a snapshot of project state at a meaningful moment.

Examples:

- after config approval
- after treatment approval
- after script approval
- after reference approval
- before generation batch
- after generation batch
- before final delivery

### Resume Snapshot

A resume snapshot is a lightweight runtime checkpoint used to continue after interruptions.
It is not necessarily a creative approval point.

Create resume snapshots:

- before provider submit
- immediately after provider job id is stored
- after each poll result
- after asset download
- after frame extraction
- after failure-handling decision
- after provider health changes

Suggested shape:

```json
{
  "resume_token": "resume:S001-01:production:v2",
  "project_id": "film_2026_0001",
  "graph_node": "poll_generation",
  "generation_id": "gen:S001-01:production:v2",
  "provider_job_id": "job_123",
  "last_safe_step": "provider_job_id_recorded",
  "next_action": "poll_provider",
  "blocking_reason": null,
  "failure_decision_ref": null,
  "created_at": "2026-06-19T12:45:00Z"
}
```

Resume snapshots should be written often, but they do not all need human-facing git tags.
The latest snapshot for each active job must be easy for the orchestrator to find.

### Revision Branch

A branch is used when exploring a change without destroying the approved path.

Examples:

- alternate ending
- darker tone
- different character design
- shorter act two
- alternative reference set

## Checkpoint Policy

Create automatic checkpoints:

- after every human approval
- before every expensive generation run
- after every generation batch
- after provider job id is recorded
- after a provider/account block is detected
- after a resumable failure decision is written
- before applying a major revision
- before changing project config
- before changing locked bibles
- before final export

Create manual checkpoints when the user says:

- "save this version"
- "checkpoint this"
- "I like this direction"
- "keep this before we try another option"

## Version Metadata

Every version should store:

```json
{
  "version_id": "version:script:v3",
  "artifact_id": "artifact:script",
  "project_id": "film_2026_0001",
  "parent_version": "version:script:v2",
  "created_at": "2026-06-19T12:00:00Z",
  "created_by": "dialogue-agent",
  "reason": "Shortened dialogue and improved character voice.",
  "change_summary": "",
  "validation_refs": [],
  "approval_ref": null,
  "status": "candidate"
}
```

Status values:

- `candidate`
- `approved`
- `superseded`
- `rejected`
- `archived`

## Checkpoint Metadata

Every checkpoint should store:

```json
{
  "checkpoint_id": "checkpoint:script-approved:v1",
  "project_id": "film_2026_0001",
  "phase": "screenwriting",
  "created_at": "2026-06-19T12:30:00Z",
  "reason": "Human approved script v3.",
  "artifact_versions": {
    "project_config": "version:project-config:v1",
    "film_constitution": "version:film-constitution:v1",
    "script": "version:script:v3",
    "scene_intents": "version:scene-intents:v2",
    "continuity_ledger": "version:continuity-ledger:v2"
  },
  "graph_state_ref": "state:graph:screenwriting:v5",
  "approval_refs": ["approval:script:v3"],
  "validation_refs": ["validation:script:v3"],
  "budget_state_ref": "budget:v2"
}
```

When git is the backend, checkpoint metadata should also include:

```json
{
  "git_commit": "abc123",
  "git_tag": "checkpoint/script-approved-v3",
  "git_branch": "film/memory-in-color/main"
}
```

## Rollback Levels

### 1. Artifact Rollback

Revert one artifact to an earlier version.

Example:

- revert `script.v4` to `script.v3`

Use when:

- a rewrite made dialogue worse
- a reference sheet drifted
- a prompt revision harmed consistency

Must trigger:

- dependency check
- downstream invalidation check
- targeted re-validation

Git implementation:

- restore specific files from the checkpoint commit
- create a new commit that records the rollback
- do not silently rewrite history for normal user rollback

### 2. Phase Rollback

Revert the whole phase to a checkpoint.

Example:

- return to the approved script checkpoint

Use when:

- many artifacts changed together
- validation shows a phase direction failed
- the user dislikes a major creative turn

### 3. Project Rollback

Revert the full project state to a checkpoint.

Use when:

- config changes damaged the project
- generation strategy was wrong
- references need to be rebuilt from a known-good point

Requires human confirmation.

Git implementation:

- reset the working project files to a checkpoint commit through a pipeline command
- create a new rollback commit unless the user explicitly asks to move the branch pointer
- preserve generated asset manifests and warn if media files are external

## Dependency And Invalidation Rules

Rollback must understand dependencies.

Examples:

- changing the character bible invalidates related reference sheets and prompts
- changing environment bible invalidates environment boards and shot prompts
- changing script invalidates scene intents, shot bible, prompts, and validation reports
- changing project config may invalidate model routing, validators, and provider plans

The system should produce an invalidation report before rollback:

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

## Approval And Versioning

Only approved versions should feed expensive downstream work.

Rules:

- candidate artifacts can be reviewed but should not drive generation
- approved artifacts are locked until explicitly revised
- changing an approved artifact creates a new candidate version
- approval creates a checkpoint
- rejection keeps the old approved version active

## Generated Asset Versioning

Generated clips should not be casually overwritten.

Each generated asset should include:

- generation id
- shot id
- provider
- prompt version
- reference version
- config version
- input frame version
- output file path
- validation report

If a shot is regenerated, it becomes a new take:

```text
shot-S001-01/take-001.mp4
shot-S001-01/take-002.mp4
```

One take can be selected as active.

## Branching For Creative Alternatives

Some changes should branch instead of overwrite.

Examples:

- alternate ending
- alternate tone
- alternate style profile
- alternate reference design

Branch metadata:

```json
{
  "branch_id": "branch:alternate-ending",
  "project_id": "film_2026_0001",
  "base_checkpoint": "checkpoint:script-approved:v1",
  "purpose": "Explore a quieter ending.",
  "active": false
}
```

Branches can later be:

- merged
- abandoned
- promoted to main

Git maps naturally to this, but the pipeline should still record the branch purpose,
base checkpoint, and affected artifacts.

## MCP Tools

Versioning tools:

- `list_checkpoints`
- `create_checkpoint`
- `get_checkpoint`
- `compare_versions`
- `list_artifact_versions`
- `rollback_artifact`
- `rollback_to_checkpoint`
- `create_revision_branch`
- `promote_branch`
- `get_invalidation_report`

Rollback tools should require confirmation when they affect approved artifacts or generated
assets.

Git-backed implementations can use:

- `git status`
- `git diff`
- `git commit`
- `git tag`
- `git branch`
- `git restore` for specific artifacts
- `git switch` for creative branches

The user should not need to run these manually for normal pipeline actions.

## Human Review

Before rollback, show:

- target checkpoint or version
- what will change
- what will be invalidated
- what will remain
- whether generated assets are affected
- recommended next validation steps

The user should be able to say:

- "rollback script to v3"
- "go back to the last approved reference checkpoint"
- "compare the current treatment with the previous one"
- "create a branch before trying this darker version"
- "restore the project to before generation"

## Storage Shape

Suggested structure:

```text
versions/
  artifacts/
  checkpoints/
  branches/
  diffs/
state/
  graph/
  budget/
  approvals/
generated-assets/
  shots/
    S001-01/
      take-001.mp4
      take-002.mp4
```

With git backend:

```text
.git/
versions/
  checkpoints/
  branches/
  diffs/
```

Large generated assets can live outside git or in git LFS, while manifests and metadata stay
in normal git history.

## Design Rule

The system should make experimentation feel safe. Users should be able to explore creative
directions without fear that a bad change permanently damages the project.

Git gives us the mechanical safety. The pipeline gives us the film-aware meaning.
