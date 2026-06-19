# Remaining Needs

## Purpose

The project vision is strong: MCP-first, LangGraph orchestration, many expert agents, human
review gates, governed KB, mock provider, validation at many levels, and safe generation.

What remains is turning the vision into buildable contracts and operational guardrails.

## Highest Priority Gaps

### 1. Formal Schemas

We need schemas before serious implementation.

Define schemas for:

- project config
- project state
- artifact metadata
- approval records
- issue records
- revision requests
- agent registry entries
- provider registry entries
- validator registry entries
- model registry entries
- KB context packets
- generation ledger rows
- validation reports
- master film matrix rows
- continuity ledger entries
- asset manifests
- MCP tool responses

Why it matters:

- LangGraph state becomes stable
- MCP responses become predictable
- agents can be tested independently
- validators can enforce structure
- versioning and rollback are safer

### 2. MCP Tool Contract Specification

Because the project is MCP-first, the tool surface needs its own contract document.

Define for each tool:

- tool name
- purpose
- input schema
- output schema
- required permissions
- idempotency behavior
- mutates state or read-only
- creates checkpoint or not
- requires human confirmation or not
- possible errors
- example requests and responses

Minimum MCP groups:

- project tools
- intake tools
- state inspection tools
- artifact inspection tools
- review and approval tools
- revision tools
- KB tools
- agent and registry tools
- validation tools
- generation planning tools
- mock provider tools
- checkpoint and rollback tools
- provider health tools

### 3. LangGraph State Machine Design

We need a real graph design, not just phase names.

Define:

- graph nodes
- phase subgraphs
- dynamic router
- action catalog
- interrupts
- resume points
- conditional edges
- failure edges
- human approval edges
- rollback edges
- provider-block edges
- artifact invalidation edges

The graph should be able to answer:

- What phase are we in?
- What is blocking progress?
- What can safely continue?
- What needs human review?
- What changed since last approval?
- What checkpoint can we resume from?

### 4. Artifact Storage And Asset Manifest

Generated media and reference images need a storage model.

Define:

- where text artifacts live
- where generated assets live
- which files are committed to git
- which files use git LFS or external storage
- how asset paths are referenced
- how thumbnails/previews are generated
- how deleted or superseded takes are handled
- how active takes are selected
- how asset integrity is checked

Required manifests:

- reference asset manifest
- generated clip manifest
- frame extraction manifest
- audio asset manifest
- assembly manifest
- delivery manifest

### 5. Test Harness

The mock provider gives us a foundation, but we also need a test harness around it.

