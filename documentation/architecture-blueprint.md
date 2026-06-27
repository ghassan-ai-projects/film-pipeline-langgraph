# Architecture Blueprint

## North Star

Build a LangGraph Film Studio:

- MCP is the primary operator surface
- OpenClaw controls the studio through MCP tools
- one orchestrator agent drives the flow
- many narrow expert agents handle small domains
- every phase produces typed artifacts
- every major phase pauses for human review
- every validation result is structured and stored
- the KB feeds task-specific context into the right agents

Design rule: do not treat MCP as a late wrapper around an internal app. The MCP contract is
the product boundary. LangGraph is the execution engine behind that boundary.

## System Layers

### 1. MCP Operator Surface

OpenClaw should control the studio through MCP tools.

MCP owns the external contract for:

- project creation
- project lookup and active project selection
- user idea submission
- phase review
- human approvals
- revision requests
- artifact inspection
- validation inspection
- generation planning
- generation pause/resume
- provider health checks
- checkpoint creation
- rollback requests
- final delivery export

Every major capability should be reachable through an MCP tool before it is exposed through
any other UI.

### 2. Orchestration Layer

LangGraph owns:

- graph state
- phase transitions
- interrupts
- resumability
- routing to specialist agents
- validation and approval gates
- version and checkpoint transitions
- execution behind MCP tool calls

The orchestrator should not assume a direct chat session. It should receive structured MCP
requests, resolve the project, run or resume the graph, and return structured artifacts,
review packages, or next required actions.

### 3. Agent Layer

Agents are small-domain specialists.

Creator agents produce artifacts. Reviewer agents critique artifacts. Validator agents score
artifacts against schemas and rubrics. The orchestrator coordinates them.

The detailed agent roster, relationships, handoff patterns, review loops, routing rules, and
MVP agent set are defined in
`agent-architecture.md` (retired during docs cleanup).

### 4. Knowledge Layer

The KB is accessed through curated retrieval:

- canonical rules
- operational references
- case studies
- raw archive

The orchestrator chooses the relevant KB slice for the current phase and agent.

The detailed KB organization, extension, retrieval, authority levels, context packets, and
MCP tools are defined in
`kb-operating-model.md` (retired during docs cleanup).

### 5. Artifact Layer

Every output becomes a versioned artifact with metadata.

Required metadata:

- `artifact_id`
- `artifact_type`
- `project_id`
- `phase`
- `version`
- `status`
- `parents`
- `created_by`
- `reviewed_by`
- `validation_refs`
- `approval_ref`
- `kb_context_ref`

### 6. Extension Layer

The system should be designed around registries so new capabilities can be added without
rewriting the graph.

Registry-backed extension points:

- agents
- validators
- providers
- model adapters
- artifact schemas
- prompt templates
- review strategies
- delivery modes

Each extension should declare:

- `id`
- `type`
- `version`
- `capabilities`
- `input_schema`
- `output_schema`
- `cost_profile`
- `failure_modes`
- `enabled`

## Core State Domains

The first implementation should model state around these domains:

- `project`
- `orchestrator`
- `kb_context`
- `film_constitution`
- `narrative`
- `characters`
- `environments`
- `camera_language`
- `scene_intents`
- `shot_bible`
- `reference_strategy`
- `generation_plan`
- `assets`
- `validation`
- `approvals`
- `issues`
- `budget`
- `provider_health`
- `runtime_errors`
- `timeline`
- `delivery`

## Core Film Data Structures

The movie should be organized around a small set of canonical data structures. These are
the backbone of the studio, and every agent should read from or write to them instead of
inventing its own local format.

### 1. Project Profile

Defines the production container.

Core fields:

- `project_id`
- `title`
- `slug`
- `film_type`
- `target_runtime`
- `aspect_ratio`
- `delivery_modes`
- `budget`
- `provider_preferences`
- `human_owner`

### 2. Film Constitution

Defines the creative law of the film.

Core fields:

- `theme`
- `tone`
- `emotional_promise`
- `visual_language`
- `camera_philosophy`
- `character_truths`
- `taboo_mistakes`
- `quality_bar`

### 3. Story Bible

Defines the narrative structure.

Core fields:

- `logline`
- `premise`
- `treatment`
- `act_map`
- `scene_list`
- `setup_payoff_map`
- `unresolved_threads`
- `theme_map`

### 4. Character Bible

Defines each character once.

Core fields:

- `character_id`
- `name`
- `role`
- `identity_block`
- `visual_identity`
- `voice_rules`
- `wardrobe_rules`
- `emotional_arc`
- `relationship_map`
- `reference_assets`
- `must_not_change`

### 5. Environment Bible

Defines each location once.

Detailed environment consistency rules are defined in
`environment-consistency.md` (retired during docs cleanup).

Core fields:

- `environment_id`
- `name`
- `locked_prompt_block`
- `layout`
- `props`
- `lighting_profiles`
- `color_palette`
- `time_of_day_rules`
- `weather_rules`
- `reference_assets`
- `must_not_change`

### 6. Camera Language Bible

Defines cinematic grammar.

Core fields:

- `profile_id`
- `use_case`
- `lens`
- `framing`
- `movement`
- `depth_of_field`
- `composition_rules`
- `transition_rules`
- `emotional_meaning`

### 7. Master Film Matrix

This is the central production table. It should connect story, character, environment,
camera, prompt, reference, validation, generation, and post-production data.

Each row represents one planned shot or clip.

Suggested fields:

```json
{
  "shot_id": "S001-01",
  "act_id": "A1",
  "sequence_id": "SEQ001",
  "scene_id": "S001",
  "beat_id": "B001",
  "story_function": "inciting image",
  "scene_intent_ref": "artifact:scene-intent:S001",
  "duration_seconds": 8,
  "priority": "hero",
  "risk_level": "medium",
  "characters": ["char:leo"],
  "environment": "env:studio",
  "camera_profile": "camera:modern_tense",
  "state_in_ref": "state:S001-01:in",
  "state_out_ref": "state:S001-01:out",
  "reference_strategy_ref": "ref-strategy:S001-01",
  "prompt_ref": "prompt:S001-01:v1",
  "provider_plan_ref": "provider-plan:S001-01",
  "generation_order": 1,
  "chaining": {
    "input_frame_ref": null,
    "return_last_frame": true,
    "re_anchor": false,
    "re_anchor_ref": null
  },
  "validation_refs": [],
  "asset_refs": [],
  "post_refs": [],
  "status": "planned"
}
```

This matrix should support:

- narrative films
- visual poetry
- experimental films
- linear chaining
- non-linear chaining
- re-anchor schedules
- alternative takes
- post-production assembly

### 8. Continuity Ledger

Tracks state changes across the matrix.

Core fields:

- `shot_id`
- `state_in`
- `action`
- `state_out`
- `character_state`
- `prop_state`
- `wardrobe_state`
- `environment_state`
- `lighting_state`
- `story_threads`
- `continuity_risks`
- `next_required_anchors`

### 9. Reference Index

Maps approved reference assets to their intended use.

Core fields:

- `reference_id`
- `asset_path`
- `asset_type`
- `subject_type`
- `subject_id`
- `approved_for`
- `quality_score`
- `moderation_risk`
- `notes`

### 10. Prompt Registry

Stores RCTCO prompt packages.

Core fields:

- `prompt_id`
- `agent_id`
- `shot_id`
- `artifact_refs`
- `r`
- `c1`
- `t`
- `c2`
- `o`
- `rendered_prompt`
- `validation_status`

### 11. Generation Ledger

Records provider execution.

Core fields:

- `generation_id`
- `shot_id`
- `provider`
- `model`
- `submitted_at`
- `completed_at`
- `cost_estimate`
- `actual_cost`
- `status`
- `output_asset_refs`
- `error_code`
- `checkpoint_ref`

### 12. Validation Ledger

Stores all validation results.

Core fields:

- `validation_id`
- `validator_id`
- `scope`
- `modality`
- `artifact_refs`
- `score`
- `status`
- `blocking_issues`
- `warnings`
- `recommended_actions`
- `requires_human_review`

### 13. Assembly Manifest

Defines how generated assets become a cut.

Core fields:

- `cut_id`
- `clip_order`
- `source_asset_refs`
- `transition_plan`
- `audio_plan`
- `color_plan`
- `duration_total`
- `missing_assets`
- `delivery_mode`

## Matrix Operating Rules

The master film matrix is not a spreadsheet afterthought. It is the shared contract between
agents.

Rules:

- every generated clip must map to one matrix row
- every matrix row must map to a scene intent
- every matrix row must reference character, environment, and camera bibles
- every matrix row must have continuity state before generation
- every matrix row must have validation records after generation
- post-production reads from the same matrix and assembly manifest
- changes to approved matrix rows create new versions

The orchestrator should treat the matrix as the production backbone.

## Extensibility Model

Flexibility should come from explicit contracts and registries, not from loose dynamic code.

### Provider Registry

Every video, image, audio, TTS, music, or post-production provider should implement a common
adapter contract.

Suggested provider contract:

```json
{
  "provider_id": "seedance-openrouter",
  "provider_type": "video",
  "models": ["bytedance/seedance-2.0"],
  "capabilities": {
    "text_to_video": true,
    "image_to_video": true,
    "return_last_frame": true,
    "max_duration_seconds": 15,
    "aspect_ratios": ["16:9", "9:16"],
    "supports_audio": false
  },
  "cost_profile": {
    "unit": "second",
    "estimated_rate": 0.18
  },
  "failure_modes": ["timeout", "quota", "moderation", "download_failure"]
}
```

Provider adapters should expose:

- `build_payload`
- `submit`
- `poll`
- `download`
- `extract_metadata`
- `estimate_cost`
- `cancel` when supported

Adding a provider should not require changing the orchestration graph. It should require
registering the adapter and its capabilities.

### Mock Provider

The project should include a first-class mock provider before any expensive provider
integration.

Purpose:

- test MCP tools end to end
- test LangGraph state transitions
- test generation ledger behavior
- test idempotent submit and resume
- test sequential last-frame chaining
- test validation gates
- test provider health handling
- test quota, auth, timeout, and download failures
- test post-production assembly with placeholder media

The mock provider should implement the same provider adapter contract as real providers.
It should not be a special path in the orchestrator.

Suggested mock provider contract:

```json
{
  "provider_id": "mock-video-provider",
  "provider_type": "video",
  "models": ["mock-fast", "mock-slow", "mock-failing"],
  "capabilities": {
    "text_to_video": true,
    "image_to_video": true,
    "return_last_frame": true,
    "max_duration_seconds": 30,
    "aspect_ratios": ["16:9", "9:16", "1:1"],
    "supports_audio": true,
    "supports_seed": true
  },
  "cost_profile": {
    "unit": "second",
    "estimated_rate": 0.0
  },
  "failure_modes": [
    "timeout",
    "quota",
    "auth",
    "moderation",
    "download_failure",
    "corrupt_asset"
  ]
}
```

The mock provider should support scenario scripts:

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

Mock outputs should be real files when possible:

- placeholder MP4 with shot id and frame number burned in
- last-frame PNG
- mid-frame PNG
- provider metadata JSON
- optional synthetic audio

This lets validators, ingestion, assembly, and post-production run against real file paths
without real provider cost.

### Mock Human

The test harness should also include a mock human actor.

Purpose:

- test mandatory human gates
- test phase approvals
- test revision requests
- test rejection paths
- test spend approvals
- test rollback confirmations
- test active-project ambiguity resolution
- run E2E tests without manual intervention

The mock human must act through the same MCP tools as a real user. It should never bypass
approval contracts or mutate state directly.

Rules:

- enabled only in test mode
- decisions are deterministic and scenario-driven
- approval records include `actor_type: mock_human`
- production mode rejects mock human approvals
- dangerous actions still require explicit scripted confirmation
- mock human decisions are included in the audit log

### Validator Registry

Validators should also be plugins.

Suggested validator contract:

```json
{
  "validator_id": "clip-character-consistency",
  "scope": "clip",
  "modalities": ["video", "image", "continuity"],
  "input_schema": "validator-input:clip-character-consistency:v1",
  "output_schema": "validation-report:v1",
  "models": ["gemini-flash", "gpt-5-mini"],
  "thresholds": {
    "pass": 85,
    "review": 75,
    "block": 60
  }
}
```

Adding a validator should require:

- registering the validator
- declaring scope and modality
- declaring required artifacts
- declaring output schema
- declaring thresholds
- defining revision behavior

### Agent Registry

Every specialist agent should be discoverable by capability.

Suggested agent contract:

```json
{
  "agent_id": "dialogue-agent",
  "domain": "writing",
  "capabilities": ["dialogue", "voice_consistency"],
  "allowed_kb_domains": ["story", "character", "tone"],
  "input_artifacts": ["script", "character_bible"],
  "output_artifacts": ["dialogue_revision"],
  "prompt_framework": "RCTCO"
}
```

The orchestrator should select agents by capability, not by hard-coded filenames.

### Failure-Handling Agent

The pipeline needs a dedicated failure-handling agent because expensive media generation
failures are not all the same. A timeout, a bad last frame, and a provider account with no
credit require different actions.

Responsibilities:

- classify provider, runtime, validation, budget, and continuity errors
- decide whether work can continue automatically
- decide whether only one chain should pause or the whole project should pause
- prevent duplicate submissions after ambiguous provider failures
- recommend retry, re-anchor, provider switch, human review, or stop-until-resolved
- write structured issues and human-readable explanations

Suggested agent contract:

```json
{
  "agent_id": "failure-handling-agent",
  "domain": "operations",
  "capabilities": [
    "error_classification",
    "provider_health_triage",
    "resume_decision",
    "retry_policy",
    "human_escalation"
  ],
  "allowed_kb_domains": ["postmortems", "provider_docs", "operations"],
  "input_artifacts": [
    "generation_ledger",
    "provider_error",
    "budget_state",
    "matrix_row",
    "validation_report",
    "profile_policy"
  ],
  "output_artifacts": ["failure_decision", "issue_record", "resume_plan"],
  "prompt_framework": "RCTCO"
}
```

Failure decisions should be structured, persisted, and attached to the graph state:

```json
{
  "decision_id": "failure:S001-01:v1",
  "error_class": "provider_account",
  "severity": "blocking",
  "safe_to_retry": false,
  "safe_to_continue_other_work": true,
  "next_graph_node": "provider_blocked_wait",
  "human_message": "Generation is paused because the provider has no remaining credit."
}
```

### Provider Health Registry

Provider state should be tracked separately from individual jobs.

Core fields:

- `provider_id`
- `status`
- `last_health_check_at`
- `last_successful_job_at`
- `quota_state`
- `credit_state`
- `known_outage`
- `blocked_reason`
- `resume_requirements`

Provider status values:

- `healthy`
- `degraded`
- `blocked_quota`
- `blocked_credit`
- `blocked_auth`
- `blocked_outage`
- `disabled_by_user`

If a provider is blocked because of credit, quota, auth, or outage, the orchestrator should
pause affected generation queues and preserve progress. It may continue unrelated planning,
writing, validation, and organization work.

### Model Registry

Models should be routed separately from agents.

An agent is a role and workflow contract. A model is an execution backend.

Suggested model metadata:

- `model_id`
- `provider`
- `strengths`
- `weaknesses`
- `cost_profile`
- `context_limit`
- `modalities`
- `preferred_tasks`
- `avoid_for`

This allows us to run the same validator or creator through different models.

## Multi-Model Review

The pipeline should support multiple models reviewing the same artifact.

This is useful because different models catch different classes of problems:

- one model may be stronger at story logic
- another may be stronger at visual reasoning
- another may be stricter about format and schemas
- another may be better at concise revision suggestions

### Review Patterns

Support several review strategies:

### Single Reviewer

Use one validator model for low-risk artifacts.

### Parallel Independent Review

Run the same validation prompt through multiple models independently.

Use for:

- script approval
- act approval
- full-movie review
- high-cost generation approval
- final delivery approval

### Specialist Panel

Run different validators on different aspects of the same artifact.

Example:

- story model reviews narrative logic
- visual model reviews references and shot design
- continuity model reviews state and flow
- production model reviews feasibility and cost

### Debate And Synthesis

Use when reviewers disagree.

Flow:

1. reviewers submit independent reports
2. synthesizer compares disagreements
3. orchestrator decides whether to revise, escalate, or ask the human

### Human-Arbitrated Review

Use for high-impact creative decisions.

The system should present:

- reviewer agreements
- reviewer disagreements
- blocking issues
- tradeoffs
- orchestrator recommendation

### Consensus Report

Multi-model review should produce one structured consensus artifact.

Suggested shape:

```json
{
  "review_id": "review:script:A1:v3",
  "artifact_refs": ["artifact:script:v3"],
  "reviewers": [
    {
      "model_id": "gemini-flash",
      "validator_id": "scene-writing-validator",
      "score": 88,
      "status": "pass_with_notes"
    },
    {
      "model_id": "gpt-5-mini",
      "validator_id": "scene-writing-validator",
      "score": 81,
      "status": "needs_revision"
    }
  ],
  "agreement_level": "medium",
  "consensus_status": "needs_revision",
  "shared_findings": [],
  "disagreements": [],
  "orchestrator_recommendation": "revise before human approval"
}
```

### Multi-Model Operating Rules

