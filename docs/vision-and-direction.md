# Film Pipeline Vision And Direction

## Companion Docs

- [`fresh-review.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/fresh-review.md) captures the fresh-eyes review of the current docs, KB, and cloned repos.
- [`architecture-blueprint.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/architecture-blueprint.md) turns this vision into implementable phases, agents, artifacts, validation contracts, and MCP tools.
- [`reference-image-flow.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/reference-image-flow.md) defines how reference images are planned, generated, validated, approved, and registered.
- [`environment-consistency.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/environment-consistency.md) defines how same-location consistency is maintained across zones, viewpoints, lighting states, and clips.
- [`project-intake.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/project-intake.md) defines how the first user input is classified, expanded, inferred, validated, and approved.
- [`versioning-and-checkpoints.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/versioning-and-checkpoints.md) defines artifact versions, phase checkpoints, rollback, branching, and invalidation.
- [`multi-angle-coverage.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/multi-angle-coverage.md) defines how the same story moment can be generated from multiple camera angles and assembled in post.
- [`clip-generation-execution.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/clip-generation-execution.md) defines safe video generation execution, polling, idempotency, test mode, and cost controls.

## Purpose

This project should become a **studio-grade film creation operating system** built on
LangGraph, not just a collection of generation scripts.

It should take an initial idea and drive it through structured creative,
technical, and production phases until final delivery, while enforcing:

- high-end creative writing quality
- multi-agent specialization
- many narrow domain experts rather than a few general-purpose agents
- typed state and explicit handoffs
- strong organization of every output artifact
- mandatory human review after each major phase
- provider-agnostic execution
- validation at clip, scene, reference, and continuity levels
- MCP-first control so the system can be operated conversationally from OpenClaw
- RCTCO-structured prompts for every agent interaction

## What We Already Have

The existing knowledge base and skill are strong in the areas that matter most for
real production discipline:

- an end-to-end lifecycle in [`film-knowledge-base/skills/film-production-pipeline/SKILL.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/film-knowledge-base/skills/film-production-pipeline/SKILL.md)
- provider abstraction in [`provider-abc.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/film-knowledge-base/skills/film-production-pipeline/references/provider-abc.md)
- validation gates in [`validation-rubric.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/film-knowledge-base/skills/film-production-pipeline/references/validation-rubric.md)
- checkpointing and recovery in [`checkpoint-system.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/film-knowledge-base/skills/film-production-pipeline/references/checkpoint-system.md)
- hard-earned production lessons in [`article.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/film-knowledge-base/articles/ART-029-film-pipeline-postmortem/article.md)

The older [`seedance` skill](/Users/ghassan/my-projects/film-pipeline-langgraph/film-knowledge-base/skills/seedance/SKILL.md) also preserves valuable ideas that should not be lost:

- stronger agent choreography
- explicit flow validation between scenes
- continuity ledger thinking
- output validation as a first-class step

## What Is Missing

The current unified skill is a **protocol**, but not yet a **LangGraph-native studio system**.

Main gaps:

- no explicit LangGraph state model for the full film lifecycle
- no graph-level interrupt/resume design for mandatory human approval
- no MCP tool surface for conversational control of the pipeline
- no persistent “director console” view over phase status, artifacts, blockers, and approvals
- validation is documented well, but not yet modeled as graph subflows with durable state
- orchestration is still too script-centric in places
- post-production and review are still more procedural than agentic

## Postmortem Guardrails

The new pipeline should explicitly defend against the failures documented in
[`article.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/film-knowledge-base/articles/ART-029-film-pipeline-postmortem/article.md).

These are not historical footnotes. They should become design requirements.

### Mistake 1. Scattered logic and no single source of truth

Design response:

- one canonical provider layer
- one canonical artifact registry
- one canonical film state
- one orchestrator-driven runtime instead of many disconnected scripts

### Mistake 2. Cost assumptions detached from real provider billing

