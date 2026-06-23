# End-To-End User Flows

## Purpose

This file defines a small set of complete user journeys that the TUI must support well.

These are more valuable than isolated screen ideas because they force correctness across:

- project setup
- navigation
- state refresh
- human decisions
- backend persistence
- failure handling

If these flows feel coherent, the TUI is likely shaped correctly.

## Why These Flows

The product needs to support both:

- film-creator-led work
- operator-led studio work

It also needs to support all three workflow modes:

- `manual`
- `hybrid`
- `automatic`

So the E2E flows below deliberately mix:

- creator focus vs operator focus
- creative review vs operational control
- steady-state work vs recovery work

## Flow Format

Each flow contains:

- actor
- mode
- goal
- success criteria
- step-by-step journey
- critical TUI requirements

## Flow 1: Creator-Led Manual Film Development

### Actor

- film_creator

### Mode

- runtime: `mock` or `real`
- workflow: `manual`

### Goal

Create a film project, move through early creative phases, and manually review each major
creative gate.

### Why It Matters

This is the most important flow for proving the TUI is creator-friendly, not just
operator-friendly.

### Journey

1. user opens the TUI
2. user selects `new project`
3. user chooses:
   - runtime mode
   - workflow mode `manual`
   - film-type/profile stack
4. user lands in the new project workspace
5. dashboard shows:
   - current phase
   - workflow mode
   - next action
   - route reason
6. intake/constitution/development outputs are generated
7. graph pauses at a creative review gate
8. TUI moves the user into `Review`
9. user reads:
   - constitution
   - treatment
   - diffs if revisions happened
   - validation notes
10. user requests revision with notes
11. system re-runs and produces new candidate artifacts
12. user compares candidate vs approved baseline
13. user approves the phase
14. system creates checkpoint and advances
15. the same pattern repeats for script and visual-development work

### Success Criteria

- creator can stay mostly in `Review` and `Artifacts`
- workflow mode is obvious at all times
- revision notes feel first-class
- approval feels safe and consequential
- candidate vs approved state is never ambiguous

### Critical TUI Requirements

- strong document reading experience
- low-friction revision flow
- visible workflow mode in header and review package
- excellent compare view for long-form artifacts

## Flow 2: Hybrid Production With Selective Human Gates

### Actor

- film_creator
- studio_operator

### Mode

- runtime: `real`
- workflow: `hybrid`

### Goal

Move quickly through safe steps while still forcing human attention on creative, cost, and
recovery decisions.

### Why It Matters

This is likely the most realistic production mode.

### Journey

1. user opens an active project already in progress
2. dashboard shows workflow mode `hybrid`
3. some low-risk steps auto-continue in the background
4. dashboard and audit show that they auto-continued, with reasons
5. system reaches a script or shot-bible gate
6. TUI marks it as `manual gate under hybrid policy`
7. user opens review workspace
8. user reviews recommendation, validation, and change summary
9. user approves
10. later, generation planning reaches a spend-sensitive gate
11. TUI shows:
   - cost preview
   - provider plan
   - why human approval is required under hybrid policy
12. user approves generation spend
13. generation starts
14. low-risk status refreshes happen automatically
15. QC produces a blocking issue
16. review workspace opens again for human decision

### Success Criteria

- user understands what auto-ran and why
- user understands why some steps still stopped
- hybrid does not feel random

### Critical TUI Requirements

- gate-decision explanation panel
- visible distinction between:
  - auto-passed under policy
  - pending human review
  - escalated due to risk/blocker
- cost and provider info integrated into review flow

## Flow 3: Headless Automatic Run With Human Escalation

### Actor

- studio_operator

### Mode

- runtime: `mock` or `real`
- workflow: `automatic`

### Goal

Run the pipeline headlessly until a blocker or escalation requires intervention.

### Why It Matters

This proves the TUI is still useful even when the human is not in the loop continuously.

### Journey

1. operator creates or opens a project set to `automatic`
2. TUI dashboard shows:
   - automatic workflow mode
   - source of mode
   - current running phase
3. user leaves the project running
4. TUI refreshes high-level state in the background
5. most phases progress without manual gates
6. provider degrades or validation blocks
7. system escalates
8. project rail status changes to `attention required`
9. operator opens the project
10. dashboard explains:
   - what happened
   - why automatic mode stopped
   - what action is needed now
