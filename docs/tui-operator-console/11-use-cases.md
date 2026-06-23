# Use Case Catalog

## Purpose

This file turns the TUI idea into a concrete use-case set that can drive:

- service design
- gateway methods
- screen design
- test scenarios
- phased implementation decisions

It is intentionally broader than a pure operator console. The TUI must stay usable for a
film creator who is actively shaping the project, not only approving backend steps.

## Design Goal

The TUI should be flexible for two closely related user modes:

- `studio_operator`
- `film_creator`

The same product should support both without forking into separate applications.

## Persona Modes

## 1. Studio Operator

Primary concern:

- state visibility
- approvals
- blockers
- provider health
- rollback and recovery

## 2. Film Creator

Primary concern:

- creative artifacts
- revision cycles
- comparing alternatives
- steering the film without fighting tooling

## Shared UX Principle

The TUI should adapt emphasis, not architecture.

That means:

- same backend services
- same durable state
- same screens where possible
- different defaults, shortcuts, and summaries by mode

Example:

- operator mode lands on `Dashboard`
- creator mode lands on `Review` or `Artifacts`

This should be independent from project workflow mode:

- `manual`
- `hybrid`
- `automatic`

Persona mode changes presentation emphasis.
Workflow mode changes backend gate behavior.

## Use-Case Format

Each use case contains:

- goal
- primary actor
- preconditions
- trigger
- main flow
- alternate flows
- postconditions
- required backend capabilities
- TUI implications

## UC-01 Create Project

### Goal

Create a new film project with the right runtime mode, workflow mode, and profile stack.

### Primary Actor

- studio_operator
- film_creator

### Preconditions

- TUI is running
- backend is reachable

### Trigger

- user selects `new project`

### Main Flow

1. user enters title, slug, runtime mode, workflow mode, and optional profile choices
2. TUI validates obvious input errors
3. gateway calls project creation service
4. service creates project state and initial persistence
5. TUI opens the new project workspace

### Alternate Flows

- invalid project id or slug
- runtime mode conflicts with server mode
- requested workflow override not allowed by policy
- required real-provider credentials missing

### Postconditions

- project exists
- active project is set
- initial dashboard is available

### Required Backend Capabilities

- project creation service
- mode/profile resolution
- workflow-mode resolution
- runtime validation

### TUI Implications

- guided project form
- clear mock vs real mode labeling
- clear manual vs hybrid vs automatic labeling
- good error messages for profile conflicts

## UC-01a Change Workflow Mode

### Goal

Change a project's workflow mode without changing its whole profile stack.

### Primary Actor

- studio_operator
- film_creator

### Preconditions

- project exists
- policy allows workflow override

### Trigger

- user selects `change workflow mode`

### Main Flow

1. TUI shows current workflow mode and source
2. user selects `manual`, `hybrid`, or `automatic`
3. gateway calls workflow update service
4. service validates policy
5. project state persists the new active mode
6. TUI refreshes dashboard and review behavior

### Alternate Flows

- project policy forbids override
- selected mode conflicts with environment or approval policy

### Postconditions

- active workflow mode is updated and visible

### Required Backend Capabilities

- workflow mode read service
- workflow mode update service
- policy validation

### TUI Implications

- visible workflow-mode switcher
- explanation of mode source and effect

## UC-02 Open And Triage Projects

### Goal

Quickly identify which project needs attention.

### Primary Actor

- studio_operator

### Preconditions

- one or more projects exist

### Trigger

- app startup
- explicit project list navigation

### Main Flow

1. TUI loads project summaries
2. user scans status, phase, blockers, and review needs
3. user opens the highest-priority project

### Alternate Flows

- no projects exist
- one project is unreadable or partially broken

### Postconditions

- selected project becomes active in the workspace

### Required Backend Capabilities

- list projects
- bulk summary or efficient summary composition

### TUI Implications

- project rail
- sort/filter/search
- urgency indicators

## UC-03 Understand Current State

### Goal

Understand what the system is doing, why, and what actions are available.

### Primary Actor

- studio_operator
- film_creator

### Preconditions

- active project exists

### Trigger

- dashboard open
- project switch
- refresh

### Main Flow

1. TUI loads project summary
2. TUI loads orchestrator summary
3. user sees current phase, next action, route reason, blockers, and active review state
4. user sees the active workflow mode and whether the current gate is manual, auto-passed, or escalated

### Alternate Flows