The initial end-to-end acceptance journeys are defined in
[`e2e-test-scenarios.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/e2e-test-scenarios.md).

Test categories:

- schema validation tests
- MCP contract tests
- graph transition tests
- human interrupt/resume tests
- mock human decision tests
- mock provider happy path
- mock provider failure scenarios
- no duplicate generation tests
- checkpoint/resume tests
- rollback tests
- KB retrieval tests
- validator output schema tests
- artifact invalidation tests
- end-to-end mini-film test

The most important test:

```text
idea -> config -> treatment -> script -> references -> shot bible -> mock generation
-> validation -> review cut -> wrap
```

This should run with zero paid providers.

Use a mock human actor for automated E2E tests. The mock human should respond through the
same MCP approval/revision tools as a real user, but its approvals must be marked as test
approvals and rejected outside test mode.

### 6. Observability And Audit Trail

We need to see what the studio did and why.

Log:

- MCP request id
- project id
- graph node
- selected agent
- selected model
- KB context refs
- input artifact refs
- output artifact refs
- validation refs
- cost estimate
- provider job id
- decision reason
- human approval ref
- checkpoint ref

Add inspection tools:

- `get_audit_log`
- `explain_last_decision`
- `explain_agent_routing`
- `explain_kb_context`
- `get_blockers`
- `get_next_actions`

### 7. Cost, Budget, And Permission Policy

The system needs a policy layer for spend and risk.

Define:

- per-project budget
- per-phase budget
- per-provider budget
- max auto-approved cost
- when human approval is required
- when provider fallback is allowed
- when regeneration is allowed
- when parallel generation is allowed
- who can approve expensive actions

Budget must connect to:

- provider planning
- generation scheduling
- failure handling
- MCP confirmations
- audit log

### 8. Security And Secrets

Provider keys and project assets need basic protection.

Define:

- secret storage strategy
- provider credential lookup
- no secrets in prompts
- no secrets in artifacts
- no secrets in logs
- per-provider credential health check
- safe error redaction
- user confirmation before external uploads

This matters because video providers, image providers, and storage services will all require
credentials.

### 9. Model Routing Policy

We already want multi-model review. We need routing rules.

Define:

- model profiles
- default model per agent role
- fallback model policy
- creator versus validator separation
- cheap model versus strong model policy
- multi-review quorum rules
- disagreement synthesis rules
- model availability checks
- cost-aware routing

Example model profiles:

- `creative_writer`
- `strict_validator`
- `visual_reasoner`
- `schema_enforcer`
- `cheap_draft`
- `operations_triage`

### 10. Validation Registry And Rubric Packs

Validators should be pluggable.

Define:

- validator id
- scope
- modality
- input artifacts
- output schema
- thresholds
- blocking conditions
- warning conditions
- repair recommendation format
- whether human review is required

Rubric packs:

- writing
- character
- environment
- reference image
- prompt readiness
- clip quality
- scene continuity
- act structure
- full movie coherence
- post-production delivery

### 11. Project Template And Profiles

Users should be able to change behavior through config files.

Create templates for:

- narrative short film
- visual poetry
- experimental film
- music video
- commercial/ad
- documentary-style piece
- social short

Each profile should define:

- default phases
- default agents
- default validators
- style choices
- length options
- camera defaults
- reference requirements
- generation policy
- review strictness
- provider preferences
- budget defaults

### 12. UI/Review Package Shape

Even if OpenClaw is the main operator, review packages need a consistent shape.

Each review package should include:

- summary
- artifact list
- diff from last approved version
- validation results
- open issues
- risks
- cost impact
- orchestrator recommendation
- available actions

Review package types:

- config review
- treatment review
- script review
- visual bible review
- reference package review
- shot bible review
- generation plan review
- clip batch review
- final cut review

### 13. Invalidation Engine

When something changes, downstream artifacts may become stale.

Examples:

- character bible change invalidates references, prompts, and clip validators
- environment bible change invalidates environment boards and shot prompts
- script change invalidates scene intents, shot bible, prompts, and continuity ledger
- provider change may invalidate prompt formatting and cost plan
- style profile change may invalidate visual bible and references

We need an invalidation report before changes are accepted.

### 14. Delivery And Export Strategy

Final output is more than an MP4.

Define delivery packages:

- final video
- review cut
- subtitle files
- audio stems
- stills
- prompt archive
- reference archive
- validation report
- cost report
- credits/metadata
- project archive

### 15. Governance For Human Decisions

Human-in-the-loop is mandatory, so approvals need structure.

Define:

- approval records
- rejection records
- revision request records
- who approved
- what was approved
- what changed since approval
- expiration or invalidation of approvals
- approval required before spend
- approval required before KB promotion

## Build Order Recommendation

Recommended order:

1. Schemas and registries
2. MCP tool contracts
3. Project config/profile system
4. Artifact store and manifests
5. LangGraph state machine skeleton
6. KB context packet builder
7. Agent registry and prompt runner
8. Review package generator
9. Validation registry
10. Mock provider and test harness
11. Checkpoint/resume and rollback
12. End-to-end mock mini-film
13. Real provider adapter
14. Post-production assembly
15. Production hardening

## First Implementation Slice

The smallest useful build should be:

- create project through MCP
- resolve active project through MCP
- generate project config from user idea
- create film constitution
- produce treatment
- create review package
- approve or request revision
- persist artifacts and approvals
- create checkpoint
- inspect state through MCP

This proves the MCP-first spine before complex generation.

## Definition Of Ready For Real Providers

Do not connect paid providers until:

- mock provider happy path passes
- mock provider failure scenarios pass
- no-duplicate generation test passes
- checkpoint/resume test passes
- provider block handling works
- budget approval works
- generation ledger is stable
- clip ingestion and asset manifests work
- human approval gates are enforced
- audit trail explains every provider action

## Bottom Line

The vision is now broad enough. The next need is discipline:

- contracts before cleverness
- mock execution before paid execution
- explainability before autonomy
- validation before scale
- human approval before irreversible action