Design response:

- cost model must be part of runtime state
- projected spend and actual spend must be tracked separately
- provider switches must be mediated by the orchestrator
- expensive transitions require explicit human approval

### Mistake 3. Long generation chains failing without graceful recovery

Design response:

- checkpoint every durable step
- resume from any approved phase and any shot batch
- preflight checks for provider availability, budget, and key status
- every long-running operation must produce resumable state

### Mistake 4. Validation loops owned by scripts instead of agents

Design response:

- scripts may prepare data or parse results
- orchestration decisions belong to the orchestrator and specialist agents
- validation outcomes must be explicit graph events, not hidden script behavior

### Mistake 5. Human review happening informally instead of structurally

Design response:

- formal review gates with interrupts
- review decisions stored as state
- revision requests stored as first-class artifacts
- no phase advances on assumed approval

### Mistake 6. Drift and continuity handled too manually

Design response:

- continuity ledger as a required artifact
- automated drift signals where possible
- dedicated continuity agents and validators
- re-anchor strategy encoded in the generation plan

### Mistake 7. Post-production documented but not operationalized

Design response:

- post-production must be a graph phase, not an appendix
- assembly manifests should be generated automatically
- validation should continue through post and delivery

## Knowledge Base Strategy

Yes, the KB is large, and that is a strength if we use it deliberately.

The knowledge base should not be treated as passive documentation only.
It should serve four roles in the new system.

### 1. Design Memory

The KB stores prior failures, protocols, heuristics, and proven patterns.

Use it to:

- seed system design decisions
- define agent instructions
- encode guardrails from previous failures
- prevent “reinventing the same broken workflow”

### 2. Retrieval Context For Agents

Different agents should retrieve different slices of the KB based on task.

Examples:

- writing agents retrieve narrative, theme, and prior film structure material
- visual-dev agents retrieve reference-image and environment guidance
- production agents retrieve provider, cost, checkpoint, and prompt rules
- QC agents retrieve validation rubrics and postmortem failure patterns
- post agents retrieve assembly and grading references

This means the orchestrator should route **task-specific KB context**, not dump the full KB into every agent.

### 3. Policy Layer

Parts of the KB should become executable policy inputs.

Examples:

- validation thresholds
- provider fallback chain
- checkpoint rules
- approval requirements
- error-handling rules
- continuity and prompt-composition rules

These should be promoted from prose into config, schemas, and runtime checks.

### 4. Continuous Learning Loop

Every new project should feed new lessons back into the KB.

The new pipeline should produce:

- structured incident reports
- review findings
- generation failure summaries
- cost deltas
- continuity failure examples
- post-production lessons

That turns the KB into a living studio memory system.

## How To Use The KB Well

