# E2E Test Scenarios

## Purpose

These scenarios define the first end-to-end acceptance tests for the studio. They should run
through MCP, use LangGraph state, persist artifacts, enforce human gates, use the KB context
builder, and use the mock provider for zero-cost generation.

The scenarios are written as product-level journeys first. Later they can become automated
tests.

## Mock Human Test Actor

E2E tests should use a mock human actor so human-in-the-loop behavior can be tested
repeatably.

The mock human is not a production bypass. It is a test actor that responds to review
packages through the same MCP tools a real OpenClaw user would use.

It should support scripted decision profiles:

- `approve_all`: approves every valid review package
- `revise_script_once`: requests one script revision, then approves the revision
- `reject_bad_reference`: rejects reference packages with blocking validation issues
- `approve_spend_under_limit`: approves generation spend below a configured amount
- `stop_on_provider_block`: does not approve fallback until provider block is resolved
- `choose_project_on_ambiguity`: selects a configured project when lookup is ambiguous
- `confirm_rollback`: confirms rollback after inspecting invalidation report
- `reject_final_cut`: rejects final cut when QC has blocking issues

Mock human decisions should create normal approval, rejection, or revision records.

Example:

```yaml
mock_human:
  profile: revise_script_once
  decisions:
    config_review: approve
    constitution_review: approve
    treatment_review: approve
    script_review:
      action: request_revision
      note: Make dialogue less explanatory and more visual.
    script_review_after_revision: approve
    visual_bible_review: approve
    shot_bible_review: approve
    generation_spend_review:
      action: approve
      max_cost_usd: 0
```

Required checks:

- mock human can only act through MCP tools
- mock human cannot approve if tool contract says confirmation is missing
- approval records must show `actor_type: mock_human`
- test mode must clearly distinguish mock approval from real user approval
- production mode must not accept mock human approvals
- mock human decisions must be deterministic
- review packages must contain enough information for the mock human policy to decide

## Shared Test Setup

Test project:

```yaml
project_slug: memory-in-rain
title: Memory In Rain
film_type: narrative_short
target_runtime: 30s
style_profile: intimate_cinematic_realism
generation_mode: mock
provider: mock-video-provider
model: mock-fast
human_gates: required
human_actor: mock_human
mock_human_profile: approve_all
```

Seed idea:

```text
A lonely watchmaker hears the rain stop for the first time in years and realizes the city
outside has been frozen in a single moment.
```

Minimum test film:

- 1 act
- 2 scenes
- 4 shots
- 1 main character
- 1 recurring environment
- sequential clip generation
- last-frame chaining enabled
- one review cut

Shared required checks:

- all state changes happen through MCP tools
- every artifact has metadata
- every generated artifact has `kb_context_ref`
- every phase gate creates review package
- approvals are persisted
- mock human approvals are marked as test approvals
- checkpoints are created after approvals
- mock generation writes ledger rows
- no duplicate provider submissions occur
- audit log can explain final state

## Scenario 1. Happy Path: Mini Film From Idea To Review Cut

### Goal

Prove the complete studio spine works with no provider cost.

### Mock Provider Behavior

```yaml
scenario: happy_path_sequential_chain
shots:
  S001-01: success_after_1_poll
  S001-02: success_after_1_poll
  S002-01: success_after_1_poll
  S002-02: success_after_1_poll
```

### Flow

1. `create_film_project`
2. `submit_idea`
3. `review_phase` for inferred project config
4. `approve_phase` for project config
5. orchestrator creates film constitution
6. `review_phase` for constitution
7. `approve_phase` for constitution
8. orchestrator creates treatment and scene intents
9. `review_phase` for treatment
10. `approve_phase` for treatment
11. orchestrator creates script
12. `review_phase` for script
13. `approve_phase` for script
14. orchestrator creates character and environment bibles
15. orchestrator creates reference strategy
16. `review_phase` for visual bible and references
17. `approve_phase` for visual bible and references
18. orchestrator creates shot bible and continuity ledger
19. `review_phase` for shot bible
20. `approve_phase` for shot bible
21. `plan_generation_batch`
22. `approve_generation_spend`
23. `start_generation_batch`
24. mock provider generates clips sequentially
25. last frame from shot N feeds shot N+1
26. validators run at clip and scene level
27. `assemble_review_cut`
28. `review_phase` for review cut
29. `approve_phase` for review cut
30. `export_project_lessons`

