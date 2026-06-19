# Clip Generation Execution

## Purpose

Video generation is expensive and slow. The pipeline must avoid duplicate submissions,
poll patiently, resume safely, and use low-cost testing before production generation.

The core rule:

> Submit once, track the job, poll until terminal state, and never re-submit unless a human
> or explicit recovery policy approves it.

## Generation Modes

### 0. Mock Mode

Purpose:
Test the complete studio pipeline without spending money or waiting on real providers.

Mock mode should use the same provider adapter contract, generation ledger, polling protocol,
asset ingestion, validation, and resume logic as real generation.

Defaults:

- zero cost
- deterministic outputs
- fast completion unless scenario says otherwise
- real placeholder files
- configurable success and failure scenarios
- human approval gates still active

Example:

```yaml
generation_mode: mock
provider: mock-video-provider
model: mock-fast
duration_seconds: 2
resolution: 480p
quality: placeholder
audio: synthetic
scenario: happy_path_sequential_chain
```

Use mock mode for:

- MCP tool testing
- graph transition testing
- end-to-end project rehearsal
- idempotency and resume testing
- last-frame chaining tests
- provider failure simulations
- validation pipeline tests
- assembly and delivery dry runs

Mock mode is not a separate orchestration path. It is a normal provider implementation with
zero-cost behavior.

### 1. Test Mode

Purpose:
Validate prompt, reference, framing, and provider compatibility cheaply.

Defaults:

- low quality
- shortest supported duration
- lower resolution
- watermark acceptable if provider requires it
- no expensive multi-angle coverage unless specifically testing coverage

Example:

```yaml
generation_mode: test
duration_seconds: 1
resolution: 480p
quality: low
audio: false
human_approval_required_before_full_generation: true
```

Use test mode for:

- new style profiles
- new providers
- first shot of a scene
- reference strategy validation
- high-risk prompts
- expensive hero moments

### 2. Preview Mode

Purpose:
Produce a reviewable but not final-quality clip.

Defaults:

- moderate duration
- medium resolution
- cheaper provider when possible
- faster model when available

Use preview mode for:

- scene review
- camera testing
- rough edit assembly

### 3. Production Mode

Purpose:
Generate final candidate clips.

Defaults:

- approved duration
- approved provider
- approved references
- approved prompt version
- full validation after completion

Production mode requires:

- approved shot or coverage group
- approved references
- approved prompt package
- approved generation plan
- budget check

## Mock Provider Scenarios

The mock provider should support named scenarios so the same workflow can be tested
repeatedly.

Required scenarios:

- `happy_path_sequential_chain`
- `slow_poll_then_complete`
- `timeout_then_resume`
- `submit_error_before_job_id`
- `network_error_after_job_id`
- `download_failure_then_success`
- `frame_extraction_failure`
- `quota_exhausted`
- `auth_failure`
- `provider_outage`
- `moderation_block`
- `corrupt_asset`
- `validator_failure_after_generation`

Each scenario should declare expected behavior and expected orchestrator decision.

Example:

```yaml
scenario: network_error_after_job_id
expected:
  duplicate_submit_allowed: false
  next_action: resume_polling
  failure_agent_decision: resume_polling
  terminal_status: completed
```

Mock provider tests should verify:

- ledger row is written before submit
- provider job id is persisted immediately
- polling resumes from job id
- duplicate generation is blocked
- last frame is extracted or simulated
- next clip receives correct `input_frame_ref`
- provider account blocks pause affected queues
- unrelated work can continue when safe
- human review gates are still enforced

## Idempotent Submission

Every generation request should have a deterministic `generation_request_id`.

Suggested key:

```text
hash(project_id + shot_id + prompt_version + reference_versions + provider + model + mode)
```

Before submitting:

1. Check generation ledger for existing request id.
2. If status is `submitted` or `running`, resume polling.
3. If status is `completed`, reuse result.
4. If status is `failed`, follow recovery policy.
5. Only submit if no existing active request exists.

This prevents accidental double billing.

## Generation Ledger

Every request is recorded before the provider call.