11. operator reviews provider/validation details
12. operator chooses to:
   - approve continuation
   - request revision
   - wait
   - change workflow mode to hybrid or manual

### Success Criteria

- automatic mode does not make the system opaque
- escalations are easy to notice and understand
- operator can intervene without losing context

### Critical TUI Requirements

- strong project-rail triage
- escalation badges
- audit visibility
- workflow-mode switch path from automatic to hybrid/manual

## Flow 4: Rollback And Recovery After A Bad Creative Decision

### Actor

- studio_operator
- film_creator

### Mode

- runtime: `real`
- workflow: `manual` or `hybrid`

### Goal

Recover from an approved-but-wrong creative direction without losing control of downstream
impact.

### Why It Matters

Rollback is where UI trust is won or lost.

### Journey

1. user notices a later-phase problem caused by an earlier approved artifact
2. user opens `Checkpoints`
3. user selects an earlier checkpoint or artifact version
4. TUI shows:
   - target checkpoint
   - artifact versions
   - invalidation preview
   - downstream effects
5. user compares versions
6. user decides rollback is necessary
7. TUI asks for explicit confirmation
8. rollback executes
9. dashboard refreshes
10. audit trail records the operation
11. TUI shows which phases or artifacts now need regeneration or re-review

### Success Criteria

- user sees blast radius before mutation
- rollback feels safe, explicit, and reversible in reasoning
- post-rollback next steps are obvious

### Critical TUI Requirements

- strong checkpoint timeline
- invalidation preview
- compare-before-rollback flow
- post-rollback guidance on what is now stale

## Flow 5: Multi-Project Daily Triage

### Actor

- studio_operator

### Mode

- mixed project modes

### Goal

Work through the day’s highest-priority projects quickly.

### Why It Matters

A good TUI must support operational throughput, not just single-project depth.

### Journey

1. operator opens TUI at start of day
2. project rail or dashboard shows all projects with:
   - current phase
   - workflow mode
   - status
   - blockers
   - pending reviews
3. operator sorts by urgency
4. operator opens first project needing review
5. operator reviews and approves or revises
6. operator returns to queue
7. operator opens a project with provider degradation
8. operator resolves or defers it
9. operator opens a creator-led manual project
10. operator leaves a detailed revision request

### Success Criteria

- project switching is fast
- local per-project UI context is preserved
- queue-based operation feels natural

### Critical TUI Requirements

- project rail with rich summaries
- “next attention item” command
- cached ephemeral UI state per project

## Flow 6: Creator Changes Workflow Mid-Project

### Actor

- film_creator

### Mode

- starts `automatic` or `hybrid`
- changes to `manual`

### Goal

Move from speed-first exploration to tight creative control without rebuilding the project.

### Why It Matters

Creators often want more manual control once the film direction becomes important.

### Journey

1. creator opens project that has been running in `hybrid`
2. creator reviews output and decides to take tighter control
3. creator opens workflow-mode settings
4. TUI shows:
   - current mode
   - source
   - impact of switching
5. creator changes mode to `manual`
6. service persists workflow-mode override
7. dashboard and review screens update
8. next major gate pauses for manual approval
9. creator continues with more detailed review/revision loops

### Success Criteria

- mode switching is understandable
- creator knows what changed operationally
- no hidden profile behavior remains

### Critical TUI Requirements

- workflow-mode settings flow
- explanation of profile default vs project override
- gate behavior changes visible immediately

## Recommended V1 Priority

If the first TUI version supports these four flows well, it will be on the right track:

1. Flow 1: creator-led manual development
2. Flow 2: hybrid production with selective human gates
3. Flow 4: rollback and recovery
4. Flow 5: multi-project daily triage

These cover:

- creation
- review
- revision
- approval
- triage
- recovery

That is the minimum credible product shape.

## Flow 7: Scene-By-Scene Creative Improvement

### Actor

- film_creator

### Mode

- runtime: `mock` or `real`
- workflow: `manual` or `hybrid`

### Goal

Move through the film scene by scene and improve weak scenes with targeted revision requests.

### Why It Matters

This is the clearest proof that the TUI supports real creative work instead of only phase
approvals.

### Journey