- project is stalled
- project is blocked on provider or budget
- project has no current phase yet

### Postconditions

- user understands what should happen next

### Required Backend Capabilities

- project summary service
- orchestrator summary service
- blockers and next-actions service
- workflow-mode summary

### TUI Implications

- dashboard summary cards
- explicit blocked vs eligible actions
- route reason visible at top level
- workflow mode always visible

## UC-03a Review Project Structure And Act Flow

### Goal

Understand the film at project and act scope before making local scene changes.

### Primary Actor

- film_creator
- studio_operator

### Preconditions

- structural artifacts exist

### Trigger

- user opens `Structure`

### Main Flow

1. TUI loads project structure summary
2. user reviews overall runtime, act balance, and structural issues
3. user selects an act
4. TUI shows act detail, pacing, and scene sequence summary
5. user decides whether strategic change is needed

### Alternate Flows

- project structure incomplete
- act mapping unavailable

### Postconditions

- user understands the film at strategic structural scope

### Required Backend Capabilities

- project structure summary
- act listing
- act detail service
- structure issue summary

### TUI Implications

- structure workspace
- act navigator
- runtime and pacing indicators

## UC-04 Review A Phase Decision Package

### Goal

Review the current phase as a decision package, not a raw artifact dump.

### Primary Actor

- studio_operator
- film_creator

### Preconditions

- phase has produced reviewable candidate artifacts

### Trigger

- review queue selection
- dashboard action

### Main Flow

1. TUI loads review workspace
2. user sees candidate artifacts, approved baselines, diffs, validation, issues, and recommendation
3. user drills into the necessary artifacts
4. user decides whether to approve, revise, escalate, or defer

### Alternate Flows

- review package incomplete
- blocking issues prevent approval
- candidate artifacts are missing expected diffs

### Postconditions

- user has enough information to decide

### Required Backend Capabilities

- review workspace service
- artifact diff service
- validation summary service
- gate-decision summary

### TUI Implications

- review-first layout
- low-friction drill-down into artifacts
- recommendation and risk summary always visible
- why this gate is manual or automatic must be visible

## UC-05 Approve Phase

### Goal

Approve a phase and resume the pipeline safely.

### Primary Actor

- studio_operator

### Preconditions

- project is awaiting review
- approval is allowed

### Trigger

- user selects `approve`

### Main Flow

1. TUI confirms the approval intent
2. gateway calls approval service
3. service resumes graph or advances phase
4. service persists state, audit, and checkpoint
5. TUI refreshes summary and review state

### Alternate Flows

- approval blocked by unresolved issues
- checkpoint creation fails
- graph resume fails

### Postconditions

- approval is durable
- phase progression is visible

### Required Backend Capabilities

- approval service
- checkpoint creation
- audit recording
- phase resume logic
- workflow policy evaluation

### TUI Implications

- confirm dialog with explicit consequence text
- read-after-write refresh

## UC-06 Request Revision

### Goal

Request targeted revision with notes that remain durable and visible.

### Primary Actor

- studio_operator
- film_creator

### Preconditions

- reviewable phase is active

### Trigger

- user selects `request revision`

### Main Flow

1. user writes revision notes
2. TUI optionally structures notes into fields such as `preserve`, `change`, `blocking reason`
3. gateway calls revision service
4. service persists the revision request
5. orchestrator routes back into repair/revision flow
6. TUI refreshes pending revisions and review-cycle state

### Alternate Flows

- note is empty and policy requires rationale
- revision request duplicates an unresolved existing request

### Postconditions

- revision is durable
- approval is blocked until revision resolves

### Required Backend Capabilities

- revision request service
- review-cycle state update
- audit recording
- workflow policy evaluation

### TUI Implications

- good revision editor
- visible history of pending and resolved revisions

## UC-07 Inspect Creative Artifacts Deeply

### Goal

Read and compare the film’s creative artifacts comfortably in terminal form.

### Primary Actor

- film_creator

### Preconditions

- artifacts exist

### Trigger

- artifact browser
- review drill-down

### Main Flow

1. user browses artifacts by phase or type
2. user opens one artifact
3. TUI formats it for reading
4. user compares versions or related baselines

### Alternate Flows

- artifact body is too large
- artifact type has no specialized renderer yet

### Postconditions

- user can understand the artifact without leaving the TUI

### Required Backend Capabilities

- artifact listing
- artifact inspection
- version compare

### TUI Implications

- reader view
- metadata side panel
- search within artifact
- default renderer fallback