- creator and validator should usually use different models
- high-impact artifacts should get at least two independent reviews
- model disagreement should be visible, not averaged away silently
- reviewer outputs must use the same validation report schema
- the orchestrator synthesizes; it does not pretend disagreement did not happen
- human review remains the final authority at major gates

## Configuration-First Design

Most project behavior should be controlled by configuration.

Configurable items:

- active providers
- active validators
- model routing
- review strategy per phase
- validation thresholds
- approval gates
- budget limits
- delivery modes
- artifact storage paths

This makes the system adaptable per film without changing core code.

## Profile System

Users should be able to change pipeline behavior with config files only.

A profile is a named configuration bundle that selects:

- creative behavior
- agent roster
- model routing
- providers
- validators
- review strategy
- strictness levels
- budget rules
- generation defaults
- delivery modes

Profiles should be composable:

- a base studio profile
- a film-type profile
- a quality profile
- a provider profile
- a project override profile

Example layering:

```text
base.studio.yaml
+ film-type.narrative.yaml
+ quality.festival.yaml
+ provider.seedance-veo.yaml
+ project.the-primordial-stroke.yaml
```

Later profiles override earlier profiles.

### Profile Categories

### Film Type Profiles

Examples:

- `narrative`
- `visual_poetry`
- `experimental`
- `short_drama`
- `commercial`

Controls:

- story structure
- validation rubrics
- scene/act model
- pacing expectations
- delivery formats

### Quality Profiles

Examples:

- `draft`
- `internal_review`
- `studio`
- `festival`
- `social`

Controls:

- validator strictness
- number of model reviewers
- human approval frequency
- required review packages
- allowed fallback quality

### Provider Profiles

Examples:

- `free_or_low_cost`
- `seedance_primary`
- `veo_primary`
- `local_first`

Controls:

- provider order
- fallback chain
- model defaults
- max duration
- reference-image strategy
- cost limits

### Review Profiles

Examples:

- `fast_single_review`
- `multi_model_panel`
- `human_heavy`
- `strict_continuity`

Controls:

- single vs multi-model review
- required validators
- consensus strategy
- escalation rules
- disagreement handling

### Creative Profiles

Examples:

- `naturalistic_drama`
- `dreamlike_visual_poetry`
- `high_tension_thriller`
- `quiet_festival_film`

Controls:

- tone
- pacing
- camera language defaults
- writing constraints
- taboo mistakes
- preferred reference style

### Style Choice Catalogs

Users should not need to invent every style value manually. The system should provide curated
choice catalogs that profiles can reference.

Core catalogs:

- writing styles
- movie styles
- visual styles
- camera styles
- pacing styles
- tone styles
- editing styles
- music/audio styles
- reference styles
- delivery intents

These catalogs should be config-driven and extendable.

### Writing Style Choices

Examples:

- `literary_minimal`
- `naturalistic_dialogue`
- `poetic_voiceover`
- `silent_visual_storytelling`
- `high_tension_short_drama`
- `mythic_fable`
- `festival_slow_burn`
- `commercial_direct`

Controls:

- sentence density
- dialogue length
- subtext level
- voiceover usage
- exposition tolerance
- emotional explicitness

### Movie Style Choices

Examples:

- `arthouse_drama`
- `short_drama_vertical`
- `visual_poetry`
- `psychological_thriller`
- `surreal_fantasy`
- `commercial_spot`
- `documentary_hybrid`
- `music_video`

Controls:

- structure
- scene rhythm
- shot density
- emotional arc
- realism level
- audience expectation

### Visual Style Choices

Examples:

- `cinematic_realism`
- `painterly_realism`
- `dreamlike_soft_focus`
- `high_contrast_noir`
- `warm_natural_light`
- `sterile_modern`
- `mythic_ancestral`
- `abstract_symbolic`

Controls:

- color palette
- contrast
- texture
- lighting style
- realism level
- reference-image preference

### Camera Style Choices

Examples:

- `locked_observational`
- `handheld_tense`
- `slow_dolly_intimate`
- `floating_dreamlike`
- `wide_reverent`
- `portrait_shallow_focus`
- `kinetic_short_drama`

Controls:

- lens defaults
- movement defaults
- framing defaults
- stability
- depth of field
- scene-to-scene camera continuity

### Pacing Choices

Examples:

- `slow_burn`
- `measured_festival`
- `tight_short_film`
- `fast_vertical_drama`
- `dreamlike_drifting`
- `commercial_snap`

Controls:

- scene length
- shot duration
- dialogue speed
- transition speed
- act escalation
- compression rules

### Tone Choices

Examples:

- `intimate`
- `melancholic`
- `mysterious`
- `tense`
- `transcendent`
- `satirical`
- `romantic`
- `tragic`
- `hopeful`

Controls:

- emotional target
- taboo tonal breaks
- music direction
- lighting mood
- performance notes

### Editing Style Choices

Examples:

- `clean_continuity`
- `elliptical`
- `montage_driven`
- `cross_dissolve_poetic`
- `hard_cut_tension`
- `social_fast_cut`

Controls:

- transition defaults
- rhythm
- scene compression
- montage use
- final cut expectations

### Style Preset Example

```yaml
style_choices:
  writing_style: literary_minimal
  movie_style: arthouse_drama
  visual_style: painterly_realism
  camera_style: slow_dolly_intimate
  pacing: measured_festival
  tone: melancholic
  editing_style: clean_continuity
  audio_style: sparse_piano
  delivery_intent: festival_short
```

### Choice Validation

Style choices should be validated against the catalog.

Validation should check:

- selected choices exist
- selected choices are compatible
- selected choices match the film type
- selected choices do not conflict with delivery mode
- custom choices include required fields

Example conflict:

- `movie_style: visual_poetry` can work with `pacing: dreamlike_drifting`
- `movie_style: visual_poetry` may conflict with `editing_style: social_fast_cut`

The orchestrator should surface conflicts before production starts.

### Delivery Profiles

Examples:

- `review_cut`
- `social_vertical`
- `festival_16x9`
- `pitch_package`

Controls:

- aspect ratio
- runtime targets
- subtitles
- audio mix
- export settings
- review artifacts

### Example Profile

```yaml
profile_id: festival_narrative_seedance
extends:
  - base.studio
  - film-type.narrative
  - quality.festival
  - provider.seedance_primary
  - review.multi_model_panel

creative:
  pacing: deliberate
  tone: emotionally restrained
  camera_language: cinematic_realism

models:
  creator_default: gpt-5
  validator_default: gemini-flash
  secondary_reviewer: claude-sonnet
  synthesizer: gpt-5-mini

providers:
  video_primary: seedance-openrouter
  video_fallback: veo-lite
  image_primary: imagen

validation:
  script_threshold: 95
  prompt_threshold: 85
  clip_threshold: 86
  act_threshold: 88
  movie_threshold: 90
  multi_model_required_for:
    - script
    - act
    - full_movie
    - final_delivery

human_review:
  required_gates:
    - film_constitution
    - treatment
    - script
    - visual_bible
    - shot_bible
    - generation_plan
    - act_qc
    - final_delivery

budget:
  cap_usd: 120
  require_approval_over_usd: 10
  test_clip_seconds: 1

delivery:
  modes:
    - review_cut
    - festival_16x9
```

### Profile Validation

Profiles should be validated before a project starts.

Validation should check:

- referenced providers exist
- referenced validators exist
- referenced models exist
- thresholds are valid
- approval gates are known
- delivery modes are supported
- budget limits are present
- conflicting settings are rejected

### Profile Runtime Rules

- no code changes should be needed to switch from draft to festival quality
- no code changes should be needed to switch provider strategy
- no code changes should be needed to add stricter continuity review
- profiles should be stored as artifacts in the project
- the resolved profile should be saved at project start for reproducibility
- profile changes mid-project should create a new profile version and require approval

## Project Config Resolution

When a new project starts, the system should create a resolved project config from three
inputs:

1. studio defaults
2. user config file
3. user prompt or idea brief

The resolved config becomes the project contract. It should be saved as an artifact before
the graph starts meaningful creative work.

### Config Inputs

### Studio Defaults

Default config owned by the system.

Examples:

- default agents
- default validators
- default approval gates
- default artifact paths
- default RCTCO prompt requirements
- default budget safety rules
- default provider fallback policy

### User Config File

Optional user-authored config.

Examples:

- preferred film type
- desired quality profile
- budget cap
- provider preferences
- style choices
- strictness preferences
- delivery modes
- disabled providers or models

### User Prompt Or Idea Brief

Natural-language project input.

Examples:

- story idea
- intended mood
- genre
- runtime target
- audience
- visual references
- constraints
- desired output format

The orchestrator should analyze this prompt and infer missing config values, but inferred
values should be marked as inferred.

### Resolution Order

The project config should resolve in this order:

```text
studio defaults
+ selected base profiles
+ user config file
+ prompt-derived inferred config
+ orchestrator normalization
+ human approval
= resolved project config
```

Important rule:
Explicit user config should usually override prompt inference. Prompt inference should fill
gaps, not silently replace deliberate user choices.

### Resolved Config Artifact

The final config should be saved into the project as:

```text
project-config.resolved.yaml
```

It should include:

- all selected profiles
- all style choices
- all provider choices
- all validators
- all model routing
- all approval gates
- all budget limits
- all delivery modes
- inferred values
- assumptions
- conflicts
- human approval record

### Example Resolution

User prompt:

```text
I want a melancholic 8-minute arthouse film about a painter who slowly reconnects with
memory through color. It should feel poetic and restrained, not commercial.
```

User config:

```yaml
quality: festival
budget:
  cap_usd: 80
providers:
  video_primary: seedance-openrouter
delivery:
  modes:
    - review_cut
    - festival_16x9
```

Resolved config excerpt:

```yaml
profile_id: project.resolved
extends:
  - base.studio
  - film-type.narrative
  - quality.festival
  - provider.seedance_primary
  - review.multi_model_panel

style_choices:
  writing_style: literary_minimal
  movie_style: arthouse_drama
  visual_style: painterly_realism
  camera_style: slow_dolly_intimate
  pacing: measured_festival
  tone: melancholic
  editing_style: clean_continuity

budget:
  cap_usd: 80

providers:
  video_primary: seedance-openrouter
  video_fallback: veo-lite

delivery:
  modes:
    - review_cut
    - festival_16x9

inferred_from_prompt:
  runtime_minutes: 8
  tone: melancholic
  movie_style: arthouse_drama
  pacing: measured_festival

assumptions:
  - "No explicit aspect ratio was provided; using festival_16x9 from delivery profile."
  - "No explicit review profile was provided; using multi_model_panel because quality is festival."
```

### Config Validation Before Project Start

Before the project graph starts, the orchestrator should validate:

- all referenced profiles exist
- all selected style choices exist
- style choices are compatible
- providers are available or marked unavailable
- validators are registered
- models are registered
- budget rules are complete
- approval gates are valid
- inferred values are visible
- conflicts are surfaced to the user

If there are material conflicts, the system should create a config review package and pause
for human approval before continuing.

### Config Review Package

The first human-in-the-loop checkpoint should be config approval.

Review package contents:

- user prompt
- user config
- resolved config
- inferred choices
- assumptions
- conflicts or warnings
- orchestrator recommendation

Once approved, this config is versioned and becomes the baseline for the project.

## Dynamic Flow Model

The pipeline should not be a static script that always runs the same nodes in the same order.
Phases are guardrails. The actual path is selected dynamically by the orchestrator based on
project state, artifact readiness, validation results, human decisions, budget, provider
health, profile policy, and blockers.

The graph should behave like a studio operating system:

```text
inspect state -> compute eligible actions -> choose next action -> run specialist work
-> validate -> update state -> maybe pause for human -> repeat
```