### Expected Artifacts

- project config
- film constitution
- treatment
- scene intent sheets
- script
- character bible
- environment bible
- reference strategy
- reference index
- shot bible
- master film matrix
- continuity ledger
- prompt registry
- generation plan
- generation ledger
- generated mock clips
- last-frame assets
- clip QC reports
- scene QC reports
- assembly manifest
- review cut
- audit log
- checkpoints

### Pass Criteria

- project reaches `review_cut_approved`
- every phase has an approval record
- every generated shot maps to one matrix row
- every generated shot has one and only one provider job id
- each shot after the first has `input_frame_ref`
- continuity ledger has state in/out for every shot
- validation reports pass or pass with notes
- final review package lists no blocking issues
- audit log can explain selected agents, KB context, and provider actions

### What This Proves

- MCP-first control path works
- graph can move through all major phases
- human gates work
- artifacts and ledgers are connected
- mock provider can exercise generation without cost
- last-frame chaining works
- review package pattern is usable

## Scenario 2. Non-Happy Path: User Requests Revision At Script Gate

### Goal

Prove human-in-the-loop revision works before downstream artifacts become expensive.

### Trigger

At script review, the user says:

```text
The dialogue feels too explanatory. Make it more restrained and visual.
```

### Flow

1. run happy path until script review
2. `request_revision` with user note
3. orchestrator creates revision issue
4. dialogue and subtext agents revise only affected scenes
5. validators re-check dialogue, character voice, and theme
6. orchestrator creates diff review package
7. user approves revised script
8. checkpoint is created
9. pipeline continues to visual development

### Expected Behavior

- old script version remains available
- revised script gets new version
- revision issue links old and new versions
- downstream visual artifacts are not created until script approval
- review package includes diff and validation deltas

### Pass Criteria

- no shot bible exists before revised script approval
- approval points to revised script version
- audit log explains revision reason
- invalidation engine reports no generated media affected

### What This Proves

- human feedback can steer the creative process
- revision requests are structured
- phase gates prevent premature downstream work
- versioning is understandable

## Scenario 3. Non-Happy Path: Reference Image Fails Usability

### Goal

Prove the system catches bad references before they poison video generation.

### Trigger

Mock reference validator returns:

```yaml
status: block
blocking_issue: character_identity_inconsistent
affected_ref: ref:char:watchmaker:identity-sheet:v1
```

### Flow

1. run until visual bible/reference review
2. reference validator blocks character identity sheet
3. orchestrator creates reference issue
4. reference agent regenerates or revises only failed sheet
5. validator re-checks identity, usability, and provider constraints
6. orchestrator creates updated reference review package
7. user approves fixed references
8. pipeline continues to shot bible

### Expected Behavior

- shot bible generation pauses
- failed reference is not approved
- new reference version supersedes failed version
- reference index marks only approved assets as usable
- KB context includes bad-reference lessons

### Pass Criteria

- no prompt package uses the rejected reference
- reference index contains approval status
- validation report links to both failed and fixed versions
- orchestrator recommendation explains why generation should not proceed

### What This Proves

- visual validation blocks unsafe assets
- references are versioned
- downstream prompts use only approved references
- KB lessons influence validation context

## Scenario 4. Non-Happy Path: Provider Quota Exhausted During Generation

### Goal

Prove provider/account failures stop safely without wasting money or losing progress.

### Mock Provider Behavior

```yaml
scenario: quota_block_after_two_jobs
shots:
  S001-01: success_after_1_poll
  S001-02: success_after_1_poll
  S002-01:
    submit_error: quota_exhausted
```

### Flow