## UC-07a Navigate Scene By Scene

### Goal

Move through the script or scene list one scene at a time with useful local context.

### Primary Actor

- film_creator
- studio_operator

### Preconditions

- scene-oriented artifacts exist

### Trigger

- user opens `Scenes`
- user jumps from review or artifact view into a scene

### Main Flow

1. TUI loads scene list
2. user selects a scene
3. TUI shows scene detail, scene-specific issues, and comparison context
4. user moves to next or previous scene
5. user repeats until the relevant section of the film is reviewed

### Alternate Flows

- scene data is incomplete
- scene has no specialized detail renderer yet

### Postconditions

- user can review the film as a sequence of scenes, not only as one large script artifact

### Required Backend Capabilities

- scene listing
- scene detail service
- scene issue lookup

### TUI Implications

- scene navigator rail
- previous/next scene navigation
- scene status indicators

## UC-07b Request Improvement For One Scene

### Goal

Apply targeted creative improvement to one scene without forcing a vague whole-artifact
revision.

### Primary Actor

- film_creator

### Preconditions

- a scene is selected
- revision is allowed

### Trigger

- user selects `request scene revision`

### Main Flow

1. user opens a scene
2. user reviews its issues and current text
3. user enters targeted revision guidance
4. gateway calls scene revision service
5. service persists the request and computes impact scope
6. TUI shows whether the change is scene-local or affects downstream artifacts
7. revised candidate scene becomes available for comparison

### Alternate Flows

- requested scene change conflicts with approved upstream constraints
- change requires broader artifact regeneration

### Postconditions

- targeted scene revision is durable and understandable in scope

### Required Backend Capabilities

- scene revision service
- scene impact preview
- scene compare service

### TUI Implications

- scene-focused revision editor
- impact preview before or after submission
- compare revised scene against approved baseline

## UC-07c Navigate Reference Images And Asset Metadata

### Goal

Move through reference images and other metadata-rich assets with enough detail to evaluate
and steer them.

### Primary Actor

- film_creator
- studio_operator

### Preconditions

- metadata-rich assets exist

### Trigger

- user opens asset navigator
- user jumps from scene or review into related asset

### Main Flow

1. TUI loads asset family list
2. user filters to references or another family
3. user selects one asset
4. TUI shows metadata, validation, dependencies, and related usage
5. user moves through similar assets and compares them as needed

### Alternate Flows

- asset metadata incomplete
- asset has no specialized metadata renderer yet

### Postconditions

- user can understand the asset in isolation and in project context

### Required Backend Capabilities

- asset listing
- asset detail service
- asset issue lookup
- dependency lookup

### TUI Implications

- asset navigator
- metadata detail panel
- related-usage jump links

## UC-07d Request Enhancement For One Asset

### Goal

Apply a targeted improvement request to one reference image or other asset-backed metadata
record.

### Primary Actor

- film_creator

### Preconditions

- an asset is selected
- enhancement is allowed by policy

### Trigger

- user selects `request enhancement`

### Main Flow

1. user inspects asset metadata and issues
2. user writes targeted enhancement guidance
3. gateway calls asset enhancement service
4. service persists the request and computes impact scope
5. TUI shows whether the enhancement is local or has broader dependencies
6. new candidate asset or metadata version appears for comparison

### Alternate Flows

- enhancement conflicts with approved constraints
- enhancement implies broad downstream regeneration

### Postconditions

- targeted asset enhancement is durable and scoped visibly

### Required Backend Capabilities

- asset enhancement service
- asset impact preview
- asset compare service

### TUI Implications

- asset enhancement editor
- metadata compare view
- dependency-aware impact preview

## UC-07e Request Project-Level Or Act-Level Structural Improvement

### Goal

Apply targeted structural changes at project or act scope, such as improving flow,
strengthening pacing, or changing duration.

### Primary Actor

- film_creator

### Preconditions

- project structure is available

### Trigger

- user selects `request structural improvement`
- user selects `increase duration` or `reduce duration`

### Main Flow

1. user opens structure workspace
2. user selects scope: project or act
3. user reviews current structural issues and runtime state
4. user enters targeted guidance
5. gateway calls structure workflow service
6. service persists request and computes impact scope
7. TUI shows whether the change affects acts, scenes, prompts, or downstream assets
8. revised candidate structure becomes available for comparison

### Alternate Flows

- requested duration change conflicts with policy or constraints
- structural change implies broad downstream invalidation