The detailed design is defined in
[`kb-operating-model.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/kb-operating-model.md).

Recommended operating model:

### Curated Layers

Not all KB content should be treated equally.

Use four layers:

- **Canonical rules**: provider architecture, validation rules, schemas, checkpoint rules
- **Operational references**: prompts, post-production references, scripts, templates
- **Case studies**: prior films, audits, postmortems
- **Raw archive**: PDFs, older notes, supporting material

### Retrieval By Phase

The orchestrator should select KB subsets per phase:

- Development phase → narrative, treatment, theme, structure references
- Pre-production phase → character, environment, reference-image, shot-bible references
- Generation phase → provider, prompt, checkpoint, cost, fallback references
- QC phase → rubric, flow, output, continuity, artifact-quality references
- Post phase → assembly, audio, grading, manifest references

### Retrieval By Agent

Each narrow expert agent should have a small approved KB domain.

Examples:

- `dialogue-agent` should not receive provider internals
- `provider-planning-agent` should not receive all thematic writing notes
- `continuity-validator` should receive continuity ledger rules and flow-validation material

This keeps agents sharp and reduces noisy context.

## External Repo Learnings

I cloned and reviewed these comparison repos under `~/external-projects/`:

- `~/external-projects/agentic-drama-pipeline`
- `~/external-projects/ai-drama-engine-demo`
- `~/external-projects/VEO.IO`

### 1. `agentic-drama-pipeline`

Useful patterns:

- simple, inspectable multi-agent decomposition
- typed schemas for seed, characters, shots, prompts, and continuity output
- clean workflow runner that produces both human-readable and structured artifacts

Takeaway:
This is a good model for **clarity of contracts** between agents, but it is too lightweight
for studio-grade production and does not yet model expensive generation, review gates,
or long-running orchestration.

### 2. `ai-drama-engine-demo`

Useful patterns:

- closer to an actual production chain
- explicit reference-image handling
- face-consistency checking
- assembled delivery artifacts and quality reports
- practical “internal review vs publishable” thinking

Takeaway:
This is strong on **operational realism** and **quality reporting**, but it is still more
pipeline-engine than studio operating system. It is also more vertical and implementation-led
than graph-led.

### 3. `VEO.IO`

Useful pattern:

- product/platform framing rather than single-run script framing

Takeaway:
This reinforces that the long-term shape should be a **platform with orchestration,
state, review, and operator interfaces**, not only a generation backend.

## Direction

The new project should combine:

- the **discipline and lessons** of your existing film-production skill
- the **typed workflow clarity** of `agentic-drama-pipeline`
- the **practical QC and assembly realism** of `ai-drama-engine-demo`
- the **platform mindset** suggested by `VEO.IO`

## Core Creative Priorities

This system should optimize for four things above all:

### 1. Creative Writing Quality

The pipeline should not behave like a prompt expander. It should function like a
serious writers' room.

Creative-writing goals:

- strong loglines and compelling treatments
- scene-level dramatic intent
- character voice consistency
- emotional progression across scenes
- thematic coherence
- rewrites driven by critique, not random regeneration

The writing system should include dedicated agents such as:

- concept developer
- story architect
- screenwriter
- dialogue doctor
- theme and symbolism reviewer
- continuity editor

### 2. Organization Of Final Results

Every phase should leave behind clear, reviewable, reusable outputs.

The system should produce organized artifacts, not scattered files.

Required organization principles:

- one canonical artifact per phase
- stable naming and versioning
- clear folders for narrative, visual, generation, QC, and delivery
- review packages prepared automatically for human inspection
- summary views for both high-level progress and shot-level detail

### 3. Validation At Every Layer

Validation should happen at multiple granularities, not only after generation.

Required validation layers:

- idea and concept validation
- treatment and script validation
- scene and beat validation
- character/reference validation
- shot-bible and prompt validation
- clip-level output validation
- scene-level continuity validation
- sequence-level flow validation
- assembly and final delivery validation

### 4. A True Orchestrator Agent

The system needs a top-level orchestrator agent that drives the entire flow.

The orchestrator should:

- own the global state
- decide which specialist agent acts next
- enforce phase gates
- trigger human review interrupts
- request revisions when validation fails
- maintain production priorities: quality, continuity, cost, and completeness
- produce executive summaries for the operator

## Agent Design Principle

The detailed agent relationship model is defined in
[`agent-architecture.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/agent-architecture.md).

This system should prefer **many small expert agents** over a handful of large,
blurred multi-purpose agents.

That means:

- each agent owns one narrow responsibility
- each agent has a clear input contract and output contract
- agents should be easy to validate independently
- reviewer agents should be separate from creator agents
- orchestration complexity belongs in the orchestrator, not inside each specialist

Bad pattern:

- one “script agent” that tries to do structure, dialogue, pacing, continuity, and theme all at once

Preferred pattern:

- one agent for structure
- one for scene beats
- one for dialogue
- one for thematic reinforcement
- one for continuity review
- one for pacing review