### Dynamic Router

The orchestrator should use a dynamic router at every step.

Inputs:

- current phase
- requested MCP tool
- project profile
- available artifacts
- missing artifacts
- artifact approval status
- validation reports
- open issues
- dependency invalidation report
- provider health
- budget state
- active generation jobs
- human decisions
- KB context recommendations
- agent and validator registry capabilities

Outputs:

- next graph node
- selected agent or validator
- required input artifacts
- expected output artifact
- required KB context
- whether human review is required
- whether work can run in parallel
- whether work must pause
- why this route was selected

Suggested routing decision:

```json
{
  "routing_decision_id": "route:film_2026_0001:next:v12",
  "current_phase": "visual_development",
  "selected_action": "repair_reference_package",
  "selected_agent": "character-reference-agent",
  "reason": "Reference identity validator blocked the main character sheet.",
  "input_refs": [
    "artifact:character-bible:v2",
    "validation:reference-identity:v1"
  ],
  "blocked_actions": [
    {
      "action": "create_shot_bible",
      "reason": "visual references are not approved"
    }
  ],
  "can_run_in_parallel": [
    "environment_bible_review"
  ],
  "requires_human_review": false,
  "next_expected_artifact": "artifact:character-reference-sheet:v2"
}
```

### Action Catalog

Instead of hard-coding one sequence, define an action catalog. Each action declares when it is
eligible.

Example:

```yaml
action_id: create_shot_bible
requires:
  approved:
    - script
    - scene_intents
    - character_bible
    - environment_bible
    - camera_language_bible
  no_blocking_issues:
    - visual_references
    - continuity
produces:
  - shot_bible
  - master_film_matrix
  - continuity_ledger
default_agents:
  - shot-design-agent
  - blocking-agent
  - continuity-ledger-agent
validators:
  - shot-design-validator
  - scene-flow-validator
human_gate_after: true
```

This lets profiles add, remove, or reorder actions without rewriting the orchestrator.

### Dynamic Behaviors We Need

The graph should support:

- skipping irrelevant phases for simple projects
- adding extra development passes for weak stories
- running visual development and script polishing in parallel when safe
- blocking shot bible until references are approved
- repairing only failed artifacts instead of rerunning a whole phase
- pausing only affected generation chains after provider errors
- continuing unrelated work during provider blocks
- branching for creative alternatives
- rolling back to checkpoints
- revalidating only invalidated downstream artifacts
- escalating to human review when confidence is low
- changing model/provider routing from profile config
- expanding validation when risk is high

### State-Driven Next Actions

The orchestrator should expose next actions through MCP.

Example response:

```json
{
  "project_id": "film_2026_0001",
  "status": "blocked_reference_validation",
  "current_phase": "visual_development",
  "available_actions": [
    {
      "action": "repair_character_reference",
      "recommended": true,
      "reason": "Main character identity sheet failed validation."
    },
    {
      "action": "review_environment_bible",
      "recommended": false,
      "reason": "Can continue independently while character reference is repaired."
    },
    {
      "action": "create_shot_bible",
      "enabled": false,
      "reason": "Requires approved references."
    }
  ]
}
```

### Graph Shape

Use a layered graph:

- top-level project graph
- phase subgraphs
- action nodes
- validation nodes
- human interrupt nodes
- repair nodes
- rollback nodes
- provider-block nodes
- wrap/lesson nodes

Conditional edges should be driven by structured state, not freeform prose.

Examples:

```text
validation.status == "pass" -> review_package
validation.status == "needs_revision" -> repair_action_router
validation.status == "block" -> human_or_repair_gate
provider.status == "blocked_quota" -> provider_blocked_wait
artifact.invalidated == true -> targeted_revalidation
human.decision == "request_revision" -> revision_router
human.decision == "approve" -> checkpoint_and_continue
```

### Dynamic Does Not Mean Chaotic

Dynamic flow still needs strong constraints:

- all actions must be registered
- all actions must declare inputs and outputs
- all state mutations happen through MCP/graph nodes
- all artifacts are versioned
- all validation reports are structured
- all route decisions are logged
- human gates remain mandatory where policy requires them
- expensive actions require explicit approval

## Default Phase Map

### Phase 0. Project Intake

Purpose:
Create the project and collect the initial idea.

Detailed intake behavior is defined in
`project-intake.md` (retired during docs cleanup).

Key agents:

- intake-agent
- genre-classifier-agent
- feasibility-scout-agent

Artifacts:

- project profile
- initial idea brief
- initial risk notes

Human gate:
Approve project setup and creative direction.

### Phase 1. Film Constitution

Purpose:
Define the creative spine.

Key agents:

- theme-agent
- tone-agent
- visual-language-agent
- character-truth-agent
- taboo-mistakes-agent

Artifacts:

- film constitution
- creative guardrails

Human gate:
Approve the non-negotiable creative rules.

### Phase 2. Development

Purpose:
Turn the idea into a strong treatment.

Key agents:

- logline-agent
- premise-agent
- treatment-agent
- story-structure-agent
- act-architect-agent
- narrative-density-validator

Artifacts:

- logline
- premise
- treatment
- act map
- development validation report

Human gate:
Approve treatment and act structure.

### Phase 3. Screenwriting

Purpose:
Create and refine the script.

Key agents:

- scene-beat-agent
- screenwriter-agent
- dialogue-agent
- character-arc-agent
- theme-review-agent
- scene-writing-validator

Artifacts:

- script
- scene list
- scene intent sheets
- script validation report

Human gate:
Approve script and scene intent sheets.

### Phase 4. Visual Development

Purpose:
Define characters, environments, references, and camera language.

Reference image details are defined in
`reference-image-flow.md` (retired during docs cleanup).

Key agents:

- character-dossier-agent
- environment-bible-agent
- camera-language-agent
- reference-brief-agent
- reference-strategy-planner
- character-reference-validator
- environment-reference-validator