### Postconditions

- structural improvement request is durable and scoped visibly

### Required Backend Capabilities

- structure improvement service
- duration change service
- structure impact preview
- structure compare service

### TUI Implications

- structure improvement editor
- duration-change controls
- broad-impact preview

## UC-08 Compare Candidate Vs Approved Baseline

### Goal

See exactly what changed and whether the change should move downstream.

### Primary Actor

- studio_operator
- film_creator

### Preconditions

- both candidate and approved refs exist

### Trigger

- review workspace
- artifact comparison command

### Main Flow

1. user selects compare
2. TUI loads baseline and candidate references
3. diff summary and metadata differences are shown
4. user uses this evidence in approval or revision decision

### Alternate Flows

- approved baseline missing
- diff service cannot produce structured diff for this artifact type

### Postconditions

- differences are explicit

### Required Backend Capabilities

- version comparison service
- artifact metadata lookup

### TUI Implications

- side-by-side or stacked compare mode
- concise diff summary first

## UC-09 Investigate Validation Issues

### Goal

Understand what is blocking progress and why.

### Primary Actor

- studio_operator
- film_creator

### Preconditions

- validation results exist

### Trigger

- review package
- validation screen
- blocker card

### Main Flow

1. user opens validation workspace
2. blocking issues are separated from warnings
3. user inspects validator outputs and consensus
4. user decides whether to revise, escalate, or approve with known risk when policy allows

### Alternate Flows

- validators disagree
- issue points to missing upstream artifact

### Postconditions

- user understands the blocking criteria

### Required Backend Capabilities

- validation workspace service
- issue listing
- consensus explanation

### TUI Implications

- severity-first display
- links from issue to artifact

## UC-10 Monitor Provider Health And Generation State

### Goal

Operate the pipeline safely during generation and provider incidents.

### Primary Actor

- studio_operator

### Preconditions

- providers registered or generation active

### Trigger

- provider screen
- health alert

### Main Flow

1. TUI shows provider statuses and active generation state
2. user opens degraded provider details
3. user sees recent failures, health classification, and safe-to-continue context
4. user chooses appropriate next action

### Alternate Flows

- no providers configured
- provider health unknown
- multiple providers degraded simultaneously

### Postconditions

- provider situation is understood

### Required Backend Capabilities

- provider status service
- generation overview service
- failure explanation

### TUI Implications

- operational dashboard treatment
- health strip in global header

## UC-10a Understand Why The System Waited Or Auto-Continued

### Goal

Understand why a step required human review or continued automatically.

### Primary Actor

- studio_operator
- film_creator

### Preconditions

- active or recent gate decision exists

### Trigger

- user inspects workflow-mode details
- user opens current gate explanation

### Main Flow

1. user opens gate decision detail
2. TUI shows workflow mode, gate class, policy decision, and reason
3. user understands whether the gate was manual, hybrid-routed, or automatic

### Alternate Flows

- gate-decision explanation unavailable

### Postconditions

- workflow behavior is understandable

### Required Backend Capabilities

- gate-decision explanation service

### TUI Implications

- workflow explanation panel

## UC-11 Preview Rollback Impact

### Goal

Understand blast radius before rollback.

### Primary Actor

- studio_operator

### Preconditions

- checkpoints or artifact versions exist

### Trigger

- rollback or compare action

### Main Flow

1. user selects checkpoint or artifact target
2. TUI loads invalidation preview
3. user sees revert scope and downstream invalidation
4. user decides whether to proceed

### Alternate Flows

- invalidation graph incomplete
- rollback target no longer exists

### Postconditions

- rollback consequences are visible before mutation

### Required Backend Capabilities

- checkpoint listing
- invalidation preview
- version comparison

### TUI Implications

- confirmation must include blast radius

## UC-12 Execute Rollback

### Goal

Perform rollback safely and durably.

### Primary Actor

- studio_operator

### Preconditions

- valid rollback target exists
- user has reviewed invalidation preview

### Trigger

- user confirms rollback

### Main Flow

1. TUI requests confirmation
2. gateway calls rollback service
3. service executes rollback and persists audit/checkpoint effects
4. TUI refreshes project state

### Alternate Flows

- rollback blocked by policy
- rollback partially fails

### Postconditions

- rollback result is durable and visible

### Required Backend Capabilities

- rollback service
- audit recording
- post-rollback state recomputation

### TUI Implications

- destructive-action UX
- immediate state refresh