1. run happy path until generation starts
2. first two shots complete
3. third shot submit returns quota exhausted
4. failure-handling agent classifies `provider_account`
5. affected generation queue pauses
6. progress is saved
7. unrelated safe work continues if available
8. `get_generation_status` shows provider block
9. user resolves provider block using `resolve_provider_block`
10. provider health check passes
11. `resume_generation`
12. generation continues from shot S002-01 without resubmitting completed shots

### Expected Behavior

- completed shots remain active
- third shot is not repeatedly retried
- provider health status becomes `blocked_quota`
- generation ledger records blocking reason
- resume token points to next safe action

### Pass Criteria

- no duplicate job ids for S001-01 or S001-02
- S002-01 has exactly one failed/prevented submission record
- failure decision says `stop_until_resolved`
- after resolution, generation resumes from S002-01
- audit log explains pause and resume

### What This Proves

- provider blocks are handled differently from creative failures
- progress is durable
- resume works
- duplicate generation protection works
- MCP can inspect and resolve operational blockers

## Scenario 5. Non-Happy Path: Network Error After Provider Job ID

### Goal

Prove ambiguous provider failures do not cause duplicate paid jobs.

### Mock Provider Behavior

```yaml
scenario: network_error_after_job_id
shot: S001-02
submit: accepted
provider_job_id: mock_job_002
client_error_after_accept: network_disconnect
poll_after_resume: completed
```

### Flow

1. run generation through S001-01
2. submit S001-02
3. provider accepts and creates job id
4. client receives network error after accept
5. ledger already contains provider job id
6. orchestrator restarts or resumes
7. failure-handling agent classifies ambiguity
8. system polls existing job id
9. output is downloaded and ingested
10. chain continues to next shot

### Expected Behavior

- no second submit occurs for S001-02
- polling resumes from `mock_job_002`
- downloaded clip becomes active take
- next shot receives S001-02 last frame

### Pass Criteria

- generation ledger has one request id
- provider job id is reused
- duplicate-submit guard records a prevented duplicate attempt if user retries
- audit log shows resume decision

### What This Proves

- idempotency works
- provider ambiguity is safe
- crash/restart recovery works
- money-protection policy works

## Scenario 6. Non-Happy Path: Clip Fails Continuity Validation

### Goal

Prove generated clips can fail validation without automatically triggering expensive
regeneration.

### Mock Provider Behavior

```yaml
scenario: continuity_drift_on_third_clip
shots:
  S001-01: success
  S001-02: success
  S002-01:
    success: true
    validation_override:
      environment_drift: severe
```

### Flow

1. run generation until S002-01 completes
2. clip validator flags severe environment drift
3. scene continuity validator blocks continuation
4. orchestrator creates issue
5. failure-handling agent does not classify as provider failure
6. orchestrator recommends re-anchor or human review
7. dependent chain pauses
8. user chooses re-anchor
9. re-anchor plan is created
10. prompt/reference package is revised
11. pipeline resumes from affected shot or creates new take if approved

### Expected Behavior

- no automatic regeneration
- affected chain pauses
- unrelated scenes may continue if safe
- issue is linked to clip, prompt, references, and environment bible
- human sees options: accept, re-anchor, revise prompt, regenerate with approval

### Pass Criteria

- validation report status is `blocked`
- generation ledger does not create a new paid/mock job without approval
- re-anchor plan references approved environment board
- audit log explains why continuation stopped

### What This Proves

- validation failures are not provider failures
- continuity gates protect downstream clips
- human controls expensive repair
- re-anchor flow is testable

## Scenario 7. Non-Happy Path: Rollback After Bad Style Change

### Goal

Prove git-backed checkpoints and invalidation reports work.

### Trigger

After approving visual bible, user asks:

```text
Make the film more neon cyberpunk.
```

The change is applied, but user dislikes it:

```text
Rollback to the last approved visual bible.
```

### Flow

1. run happy path until visual bible approval
2. create checkpoint
3. request style revision
4. style bible and references update
5. validators warn tone mismatch
6. user requests rollback
7. system creates invalidation report
8. user confirms rollback
9. artifacts restore to checkpoint
10. downstream stale artifacts are marked invalid

### Expected Behavior

- rollback does not silently rewrite history
- rollback creates new rollback record
- invalidation report lists affected references, prompts, and shot bible rows
- active version returns to approved visual bible