Every agent prompt should follow the RCTCO framework documented in
[`prompt-framework.md`](/Users/ghassan/my-projects/film-pipeline-langgraph/film-knowledge-base/prompt-framework.md):

- Role
- Core Task
- Context
- Constraints
- Output Format

This gives small agents sharper boundaries and makes their outputs easier to validate.

## Target Product

Build a **LangGraph Film Studio** with three layers.

### Layer 1. Studio Brain

This is the LangGraph orchestration layer, led by the **Orchestrator Agent**.

It owns:

- global film state
- phase routing
- review interrupts
- retry/escalation policy
- artifact registry
- budget/status ledger
- final arbitration between specialist agents
- operator-facing progress summaries

### Layer 2. Specialist Agent Teams

Each phase has dedicated agents, with reviewer agents separate from writer/maker agents.

Each team should itself be made of small-domain experts.

Suggested teams:

- Development team: concept, logline, treatment, structure, theme
- Screenwriting team: scenes, beats, dialogue, pacing
- Directing team: shot design, continuity, camera language
- Visual development team: characters, wardrobe, locations, style bible
- Production team: prompts, references, model/provider planning, generation scheduling
- QC team: script review, continuity review, prompt review, output review, assembly review
- Post team: assembly, transitions, audio, grading, delivery manifests

Example specialist agents:

- `logline-agent`
- `treatment-agent`
- `story-structure-agent`
- `scene-beat-agent`
- `dialogue-agent`
- `theme-agent`
- `character-arc-agent`
- `continuity-ledger-agent`
- `shot-design-agent`
- `camera-language-agent`
- `reference-brief-agent`
- `character-reference-agent`
- `environment-reference-agent`
- `prompt-composition-agent`
- `prompt-readiness-validator`
- `clip-validator`
- `scene-flow-validator`
- `continuity-validator`
- `assembly-validator`
- `delivery-validator`

### Layer 3. MCP Operator Surface

This is the interface OpenClaw talks to.

It should expose tools like:

- `create_film_project`
- `submit_idea`
- `get_current_phase`
- `get_film_state`
- `get_orchestrator_summary`
- `review_phase_artifacts`
- `approve_phase`
- `request_revision`
- `list_shots`
- `inspect_shot`
- `inspect_scene`
- `inspect_reference`
- `inspect_continuity_report`
- `regenerate_shot_plan`
- `assemble_cut`
- `export_review_package`

## Human-In-The-Loop Model

Human review should be mandatory after each major phase, not optional.

Required approval gates:

1. Concept approval
2. Treatment approval
3. Script approval
4. Shot bible approval
5. Character/environment reference approval
6. Prompt readiness approval
7. Batch generation approval
8. Output/QC approval
9. Assembly approval
10. Final delivery approval

LangGraph should use interrupts at these points and persist:

- produced artifacts
- reviewer notes
- approval decision
- revision requests
- phase outcome

## Recommended Graph Shape

Use a **supervisor graph** with subgraphs, not one giant linear chain.

High-level flow:

1. Intake
2. Development
3. Script
4. Pre-production
5. Production planning
6. Generation
7. QC
8. Post-production
9. Delivery

Within each phase, use micro-loops:

- orchestrator decision
- creator agent
- reviewer agent
- synthesizer or supervisor
- human approval interrupt

This gives us controlled iteration without losing state or overspending.

In practice, “creator agent” and “reviewer agent” should usually mean multiple
small agents composed together, not one large worker each.

## Canonical State Model

The system should define a typed state model early. Suggested top-level domains:

- `project`
- `vision`
- `narrative`
- `visual_bible`
- `characters`
- `environments`
- `shot_bible`
- `generation_plan`
- `assets`
- `qc`
- `post_production`
- `budget`
- `approvals`
- `issues`
- `timeline`
- `orchestrator`
- `validation`

Important principle:
The film state is the production bible. Agents do not pass loose prose to each other if a
structured artifact can be passed instead.

