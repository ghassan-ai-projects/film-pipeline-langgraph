# Fresh Review

## Review Scope

This review looked at:

- the current repo surface
- the local `film-knowledge-base/`
- the current [`vision-and-direction.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/vision-and-direction.md)
- cloned reference repos under `~/external-projects/`

The important finding: we have unusually rich production knowledge, but the repo still needs
to turn that knowledge into a crisp runtime architecture.

## Current Repo State

The tracked project surface is still small:

- `README.md`
- `docs/vision-and-direction.md`
- `docs/fresh-review.md`
- `docs/architecture-blueprint.md`
- `LICENSE`

The real planning fuel lives in local research material:

- `film-knowledge-base/`
- `~/external-projects/agentic-drama-pipeline`
- `~/external-projects/ai-drama-engine-demo`
- `~/external-projects/VEO.IO`

This is fine for vision work, but implementation should make a deliberate choice:

- either keep the large KB as a local research source and ingest/index it
- or promote curated parts into the repo as canonical schemas, prompts, configs, and tests

We should not accidentally depend on hidden local folders without documenting that dependency.

## What We Already Have

The local KB gives us a strong foundation:

- a unified film-production skill
- the RCTCO prompt framework
- provider abstraction
- cost guardrails
- checkpointing and resume logic
- postmortem lessons from real failures
- validation rubrics
- prompt composition patterns
- post-production references
- prior film case studies

This is not generic brainstorming. It is production scar tissue in useful form.

## Main Strengths

### 1. Strong Memory Of Real Failures

The postmortem names concrete problems:

- moderation failures
- bad cost assumptions
- key limits breaking long chains
- scattered provider logic
- script-owned validation loops
- informal human review

These are exactly the right failures to encode into the new system.

### 2. Good Existing Production Protocol

The unified skill has the right instincts:

- phase gates
- provider abstraction
- no hidden retries
- checkpointing
- post-production as a phase
- validation as part of the lifecycle

It should be treated as source material for a LangGraph runtime, not discarded.

### 3. Clear Direction Toward Human-Supervised Studio Work

The current vision correctly centers:

- many narrow expert agents
- one orchestrator agent
- human-in-the-loop approval
- MCP control from OpenClaw
- artifact organization
- multi-level validation

This is the right shape.

## Main Gaps

### 1. Vision Is Ahead Of Contracts

We know what we want, but the repo does not yet define:

- state schemas
- artifact schemas
- graph nodes
- subgraphs
- MCP tool contracts
- validation report contracts
- approval event contracts

The next phase should close that gap.

### 2. The KB Is Not Yet Operational

The KB is large and useful, but right now it is still mostly documentation.

We need to classify it into:

- canonical rules
- operational references
- case studies
- raw archive

Then promote the rules into schemas, configs, and runtime checks.

### 3. Validation Needs Execution Semantics

The vision has a strong taxonomy, but we still need to define:

- which validators run at each phase
- what input each validator receives
- what output schema each validator produces
- what score blocks progress
- what score requires human review
- what score creates a revision request

Prompt validation should also be explicit. The new
[`prompt-framework.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/film-knowledge-base/prompt-framework.md)
should become the standard for all agent prompts: Role, Core Task, Context, Constraints,
and Output Format.

### 4. The Orchestrator Needs A Concrete Job Description

The orchestrator should not become a vague "manager agent."

It needs concrete responsibilities:

- read current state
- choose next graph transition
- assign specialist agents
- select KB context
- create review packages
- enforce approval gates
- summarize risks
- decide revision path after validation failures

### 5. Post-Production Needs To Stay In Scope

The previous pipeline treated post-production too lightly. The new architecture should keep
assembly, audio, color, delivery reports, and final validation in the graph.

## Lessons From Cloned Repos

### `agentic-drama-pipeline`

Useful:

- typed data contracts
- simple agent decomposition
- human-readable plus structured outputs
- deterministic local demo path

Limit:

- too lightweight for expensive generation and long-running review gates

Adopt:

- schema clarity
- artifact-first outputs
- simple testable workflow runner ideas

### `ai-drama-engine-demo`

Useful:

- real generated assets
- reference image pathing
- face similarity checks
- quality report with publishability status
- per-shot issue reporting
- delivery summary

Limit:

- more vertical script pipeline than LangGraph studio architecture

Adopt:

- per-shot QC records
- final delivery summaries
- reference consistency checks
- "internal review" vs "publishable" quality levels

### `VEO.IO`

Useful:

- product/platform framing

Limit:

- little implementation detail in the cloned repo

Adopt:

- think in terms of operator interface and product workflow, not a one-off script

## Recommended Updates To Direction

The project should now split work into five documents or modules:

- vision: what we are building and why
- architecture: graph, state, agents, MCP tools
- KB operating model: what knowledge is canonical and how agents retrieve it
- validation model: validators, reports, gates, revision paths
- MVP plan: what gets built first

The current [`vision-and-direction.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/vision-and-direction.md) can remain the high-level source of truth. The new architecture blueprint should become the next working document.

## Immediate Recommendation

Build the first version around pre-production and review:

1. idea intake
2. film constitution
3. treatment
4. script
5. scene intent sheets
6. shot bible
7. reference strategy
8. validation reports
9. human approval packages
10. MCP inspection and approval tools

This proves the studio brain before full video generation cost enters the system.