### Pass Criteria

- checkpoint is discoverable through MCP
- compare shows cyberpunk change versus approved version
- rollback requires confirmation
- current state uses restored artifacts
- audit log records rollback reason

### What This Proves

- versioning is film-aware
- users can safely experiment
- invalidation protects downstream consistency
- MCP rollback tools work

## Scenario 8. Non-Happy Path: KB Policy Conflict

### Goal

Prove the governed KB prevents old rules from overriding current policy.

### Trigger

During provider quota failure, retrieval finds:

- old skill: fallback automatically on insufficient quota
- current policy: stop provider queue until solved unless user approves fallback

### Flow

1. run quota exhaustion scenario
2. KB context builder finds conflicting rules
3. canonical policy wins over old case-study/archive item
4. orchestrator records excluded KB ref
5. failure-handling agent recommends stop-until-resolved
6. MCP `kb_explain_context_choice` explains decision

### Expected Behavior

- old rule is not injected as active policy
- conflict is visible
- current policy drives behavior
- user can inspect why

### Pass Criteria

- `kb_context_ref` includes current provider-block policy
- old fallback rule appears in `excluded_refs`
- no automatic provider switch occurs
- audit log links decision to KB context

### What This Proves

- KB authority levels work
- orchestrator context selection is explainable
- historical lessons do not accidentally become runtime policy

## Scenario 9. Non-Happy Path: Active Project Ambiguity

### Goal

Prove MCP project resolution protects against acting on the wrong film.

### Setup

Two projects exist:

- `memory-in-rain`
- `memory-in-snow`

User says:

```text
Approve the references for memory.
```

### Flow

1. MCP receives ambiguous request
2. project lookup returns multiple matches
3. orchestrator refuses mutation
4. user is asked to choose project
5. after selection, `set_active_project` is called
6. approval proceeds only for selected project

### Expected Behavior

- no approval occurs before project is resolved
- candidate projects are shown
- expensive/destructive action requires exact project resolution

### Pass Criteria

- no state mutation happens during ambiguity
- audit log records blocked ambiguous request
- selected project receives approval
- other project remains unchanged

### What This Proves

- MCP-first project identity is safe
- multi-project workflows are protected
- accidental approvals are prevented

## Scenario 10. Dynamic Flow: Block One Path, Continue Another

### Goal

Prove the orchestrator is state-driven, not a static phase runner.

### Trigger

During visual development:

- character reference validation fails
- environment bible validation passes
- camera language bible is ready for review

### Flow

1. run until visual development
2. character reference validator blocks main character identity sheet
3. orchestrator computes eligible actions
4. `create_shot_bible` is disabled because references are not approved
5. `repair_character_reference` is recommended
6. `review_environment_bible` remains available
7. mock human approves environment bible
8. character reference agent repairs failed sheet
9. validator passes repaired sheet
10. orchestrator recomputes eligible actions
11. `create_shot_bible` becomes available

### Expected Behavior

- system does not blindly proceed to shot bible
- system does not freeze the whole project unnecessarily
- eligible actions are visible through MCP
- blocked actions include reasons
- route decision is logged

### Pass Criteria

- `get_next_actions` shows at least one blocked action and one available action
- shot bible is not created until character references pass
- environment bible approval can complete while character reference repair is pending
- audit log includes routing decision explaining the dynamic branch

### What This Proves

- dynamic routing works
- dependencies are enforced
- independent safe work can continue
- phase map is a guardrail, not a static script

## Automation Priority

Automate in this order:

1. happy path mini film
2. network error after job id
3. provider quota exhausted
4. script revision gate
5. reference validation failure
6. clip continuity failure
7. rollback after bad style change
8. KB policy conflict
9. active project ambiguity
10. dynamic flow blocked path plus available path

## Acceptance Baseline

Before real providers are connected, these must pass:

- Scenario 1
- Scenario 4
- Scenario 5
- Scenario 6

Those four cover the core expensive-risk surface:

- full pipeline coherence
- provider account block
- duplicate generation prevention
- validation-driven stop and repair