Artifacts:

- character dossiers
- environment bible
- camera language bible
- reference strategy
- visual validation report

Human gate:
Approve visual bible and reference strategy.

### Phase 5. Shot Bible

Purpose:
Translate script and visual design into executable shots.

Multi-angle scene coverage is defined in
`multi-angle-coverage.md` (retired during docs cleanup).

Key agents:

- shot-design-agent
- blocking-agent
- prompt-composition-agent
- continuity-ledger-agent
- creative-risk-register-agent
- prompt-readiness-validator
- scene-flow-validator

Artifacts:

- shot bible
- prompt package
- continuity ledger
- creative risk register
- shot validation report

Human gate:
Approve shot bible before generation planning.

### Phase 6. Generation Planning

Purpose:
Plan providers, budget, re-anchors, fallbacks, and batch strategy.

Key agents:

- provider-planning-agent
- cost-estimation-agent
- reference-risk-agent
- generation-scheduler-agent

Artifacts:

- generation plan
- budget forecast
- provider plan
- checkpoint plan

Human gate:
Approve spend and generation strategy.

### Phase 7. Clip Generation

Purpose:
Generate clips according to the approved plan.

Safe generation execution is defined in
`clip-generation-execution.md` (retired during docs cleanup).

Key agents:

- generation-runner-agent
- checkpoint-agent
- provider-monitor-agent
- clip-ingestion-agent

Artifacts:

- generated clips
- last-frame captures
- provider run records
- checkpoint state

Human gate:
Approve generated batch or request targeted repair.

### Phase 8. Multi-Level QC

Purpose:
Validate clips, scenes, acts, and full movie structure.

Key agents:

- clip-validator
- artifact-detector
- prompt-adherence-validator
- scene-continuity-validator
- act-continuity-validator
- full-movie-flow-validator
- payoff-validator

Artifacts:

- clip QC reports
- scene QC reports
- act QC reports
- movie QC report
- revision recommendations

Human gate:
Approve QC outcome and revision plan.

### Phase 9. Post-Production

Purpose:
Assemble the film and validate delivery.

Key agents:

- assembly-agent
- transition-agent
- audio-sync-agent
- color-agent
- timeline-validator
- delivery-validator

Artifacts:

- assembly manifest
- review cut
- audio report
- final delivery report

Human gate:
Approve final cut or request revisions.

### Phase 10. Wrap

Purpose:
Close the project and learn from it.

Key agents:

- cost-report-agent
- lessons-agent
- archive-agent
- failure-memory-agent

Artifacts:

- cost report
- lessons learned
- incident summaries
- archive manifest

Human gate:
Approve wrap and KB updates.

## Orchestrator Responsibilities

The orchestrator must:

- read current state
- select the next graph transition
- choose specialist agents
- provide each agent with scoped KB context
- enforce validation gates
- assemble human review packages
- pause for human approval
- turn validation failures into revision requests
- protect budget and provider limits
- maintain executive summaries

The orchestrator should not:

- write every artifact itself
- validate its own output
- hide failed checks
- advance phases without approval

## Prompt Framework