Important companion principle:
Agent boundaries should follow artifact boundaries. If two responsibilities produce
different artifacts or are validated differently, they should usually be separate agents.

## Validation Architecture

Validation should be represented as a first-class subsystem, not as scattered checks.

Recommended validation scopes:

### Artifact-Level

- logline quality
- treatment quality
- script quality
- character dossier quality
- environment bible quality
- reference-image quality
- shot prompt readiness

### Modality-Level

Validation should also be separated by what is being judged.

- **text validation**: logline, treatment, scene writing, dialogue, theme, pacing
- **image validation**: reference sheets, character identity, environment clarity, composition
- **camera validation**: shot type, lens logic, framing, movement, cinematic intent
- **scene validation**: dramatic function, visual feasibility, emotional clarity
- **flow validation**: transition logic, continuity, escalation, narrative momentum
- **video validation**: motion quality, temporal stability, prompt adherence, artifacts
- **assembly validation**: sequencing, transitions, audio sync, runtime coherence

### Scene-Level

- scene dramatic clarity
- emotional continuity
- character motivation consistency
- visual feasibility

### Clip-Level

- prompt adherence
- identity preservation
- artifact detection
- environment fidelity
- timing and duration correctness

### Act-Level

- act structure integrity
- escalation and pacing across the act
- character progression within the act
- visual and tonal consistency across the act
- continuity of props, wardrobe, locations, and blocking
- camera-language consistency across scenes in the act
- entry/exit quality between scenes

### Full-Movie-Level

- overall narrative coherence
- thematic unity
- character arc completion
- continuity across all acts
- visual language consistency across the film
- rhythm and pacing of the complete movie
- payoff quality: setups, reversals, climax, ending
- final delivery completeness and festival/readiness standards

### Sequence-Level

- continuity across adjacent clips
- progression of lighting, mood, and action
- continuity of props, wardrobe, and blocking
- transition quality

### Delivery-Level

- assembly completeness
- audio/video sync
- final pacing
- export correctness

## Validation Matrix

The new pipeline should validate on two axes at once:

1. **Scale**
2. **Modality**

### Scale Axis

- artifact
- clip
- scene
- sequence
- act
- full movie
- final delivery

### Modality Axis

- text
- image
- camera
- scene construction
- continuity
- flow
- video output
- assembly

Every important artifact or output should be judged by both:

- what scale it belongs to
- what modality it belongs to

Example:

- a reference sheet is `artifact + image`
- a shot prompt is `artifact + text + camera`
- a generated clip is `clip + video + continuity`
- a transition between two scenes is `sequence + flow + camera`
- act pacing is `act + text + flow`
- the final film is `full movie + flow + continuity + assembly`

## Recommended Validation Families

To keep the system understandable, group validators into families.

### Writing Validators

- logline validator
- treatment validator
- scene-writing validator
- dialogue validator
- theme validator
- pacing validator

### Visual Validators

- character-reference validator
- environment-reference validator
- style-bible validator
- composition validator

### Cinematography Validators

- shot-design validator
- camera-language validator
- lens/framing validator
- movement validator

### Continuity Validators

- clip continuity validator
- scene continuity validator
- act continuity validator
- full-movie continuity validator

### Flow Validators

- scene transition validator
- sequence flow validator
- act flow validator
- full-movie flow validator

### Output Validators

- clip quality validator
- artifact detector
- prompt-adherence validator
- temporal stability validator

### Assembly Validators

- timeline validator
- transition validator
- audio sync validator
- final delivery validator

## Validation Operating Rules

To avoid shallow validation theater, the system should follow these rules:

1. No single validator decides quality for the whole movie.
2. Validators should be narrow experts, like the rest of the agent system.
3. Validation at one level does not replace validation at another level.
4. Human review remains mandatory at major checkpoints.
5. Validation outputs must be structured and stored as artifacts.
6. Failing validation should trigger explicit revision workflows.
7. Act-level and full-movie validators should review accumulated context, not isolated fragments.