```json
{
  "generation_request_id": "genreq:abc123",
  "generation_id": "gen:S001-01:test:v1",
  "project_id": "film_2026_0001",
  "shot_id": "S001-01",
  "coverage_group_id": null,
  "mode": "test",
  "provider": "seedance-openrouter",
  "model": "bytedance/seedance-2.0",
  "prompt_ref": "prompt:S001-01:v1",
  "reference_refs": ["ref:char:leo:identity:v1", "ref:env:studio:board:v1"],
  "status": "prepared",
  "provider_job_id": null,
  "submitted_at": null,
  "last_polled_at": null,
  "poll_count": 0,
  "estimated_cost": 0.18,
  "actual_cost": null,
  "output_refs": [],
  "error": null,
  "resume_token": "resume:S001-01:test:v1",
  "blocking_reason": null,
  "next_action": "poll"
}
```

Status values:

- `prepared`
- `submitted`
- `running`
- `completed`
- `failed`
- `cancelled`
- `timed_out`
- `requires_human_review`
- `blocked_provider`
- `blocked_budget`

## Durable Progress And Resume

Generation must be resumable after process crashes, provider delays, network failures, or
human pauses.

Persist progress after every important transition:

- before submit
- immediately after provider job id is received
- after every poll
- after download starts
- after download completes
- after frame extraction
- after validation
- after human decision
- after selected take changes

The orchestrator should never rely only on in-memory state. The generation ledger, graph
state, matrix row, issue log, budget ledger, and asset manifest should be updated
incrementally.

Resume behavior:

1. load active graph state
2. find ledger rows with non-terminal status
3. reacquire per-shot lock
4. continue from `provider_job_id` when present
5. continue from downloaded asset when present
6. continue from extracted frames when present
7. never submit a duplicate request unless recovery policy explicitly allows it

Suggested resume record:

```json
{
  "resume_token": "resume:S001-01:production:v2",
  "last_safe_step": "provider_job_id_recorded",
  "next_action": "poll_provider",
  "can_continue_automatically": true,
  "requires_human_review": false,
  "requires_provider_fix": false
}
```

## Submit Protocol

Before submit:

- validate prompt readiness
- validate references are approved
- validate budget
- check provider availability
- check no active request exists
- write ledger entry as `prepared`
- create checkpoint

Submit:

- call provider once
- record provider job id immediately
- update status to `submitted`
- persist ledger

If process dies after submission but before completion:

- resume from provider job id
- do not submit again

## Polling Protocol

Poll with patience.

Each provider should define:

- `initial_delay_seconds`
- `poll_interval_seconds`
- `max_wait_seconds`
- `terminal_statuses`
- `recoverable_statuses`

Example:

```yaml
polling:
  initial_delay_seconds: 20
  poll_interval_seconds: 30
  max_wait_seconds: 1800
  backoff_multiplier: 1.2
```

Rules:

- do not poll immediately in a tight loop
- do not re-submit while waiting
- persist after every poll result
- if max wait is reached, mark `timed_out` and require recovery decision
- if provider exposes status URL, store it
- if provider says still running, keep waiting until timeout

## Recovery Policy

Errors should be classified before any action is taken. The failure-handling agent should
decide whether the pipeline can continue, retry, skip, re-anchor, ask the human, or stop.

### Error Classes

Recoverable execution errors:

- temporary network failure
- polling timeout while provider still has a job id
- download failure
- frame extraction failure
- validator service unavailable
- one failed alternate take when other approved takes exist

Creative or validation errors:

- character drift
- environment drift
- unusable last frame
- prompt mismatch
- camera mismatch
- continuity mismatch

Blocking provider/account errors:

- no credit
- quota exhausted
- account suspended
- invalid API key
- provider-wide outage
- model removed or unavailable
- payment required
- repeated moderation block for approved project material

Blocking provider/account errors should stop the affected queue immediately. The system
should save all progress, mark the project as blocked, explain the reason, and wait until the
problem is solved. It should not keep retrying and should not switch to a different provider
unless the user or configured policy approves the fallback.

### Failure-Handling Agent

The failure-handling agent is responsible for turning raw errors into safe production
decisions.

Inputs:

- generation ledger row
- provider error payload
- provider registry failure modes
- budget ledger
- retry history
- matrix row
- validation reports
- active profile policy

Outputs:

```json
{
  "decision": "stop_until_resolved",
  "error_class": "provider_account",
  "severity": "blocking",
  "safe_to_retry": false,
  "safe_to_continue_other_work": true,
  "recommended_action": "Add provider credits, then resume from provider health check.",
  "human_message": "Generation is paused because the provider reports no remaining credit.",
  "next_graph_node": "provider_blocked_wait"
}
```