All agent prompts should use the RCTCO framework from
[`film-knowledge-base/prompt-framework.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/film-knowledge-base/prompt-framework.md).

RCTCO means:

- `R`: Role
- `C1`: Core Task
- `T`: Context
- `C2`: Constraints
- `O`: Output Format

This should apply to:

- creator-agent prompts
- reviewer-agent prompts
- validator-agent prompts
- orchestrator delegation prompts
- revision prompts
- human review package summaries

### Prompt Contract

Every executable agent prompt should have this structure:

```json
{
  "prompt_id": "scene-writing-v1",
  "agent_id": "scene-beat-agent",
  "r": "Role the agent must adopt",
  "c1": "Specific task the agent must perform",
  "t": {
    "project_context": [],
    "kb_context": [],
    "artifact_refs": []
  },
  "c2": {
    "constraints": [],
    "must_include": [],
    "must_avoid": [],
    "quality_bar": ""
  },
  "o": {
    "format": "json",
    "schema_ref": "artifact-schema:scene-intent"
  }
}
```

### Prompt Validation

Before an agent runs, the orchestrator or prompt-readiness validator should check:

- role is explicit
- task is specific and actionable
- context includes only relevant KB and artifact references
- constraints are concrete
- output format is machine-readable when downstream agents need it
- assumptions are stated when the prompt fills gaps

Prompts missing any RCTCO component should be revised before execution.

### Why It Matters

RCTCO prevents several failure modes we already saw:

- vague writer prompts
- validators judging against unclear criteria
- agents receiving too much unrelated KB context
- outputs that look useful but cannot be parsed or validated
- revision loops where the critique is not tied to a concrete task

## Validation Contracts

Every validator should produce the same high-level report shape:

```json
{
  "validator_id": "clip-validator",
  "scope": "clip",
  "modality": ["video", "continuity"],
  "artifact_refs": ["artifact:shot-001-clip"],
  "score": 86,
  "status": "pass",
  "blocking_issues": [],
  "warnings": [],
  "recommended_actions": [],
  "requires_human_review": false
}
```

Status values:

- `pass`
- `pass_with_notes`
- `needs_revision`
- `blocked`

## Consistency Strategy

Consistency should be maintained by design, not repaired only after generation.

The system needs three canonical bibles:

- character bible
- environment bible
- story bible

These bibles are approved artifacts. Downstream agents must reference them rather than
recreating descriptions from memory.

### Character Consistency

Canonical artifacts:

- character dossier
- visual identity sheet
- voice and dialogue rules
- wardrobe rules
- emotional arc map
- relationship state map
- approved reference images

Runtime rules:

- character descriptions are locked atomic blocks
- identity anchors appear in every relevant shot prompt
- wardrobe and physical state come from the continuity ledger
- dialogue agents follow the character voice rules
- generated clips are checked against approved references where possible

Validators:

- character-dossier-validator
- dialogue-voice-validator
- character-arc-validator
- reference-identity-validator
- clip-character-consistency-validator

### Environment Consistency

Canonical artifacts:

- environment bible
- location map
- lighting rules
- color palette
- time-of-day rules
- weather rules
- approved environment plates
- spatial continuity notes

Runtime rules:

- environment descriptions are locked atomic blocks
- scene and shot prompts pull location details from the environment bible
- lighting and palette are inherited from the approved scene context
- camera blocking respects the location map
- environment changes must be intentional story events

Validators:

- environment-bible-validator
- location-continuity-validator
- lighting-continuity-validator
- spatial-logic-validator
- clip-environment-fidelity-validator

### Story Consistency

Canonical artifacts:

- film constitution
- act map
- treatment
- script
- scene intent sheets
- continuity ledger
- unresolved thread tracker
- setup/payoff map

Runtime rules:

- every scene must declare what changes
- every shot must map to scene intent
- unresolved threads are tracked until resolved or intentionally abandoned
- act-level validators check escalation and pacing
- full-movie validators check setup/payoff, arc completion, and theme

Validators:

- scene-intent-validator
- narrative-density-validator
- act-structure-validator
- setup-payoff-validator
- full-movie-coherence-validator

### Continuity Ledger

The continuity ledger is the main mechanism that ties character, environment, and story
consistency together.

It should track per scene and per shot:

- character location
- body state
- wardrobe
- props
- emotional state
- relationship state
- environment
- lighting
- time of day
- unresolved story threads
- previous reference image
- next required anchor

Each shot should have:

- `state_in`
- `action`
- `state_out`
- `continuity_risks`
- `required_anchors`
- `validation_refs`

### Prompt Assembly Rule

Prompts should be composed from approved blocks:

```text
FILM_CONSTITUTION
+ SCENE_INTENT
+ ENVIRONMENT_BLOCK
+ CHARACTER_BLOCKS
+ CONTINUITY_STATE
+ CAMERA_LANGUAGE
+ ACTION
+ ANCHORS
+ NEGATIVES
```

Agents should not hand-write freeform prompts from scratch once canonical blocks exist.

### Consistency Review Rhythm

Consistency checks should run at multiple intervals:

- before scene approval
- before shot-bible approval
- before generation
- after each generated clip
- after each scene group
- after each act
- before final delivery

This gives the pipeline several chances to catch drift before it compounds.

## MCP Tool Surface

MCP is the first-class control plane. The pipeline should be operable through MCP even before
there is a custom web UI.

MCP operating rules:

- every user-visible action should have a tool contract
- every tool must accept or resolve `project_id`
- tools that mutate approved work must create version records
- tools that spend money must expose estimated cost and require approval when policy says so
- tools that resume generation must consult the generation ledger first
- tools should return structured next actions, not only prose
- tools should expose review packages that are easy for OpenClaw to present conversationally
- dangerous operations such as rollback, provider switch, regeneration, deletion, and final
  delivery export require explicit confirmation

Initial MCP tools should include:

Project tools:

- `list_projects`
- `find_project`
- `set_active_project`
- `get_active_project`
- `create_film_project`
- `submit_idea`

State and review tools:

- `get_project_state`
- `get_orchestrator_summary`
- `list_phase_artifacts`
- `review_phase`
- `approve_phase`
- `request_revision`

Registry tools:

- `list_agents`
- `list_validators`
- `list_providers`
- `get_provider_health`
- `check_provider_health`

Inspection tools:

- `inspect_scene`
- `inspect_shot`
- `inspect_reference`
- `inspect_validation_report`
- `inspect_continuity_ledger`
- `export_review_package`

Versioning tools:

- `list_checkpoints`
- `create_checkpoint`
- `compare_versions`
- `rollback_to_checkpoint`

Coverage tools:

- `plan_coverage_group`
- `inspect_coverage_group`

Generation-era MCP contracts should be defined early, even if provider-backed
implementations come later:

- `plan_generation_batch`
- `approve_generation_spend`
- `start_generation_batch`
- `pause_generation`
- `resume_generation`
- `get_generation_status`
- `list_active_generations`
- `get_generation_ledger`
- `inspect_failure_decision`
- `resolve_provider_block`
- `inspect_clip_qc`
- `assemble_review_cut`
- `export_final_delivery`

Suggested MCP response shape:

```json
{
  "project_id": "film_2026_0001",
  "status": "requires_human_review",
  "summary": "Scene references are ready for review.",
  "artifact_refs": ["artifact:reference-index:v2"],
  "validation_refs": ["validation:references:v2"],
  "issues": [],
  "next_actions": [
    {
      "action": "approve_phase",
      "label": "Approve references",
      "requires_confirmation": true
    },
    {
      "action": "request_revision",
      "label": "Revise selected references",
      "requires_confirmation": false
    }
  ]
}
```

## KB Operating Model

The KB should be a governed studio memory, not an undifferentiated document dump.

Use four authority levels:

- canonical policy
- active playbook
- case-study lesson
- raw archive

The orchestrator should build scoped KB context packets per graph node and agent. Every
artifact should store `kb_context_ref` so decisions are explainable later.

See
`kb-operating-model.md` (retired during docs cleanup)
for the full design.

## MVP Recommendation

The first MVP should stop before expensive full video generation.

The detailed gap list and recommended build order are defined in
`remaining-needs.md` (retired during docs cleanup).

Build:

1. project intake
2. film constitution
3. treatment generation and validation
4. script and scene intent sheets
5. visual bible and reference strategy
6. shot bible and continuity ledger
7. validation reports
8. human approval gates
9. MCP inspection and approval tools
10. mock provider generation dry run
11. mock resume and failure scenarios

This proves the studio operating system before real provider cost and generation instability
enter the loop. Real provider integrations should come only after the mock provider can run a
small film end to end through MCP, graph state, ledgers, validation, human review, and
checkpoint/resume.