## Suggested Review Gates By Level

Suggested mandatory review packages:

- **Clip review package**: prompt, references, generated clip, continuity notes, QC report
- **Scene review package**: scene text, scene references, shot group, transition notes, scene QC
- **Act review package**: ordered scenes, act pacing report, continuity ledger slice, act QC
- **Movie review package**: full outline, full continuity report, style-consistency report, movie QC

This ensures the human is reviewing the right granularity for the decision being made.

## Artifact Organization

The system should have a formal artifact model and storage structure.

Suggested categories:

- `01-vision/`
- `02-development/`
- `03-script/`
- `04-visual-dev/`
- `05-shot-bible/`
- `06-generation-plan/`
- `07-generated-assets/`
- `08-validation/`
- `09-post/`
- `10-delivery/`

Every artifact should carry metadata:

- phase
- version
- status
- parent artifact
- validation result
- approval status
- generated_by
- reviewed_by

## What To Preserve From The Current Skill

- provider-agnostic design
- validation gates
- checkpointing
- cost-awareness
- no hidden retries on expensive generation
- phase outputs as durable artifacts
- continuity/state thinking
- post-production as a first-class phase
- critique-driven iteration

## What To Change

- move from skill/protocol language to graph/runtime architecture
- turn validation docs into executable graph subflows
- separate “creative drafting” from “review and approval”
- formalize artifact schemas beyond `film-profile.json`
- add operator-facing MCP tools from day one
- design for resumability, inspectability, and conversational control
- model phase status and approvals as state, not comments
- make the orchestrator agent explicit rather than implied
- elevate artifact organization to a core design concern

## Missing Capabilities To Add

The current vision is strong, but several additions would make the system feel much more
like a real studio.

### 1. Film Constitution

Create a top-level artifact that defines the non-negotiable creative truth of the film.

Suggested contents:

- theme
- tone
- emotional promise
- pacing philosophy
- visual language
- camera philosophy
- character truth rules
- taboo mistakes to avoid

Purpose:
This gives all agents a shared creative spine and prevents drift in taste and intent.

### 2. Rich Continuity Ledger

The continuity ledger should go beyond simple `state_in` and `state_out`.

It should track:

- props
- wardrobe
- injuries and physical condition
- emotional state
- relationship state
- geography and spatial logic
- time of day
- weather
- unresolved plot threads
- visual anchors

Purpose:
This improves scene-to-scene, act-to-act, and full-movie consistency.

### 3. Scene Intent Sheets

Each scene should have a concise intent artifact.

Suggested contents:

- why the scene exists
- what changes in the scene
- who wants what
- conflict source
- emotional target for the audience
- visual concept
- generation risk level

Purpose:
This prevents scenes from becoming visually polished but narratively empty.

### 4. Camera Language System

Create a reusable cinematic grammar instead of ad hoc camera instructions.

Suggested domains:

- tension framing
- intimacy framing
- revelation framing
- movement rules
- stillness rules
- lens logic
- composition patterns
- transition language

Purpose:
This gives the film a consistent directorial voice.

### 5. Reference Strategy Planner

The system should decide reference strategy deliberately, not shot by shot in isolation.

It should determine:

- where hard identity references are required
- where style references are enough
- where re-anchors are needed
- where references create moderation/provider risk
- where synthetic references vs real references are safer

Purpose:
This reduces drift while also reducing avoidable provider failures.

### 6. Creative Risk Register

Add a planning artifact for known hard-generation scenarios.

Examples:

- crowds
- combat
- transformations
- children
- water
- animals
- surreal transitions
- multi-character blocking
- complex hand interactions

Purpose:
The orchestrator can adapt strategy before spending money on fragile shots.

### 7. Narrative Density Validator

Add a validator that checks whether each scene and shot earns its place.

It should ask:

- does this advance plot, character, or theme?
- is this visually repetitive?
- is this emotional beat necessary?
- could this be compressed or merged?

Purpose:
This protects the movie from becoming long, expensive, and empty.

### 8. Act Architect

Add an act-level specialist agent, not only act-level validation.

Responsibilities:

- act structure
- escalation design
- pacing within the act
- act opening/closing strength
- balance across scenes

Purpose:
Many films fail because acts are weak even when individual scenes are decent.

### 9. Full-Movie Payoff Validator

Add a top-level validator for long-range narrative success.

It should check:

- setup/payoff integrity
- motif recurrence
- character arc completion
- climax quality
- ending fulfillment
- thematic closure

Purpose:
This catches failures that no clip-level or scene-level validator can detect.

### 10. Review Package Generator

Every review gate should automatically produce a human-ready package.

Suggested contents:

- executive summary
- artifacts under review
- changes since previous version
- key risks
- validation summary
- orchestrator recommendation

Purpose:
Human review becomes faster, clearer, and more reliable.

### 11. Failure Memory System

Beyond the KB, keep structured examples of failures and recoveries.

Examples:

- drift cases
- provider moderation failures
- continuity failures
- prompt patterns that caused problems
- successful mitigation strategies

Purpose:
This turns operational pain into reusable intelligence for later projects.

### 12. Production Strategy Layer

Before generation, classify what deserves the highest production investment.

Suggested decisions:

- premium shots
- acceptable fallback shots
- stylized substitutions
- static or limited-motion alternatives
- scenes that can be implied instead of shown

Purpose:
This protects budget and creative focus.

### 13. Delivery Modes

Support multiple final-output modes, not only one “final movie.”

Suggested modes:

- internal review cut
- director review cut
- social short-drama cut
- festival cut
- investor/pitch package

Purpose:
Different stakeholders need different forms of the result.

## Highest-Value Additions First

If we want maximum leverage early, prioritize:

1. Film constitution
2. Rich continuity ledger
3. Scene intent sheets
4. Camera language system
5. Review package generator

These five additions would improve creativity, consistency, and operator control immediately.

## Proposed MVP Scope

The first version should **not** try to generate the final movie immediately.
It should prove the studio architecture.

Recommended MVP:

1. Idea intake to approved treatment
2. Treatment to approved script
3. Script to approved shot bible
4. Shot bible to approved visual/reference package
5. Validation pipeline for scenes, references, and continuity
6. MCP-first interface for project control, review, approval, revision, and inspection

This gives a usable studio pre-production system before high-cost generation is added.

## Phase Plan For The Project

### Phase A. Foundation

- define core state schemas
- define artifact schemas
- define approval schema
- define issue/revision schema
- define MCP tool contracts first

### Phase B. Studio Graph

- build supervisor graph behind the MCP contract
- build phase subgraphs
- add interrupts and resume points
- persist all phase artifacts and decisions

### Phase C. Review System

- human approval workflow
- reviewer-agent workflow
- revision request workflow
- audit trail per phase

### Phase D. Production Extensions

- provider adapters
- reference generation integration
- shot generation orchestration
- QC and post-production automation

## Strategic Recommendation

Do **not** start by porting the old skill 1:1 into LangGraph.

Instead:

1. extract the existing skill into formal schemas and artifacts
2. build the approval-aware graph around those artifacts
3. implement the graph behind those MCP tools
4. prove generation flow with a mock provider
5. only then connect expensive generation providers

That path preserves your best production lessons while avoiding another script-heavy pipeline.

## Bottom Line

The right vision is:

> a human-supervised LangGraph film studio with typed state, specialist agent teams,
> durable review gates, strong artifact organization, deep creative-writing support,
> multi-level validation, and an MCP-first operator interface guided by a central orchestrator agent

not:

> a single autonomous generator that runs from idea to MP4 without supervision

The current skill is the right **knowledge foundation**. The next project must turn it into
the right **runtime architecture**.
