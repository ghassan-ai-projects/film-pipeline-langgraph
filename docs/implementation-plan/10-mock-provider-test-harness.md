# Phase 10 — Mock Provider & Test Harness

**Depends on:** Phase 05 (LangGraph Skeleton), Phase 07 (Agent Registry), Phase 09 (Validation Registry)
**Blocks:** Phase 11 (Checkpoint/Resume), Phase 12 (E2E Mock Mini-Film)

---

## Goal

Implement the mock video provider and the test harness (mock human actor). The mock provider implements the same adapter contract as real providers, produces real placeholder files (MP4, PNG, JSON), and supports scenario scripts for failure testing. The mock human actor responds to review packages through the same MCP tools as a real user.

This is the foundation for zero-cost end-to-end testing of the entire pipeline.

---

## Deliverables

### Files to Create

#### Mock Provider (`src/film_pipeline/providers/`)

- [ ] `base.py` — `BaseProviderAdapter` abstract class: build_payload, submit, poll, download, extract_metadata, estimate_cost, cancel
- [ ] `contract.py` — `ProviderAdapterContract` (from Phase 01 schema)
- [ ] `registry.py` — `ProviderRegistry` class: register, lookup by id, lookup by type
- [ ] `health.py` — `ProviderHealthTracker` (tracks provider status, quota, credit, outages)
- [ ] `mock_provider.py` — `MockVideoProvider`:
  - [ ] Implements full adapter contract
  - [   ] Generates real placeholder MP4 (shot id + frame number burned in)
  - [ ] Generates last-frame PNG
  - [   ] Generates mid-frame PNG
  - [ ] Generates provider metadata JSON
  - [   ] Generates synthetic audio (optional)
  - [ ] Supports scenario scripts (happy path, timeout, quota, auth, moderation, download failure, corrupt asset)
  - [ ] Zero cost
- [ ] `mock_image_provider.py` — `MockImageProvider` for reference image generation
- [ ] `__init__.py`

#### Mock Human (`src/film_pipeline/testing/`)

- [ ] `mock_human.py` — `MockHumanActor`:
  - [   ] Responds to review packages through MCP tools
  - [ ] Decision profiles: `approve_all`, `revise_script_once`, `reject_bad_reference`, `approve_spend_under_limit`, `stop_on_provider_block`, `confirm_rollback`, `reject_final_cut`
  - [ ] Deterministic, scenario-driven
  - [ ] Approval records include `actor_type: mock_human`
  - [   ] Production mode rejects mock human approvals
- [ ] `mock_model.py` — `MockModelAdapter`:
  - [ ] Returns canned JSON for agent prompts
  - [   ] Returns canned validation reports
  - [ ] Configurable per agent/validator
- [ ] `fixtures.py` — test fixtures (seed idea, project config, expected artifacts)
- [ ] `scenarios.py` — mock provider scenario definitions (13 scenarios from clip-generation-execution.md)
- [ ] `__init__.py`

#### Tests

- [ ] `tests/unit/providers/test_mock_provider.py` — submit, poll, download, extract frames
- [ ] `tests/unit/providers/test_provider_registry.py` — register, lookup
- [ ] `tests/unit/providers/test_health_tracker.py` — status tracking, block detection
- [ ] `tests/unit/testing/test_mock_human.py` — decision profiles
- [   ] `tests/unit/testing/test_mock_model.py` — canned responses

---

## Task Checklist

- [ ] Implement `BaseProviderAdapter` abstract class with all methods:
  - [ ] `build_payload(prompt_package, references, config)` — construct provider-specific payload
  - [ ] `submit(payload)` — submit to provider, return job_id
  - [ ] `poll(job_id)` — check job status
  - [ ] `download(job_id)` — download output asset
  - [ ] `extract_metadata(asset)` — extract duration, resolution, etc.
  - [   ] `estimate_cost(duration, model)` — calculate cost
  - [ ] `cancel(job_id)` — cancel if supported
- [ ] Implement `ProviderRegistry` with register, lookup_by_id, lookup_by_type
- [ ] Implement `ProviderHealthTracker`:
  - [ ] Track status: healthy, degraded, blocked_quota, blocked_credit, blocked_auth, blocked_outage, disabled_by_user
  - [ ] Record last_health_check, last_successful_job, quota_state, credit_state
  - [   ] Block detection and unblocking
- [ ] Implement `MockVideoProvider`:
  - [ ] Generate placeholder MP4 with ffmpeg (shot id + frame number overlay)
  - [   ] Generate last-frame PNG
  - [ ] Generate mid-frame PNG
  - [   ] Generate provider metadata JSON
  - [ ] Support all 13 scenarios from clip-generation-execution.md:
    - [ ] `happy_path_sequential_chain`
    - [ ] `slow_poll_then_complete`
    - [ ] `timeout_then_resume`
    - [ ] `submit_error_before_job_id`
    - [ ] `network_error_after_job_id`
    - [ ] `download_failure_then_success`
    - [   ] `frame_extraction_failure`
    - [ ] `quota_exhausted`
    - [ ] `auth_failure`
    - [ ] `provider_outage`
    - [ ] `moderation_block`
    - [ ] `corrupt_asset`
    - [ ] `validator_failure_after_generation`
- [ ] Implement `MockImageProvider` for reference images (placeholder PNGs)
- [ ] Implement `MockHumanActor`:
  - [   ] All 7 decision profiles
  - [ ] Acts through MCP tools only (never bypasses approval contracts)
  - [ ] Deterministic decisions per profile
  - [ ] Records `actor_type: mock_human` on approvals
- [ ] Implement `MockModelAdapter`:
  - [   ] Returns canned JSON per agent_id
  - [ ] Returns canned validation reports per validator_id
  - [   ] Configurable response templates
- [ ] Implement test fixtures and scenario definitions
- [   ] Write unit tests for mock provider, registry, health tracker
- [ ] Write unit tests for mock human and mock model
- [ ] Run `make ci-check`

---

## Mock Provider Scenario Example

```yaml
scenario: quota_block_after_two_jobs
provider: mock-video-provider
behavior:
  - shot_id: S001-01
    submit: success
    polls_before_complete: 2
    output: placeholder_video
    last_frame: generated
  - shot_id: S001-02
    submit: success
    polls_before_complete: 1
    output: placeholder_video
    last_frame: generated
  - shot_id: S001-03
    submit: error
    error_code: quota_exhausted
    expected_decision: stop_until_resolved
```

---

## Acceptance Criteria

- [ ] Mock provider implements the full adapter contract
- [   ] Mock provider generates real placeholder files (MP4, PNG, JSON)
- [ ] All 13 scenarios produce expected behavior
- [ ] Provider health tracker correctly detects and reports blocks
- [ ] Mock human acts through MCP tools only
- [   ] Mock human decision profiles are deterministic
- [ ] Mock model returns correctly-typed JSON for every agent and validator
- [   ] Mock provider cost is always $0.00
- [ ] All tests pass
- [ ] `make ci-check` passes

---

## Risks

| Risk | Mitigation |
|------|------------|
| ffmpeg not available in CI | Install ffmpeg in CI workflow; or generate minimal valid MP4 without ffmpeg |
| Mock provider diverges from real contract | Abstract behind `BaseProviderAdapter`; real providers implement same interface |
| Mock human bypasses gates | Enforce: mock human can only call MCP tools; never mutate state directly |