1. creator opens a project in script or scene-oriented phase
2. creator opens `Scenes`
3. TUI shows scene navigator with issue badges and candidate/approved status
4. creator selects scene 1
5. creator reads:
   - scene heading
   - action
   - dialogue
   - dramatic purpose
   - scene-specific issues
6. creator moves to scene 2, scene 3, and so on
7. creator finds a weak scene
8. creator opens `request scene revision`
9. creator writes targeted notes such as:
   - improve pacing
   - clarify motivation
   - make dialogue more restrained
10. TUI shows whether the change is scene-local or may affect downstream continuity
11. creator submits the request
12. revised candidate scene appears
13. creator compares revised scene against approved baseline or previous candidate
14. creator either accepts the improvement or requests another pass
15. after several scene-level fixes, creator returns to whole-phase review

### Success Criteria

- scene navigation is fast
- scene context is rich enough for real decisions
- targeted changes feel precise
- the user understands the blast radius of a scene change

### Critical TUI Requirements

- first-class `Scenes` workspace
- previous/next scene navigation
- scene issue panel
- scene revision editor
- scene compare view
- impact preview for scene-specific changes

## Flow 8: Reference Image And Metadata Enhancement

### Actor

- film_creator

### Mode

- runtime: `mock` or `real`
- workflow: `manual` or `hybrid`

### Goal

Navigate reference images and their metadata, then request targeted enhancement for weak
visual references or related records.

### Why It Matters

Visual development depends on reference quality and metadata quality. A creator needs to
steer these assets directly, not only through whole-phase approvals.

### Journey

1. creator opens a project in visual development or shot-planning phase
2. creator opens `Artifacts` or asset navigator
3. TUI filters to `reference images`
4. creator browses reference entries one by one
5. for each entry, TUI shows:
   - metadata
   - quality/validation signals
   - dependencies
   - where the asset is used
6. creator finds a weak reference
7. creator opens `request enhancement`
8. creator writes targeted notes such as:
   - align closer to character identity
   - improve lighting consistency
   - strengthen environmental mood
   - refine metadata tags
9. TUI shows whether the enhancement is local or affects dependent prompts/scenes/shots
10. creator submits the request
11. revised candidate asset or metadata appears
12. creator compares new and old versions
13. creator accepts the improved asset or requests another pass

### Success Criteria

- reference navigation is fast
- metadata is rich enough for real visual decisions
- targeted enhancement feels precise
- asset dependency impact is visible

### Critical TUI Requirements

- first-class asset navigator
- metadata detail panel
- dependency graph or usage panel
- targeted asset enhancement editor
- asset compare view

## Flow 9: Act-Level Flow Repair And Duration Increase

### Actor

- film_creator

### Mode

- runtime: `mock` or `real`
- workflow: `manual` or `hybrid`

### Goal

Inspect the film at act scope, validate flow, and request structural changes such as pacing
improvement or duration increase.

### Why It Matters

This proves the TUI supports strategic storytelling work, not only local scene or asset
adjustment.

### Journey

1. creator opens a project that feels too short or structurally weak
2. creator opens `Structure`
3. TUI shows:
   - target runtime
   - estimated current runtime
   - act list
   - structural issue summary
4. creator selects act 2
5. TUI shows pacing, scene sequence, and act issues
6. creator runs `validate flow`
7. validation highlights weak escalation and rushed transitions
8. creator selects `increase duration`
9. creator requests:
   - add roughly 90 seconds
   - strengthen escalation through act 2
   - preserve current act 1 setup
10. TUI shows impact preview across scenes and downstream planning artifacts
11. creator submits the request
12. revised candidate structure appears
13. creator compares old and new structure
14. creator drills into affected scenes if needed
15. creator accepts the structural revision or requests another pass

### Success Criteria

- project and act structure are readable
- flow validation is actionable
- duration change is easy to request
- the user understands the scope impact of structural changes

### Critical TUI Requirements

- first-class `Structure` workspace
- act navigator
- flow validation view
- duration-change controls
- structure compare view
- cross-links from act to scenes

## What These Flows Imply About The TUI

The TUI should be built around these centers of gravity:

- `Dashboard` for triage and explanation
- `Review` for human decision-making
- `Artifacts` for deep reading and comparison
- `Checkpoints` for safe recovery
- `Providers` for operational control

If the UI drifts into a screen set that does not serve these flows directly, it is probably
becoming over-designed.