Decision options:

- `retry_later`
- `resume_polling`
- `retry_download`
- `use_previous_usable_frame`
- `re_anchor_next_clip`
- `request_human_review`
- `switch_provider_with_approval`
- `continue_unrelated_work`
- `stop_until_resolved`

### Continue What Is Safe

The pipeline should stop only the work that is unsafe to continue.

If one provider is out of credit:

- stop generation jobs using that provider
- continue writing, planning, validation, prompt preparation, and asset organization
- continue unrelated providers only if profile policy allows it
- keep completed clips and approved takes intact
- keep the current chain position saved

If a clip fails validation:

- stop the dependent chain
- continue independent scenes, references, or low-cost diagnostics
- create a drift or continuity issue
- recommend re-anchor, revision, or human review

If the orchestrator crashes:

- reload graph state
- inspect non-terminal ledger rows
- resume without duplicate submit
- ask the failure-handling agent to classify ambiguous rows

### Timeout

If timeout occurs:

1. try one final provider status check
2. if provider still reports running, mark `requires_human_review`
3. do not resubmit automatically

### Provider Error Before Job ID

If no job id was created:

- mark `failed`
- no billing likely occurred
- fallback can be considered after cost gate

### Provider Error After Job ID

If job id exists:

- poll provider status if possible
- do not assume failure means no output
- avoid resubmit until status is terminal

### Download Failure

Download failure is not generation failure.

Rules:

- retry download
- do not regenerate
- keep provider output URL
- mark asset ingestion issue if download keeps failing

### Provider Account Block

Provider account failures are blocking, not normal retries.

Rules:

- mark active jobs for that provider as `blocked_provider`
- write `blocking_reason`
- create a provider health issue
- pause dependent generation queues
- avoid retry loops
- surface a clear human-facing message
- resume only after provider health check passes or user approves a different provider

Example:

```json
{
  "provider": "seedance-openrouter",
  "status": "blocked_provider",
  "blocking_reason": "quota_exhausted",
  "can_resume_after": "provider_health_ok",
  "affected_generation_ids": ["gen:S001-01:production:v1"],
  "safe_continuation": ["screenwriting", "prompt_preparation", "validation_review"]
}
```

## No Duplicate Request Rule

The orchestrator must prevent duplicate generation requests.

Duplicate risk cases:

- user retries command while job is running
- process crashes after submit
- network times out but provider accepted job
- multiple agents try to generate same shot
- coverage group partially completed

Prevention:

- idempotency key
- generation ledger lock
- provider job id persistence
- per-shot active request check
- checkpoint before and after submit

## Test-To-Production Promotion

A shot should move through:

```text
test -> review -> production
```

Test passes when:

- prompt is understood
- framing is plausible
- reference works
- no obvious provider issue
- environment and character are recognizable

Test does not need:

- perfect motion
- final resolution
- final duration
- final audio

Production should start only after:

- test result approved or intentionally skipped
- production cost approved
- prompt/reference versions locked

## Generation Order

The default generation order should be sequential, one clip at a time.

Default rule:

```text
Generate clip N -> extract last frame -> pass last frame to clip N+1
```

This gives the video model a concrete visual continuation signal and is the safest path for
character, environment, lighting, wardrobe, and prop continuity.

### Sequential Chain

For a normal scene:

```text
S001-01 -> S001-02 -> S001-03 -> S001-04
```

Each completed clip produces:

- video asset
- last-frame image
- optional mid-frame image
- validation report
- continuity state update

The next clip receives:

- approved references
- continuity ledger state
- previous last frame
- same environment fingerprint
- same character anchors

### Scene Boundary Rule

At scene boundaries, the orchestrator decides whether to continue the chain or re-anchor.

Continue chain when:

- same location
- same time
- same character state
- same action flow
- direct continuation

Re-anchor when:

- new location
- large time jump
- major lighting change
- wardrobe change
- act boundary
- previous clip failed validation
- identity or environment drift is detected

### Re-Anchor Strategy

A re-anchor resets the chain using stronger references.

Possible anchors:

- character identity sheet
- environment board
- selected best previous frame
- master wide frame
- approved scene reference

Use re-anchor:

- every configured number of clips
- after drift warnings
- after scene boundary
- before hero shots
- after provider switch

Example:

```yaml
re_anchor:
  every_n_clips: 5
  use:
    - character_identity_sheet
    - environment_board
    - best_previous_frame
```

### Non-Linear Chaining

Sometimes the immediate previous last frame is not the best anchor.

Use non-linear chaining when:

- previous last frame has motion blur
- previous clip has identity drift
- a mid-frame is cleaner than last frame
- returning to a prior composition
- coverage group needs a master frame anchor

Example:

```text
S001-01 end -> S001-02
S001-01 mid -> S001-03
S001-02 end -> S001-04
S001-03 mid -> S001-05
```

The generation plan should explicitly record the selected frame anchor.

### Coverage Group Order

For multi-angle coverage, the default order is:

1. generate master/context angle
2. validate master/context angle
3. extract strong frame anchors
4. generate close/reaction/insert angles
5. validate cross-angle consistency

Coverage group clips share the same story event state. They should not advance story state
independently unless the edit plan uses them sequentially.

### When Parallel Generation Is Allowed

Parallel generation can be allowed only when clips are independent.

Allowed:

- different scenes with no continuity dependency
- environment tests
- reference tests
- alternate takes of the same static concept after approval
- isolated inserts that do not depend on previous motion

Not allowed by default:

- direct action continuation
- same character/emotion flow
- same room continuity chain
- last-frame-dependent shots
- long narrative sequence

If parallel generation is used, the generation plan must declare why it is safe.

### Matrix Fields For Order

The master film matrix should include:

```json
{
  "generation_order": 12,
  "depends_on_shot_id": "S001-11",
  "input_frame_ref": "asset:S001-11:last-frame",
  "input_frame_type": "last_frame",
  "chain_group_id": "chain:S001",
  "re_anchor": false,
  "re_anchor_refs": []
}
```

### Last Frame Extraction

After each completed clip:

- download output
- verify file integrity
- extract last frame
- optionally extract middle frame
- store frame assets
- validate frame usability
- update generation ledger
- update continuity ledger

If last-frame extraction fails:

- do not regenerate the clip
- log extraction failure
- use approved reference sheets or previous usable frame
- mark next shot as `chain_degraded`

### Chain Validation

After each clip, validate:

- last frame is usable
- character identity did not drift
- environment did not reset
- lighting direction is stable
- state_out matches next state_in

If validation fails:

- do not blindly continue
- create drift issue
- recommend re-anchor
- require human review if severe

### Generation Order Policy By Profile

```yaml
generation_order:
  default: sequential
  allow_parallel_independent_tests: true
  require_last_frame_chaining: true
  re_anchor_every_n_clips: 5
  re_anchor_on_scene_boundary: true
  re_anchor_on_drift_warning: true
```

## Cost Controls

Generation plan should include:

- mode
- provider
- estimated cost
- budget remaining
- whether approval is required

Require human approval when:

- switching to more expensive provider
- generating production mode for many clips
- regenerating completed production clips
- generating multi-angle coverage above threshold
- budget delta exceeds configured limit

## Quality Defaults By Mode

```yaml
generation_modes:
  test:
    duration_seconds: 1
    resolution: 480p
    quality: low
    audio: false
    validators:
      - prompt_adherence
      - rough_identity
      - rough_environment
  preview:
    duration_seconds: 3
    resolution: 720p
    quality: medium
    audio: false
    validators:
      - prompt_adherence
      - identity
      - environment
      - motion
  production:
    duration_seconds: from_matrix
    resolution: from_profile
    quality: high
    audio: from_profile
    validators:
      - clip_quality
      - identity
      - environment
      - continuity
      - artifact_detection
```

## Human Review

Before production generation, show:

- shot id
- prompt version
- reference versions
- provider
- mode
- estimated cost
- test result
- risks

During generation, user can ask:

- "what is running?"
- "show generation status"
- "resume polling"
- "cancel if provider supports it"

After generation, show:

- output clip
- validation report
- cost
- whether it is selected, rejected, or needs review

## MCP Tools

Suggested tools:

- `prepare_generation_request`
- `submit_generation_request`
- `get_generation_status`
- `resume_generation_polling`
- `list_active_generations`
- `cancel_generation_request`
- `download_generation_output`
- `promote_test_to_production`
- `approve_generation_cost`

## Design Rule

The system should be patient and boring around expensive API calls. Most cost disasters come
from uncertainty, impatience, or duplicate submission.