## UC-13 Follow Audit Trail

### Goal

See what happened, who did it, and why.

### Primary Actor

- studio_operator
- film_creator

### Preconditions

- audit events exist

### Trigger

- audit screen
- detail drill-down

### Main Flow

1. user opens audit feed
2. user filters by time, action, or phase
3. user opens relevant event
4. user follows links to artifacts or decisions

### Alternate Flows

- no audit data
- audit event references missing artifact

### Postconditions

- timeline is understandable

### Required Backend Capabilities

- audit feed service
- decision explanation services

### TUI Implications

- timeline reader
- linked navigation

## UC-14 Support Film-Creator Steering

### Goal

Allow a film creator to stay close to the creative process, not just the approvals.

### Primary Actor

- film_creator

### Preconditions

- creative artifacts exist or are being developed

### Trigger

- creator mode enabled
- creative review workflow

### Main Flow

1. creator opens project
2. TUI emphasizes creative artifacts, diffs, notes, and revision history
3. creator navigates narrative, character, visual, and shot artifacts
4. creator submits targeted revision guidance or approves creative direction

### Alternate Flows

- creator wants less system detail
- creator wants to focus on one artifact family only

### Postconditions

- creator can steer the film without backend complexity dominating the experience

### Required Backend Capabilities

- same shared services as operator mode

### TUI Implications

- mode-specific landing view
- denser artifact reading tools
- calmer presentation of technical details

## UC-15 Work Across Multiple Projects

### Goal

Handle several films without losing context.

### Primary Actor

- studio_operator

### Preconditions

- multiple active projects exist

### Trigger

- daily triage

### Main Flow

1. user sorts projects by urgency or review state
2. user cycles through review queue
3. TUI preserves lightweight local context per project

### Alternate Flows

- too many projects for simple list rendering

### Postconditions

- multi-project operation is manageable

### Required Backend Capabilities

- efficient project summary service
- optional operator inbox later

### TUI Implications

- fast switching
- per-project cached view state only

## Cross-Cutting Flexibility Requirements

These apply to all use cases.

### 1. Role-flexible presentation

The same backend should support operator-heavy and creator-heavy workflows.

### 2. Readable long-form content

Scripts, treatments, constitutions, and notes must be readable in terminal form.

### 3. Safe mutation model

Any costly or destructive action must require confirmation and backend persistence before UI
state updates.

### 4. Candidate vs approved clarity

The user must always know whether they are looking at draft output or approved baseline.

### 5. Degraded-mode usability

If part of the backend is unavailable, the TUI should still provide useful inspection where
possible.

## Mapping To Initial Services

The first service set should support these use cases directly:

- `ProjectService`
  - UC-01, UC-01a, UC-02, UC-03, UC-15
- `OrchestrationService`
  - UC-03, UC-05, UC-06, UC-09, UC-10a
- `StructureWorkflowService`
  - UC-03a, UC-07e
- `ReviewService`
  - UC-04, UC-05, UC-06, UC-08, UC-14
- `ArtifactService`
  - UC-07, UC-07a, UC-07c, UC-08, UC-14
- `SceneWorkflowService`
  - UC-07a, UC-07b
- `AssetWorkflowService`
  - UC-07c, UC-07d
- `ValidationService`
  - UC-09
- `ProviderService`
  - UC-10
- `CheckpointService`
  - UC-11, UC-12
- `WorkflowPolicyService`
  - UC-01, UC-01a, UC-03, UC-04, UC-05, UC-06, UC-10a
- `AuditService`
  - UC-13

## Mapping To Initial Screens

- `Dashboard`
  - UC-02, UC-03, UC-10, UC-10a, UC-15
- `Review`
  - UC-04, UC-05, UC-06, UC-08, UC-14
- `Structure`
  - UC-03a, UC-07e
- `Scenes`
  - UC-07a, UC-07b
- `Artifacts`
  - UC-07, UC-07c, UC-07d, UC-08, UC-14
- `Validation`
  - UC-09
- `Providers`
  - UC-10
- `Checkpoints`
  - UC-11, UC-12
- `Audit`
  - UC-13

Possible later screen or modal:

- `Project Settings`
  - UC-01a

## Use Cases To Delay

Do not make these V1-critical:

- direct artifact authoring inside TUI
- multi-user collaborative live editing
- plugin marketplace behavior inside TUI
- full push-event architecture

Those can come later after the operator and creator workflows are stable.
