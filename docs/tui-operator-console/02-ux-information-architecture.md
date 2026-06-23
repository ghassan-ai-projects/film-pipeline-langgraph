# UX And Information Architecture

## Recommended Shell Model

Use a persistent multi-pane workspace instead of a wizard.

Recommended top-level areas:

1. Global header
2. Project rail
3. Main workspace
4. Context drawer
5. Command palette
6. Event/status footer

## Global Header

Show:

- active project
- current phase
- runtime mode: `mock` or `real`
- workflow mode: `manual`, `hybrid`, or `automatic`
- provider health summary
- approval queue count
- refresh state

## Project Rail

Purpose:

- switch projects quickly
- expose urgency at a glance

Each project row should show:

- project title or slug
- current phase
- workflow mode
- status badge: `running`, `awaiting review`, `blocked`, `stalled`, `complete`
- blocking issue count
- last updated time

## Main Workspace Tabs

Recommended tabs:

- `Dashboard`
- `Review`
- `Structure`
- `Scenes`
- `Artifacts`
- `Validation`
- `Checkpoints`
- `Providers`
- `Audit`

## Dashboard

This is the default landing screen.

Show:

- current phase card
- workflow mode card
- orchestrator summary
- next action
- eligible actions
- blocked actions with reasons
- review cycle state
- budget snapshot
- provider warnings
- latest artifacts

## Review

This is the most important screen.

Show the review package as a structured decision workspace:

- candidate artifacts under review
- approved baseline refs
- diff summary
- validation summary
- unresolved issues
- risk summary
- orchestrator recommendation
- actions: approve, request revision, escalate, defer

The review area should also allow drilling into scene-by-scene review for script- and
scene-oriented phases.

## Structure

This should be a first-class workspace.

Show:

- project structure summary
- act list
- active act detail
- structure issues
- duration and flow operations

## Scenes

This should be a first-class workspace.

Show:

- scene list
- active scene content
- scene-specific issues
- scene comparison
- scene revision actions

## Artifacts

Capabilities:

- list artifacts by phase or type
- browse metadata-rich asset families such as references, shot rows, and prompt rows
- inspect one artifact in formatted form
- compare versions
- filter by `candidate` vs `approved`
- jump from artifact to scene-level navigation where applicable
- jump from scene to related references and other assets

For text-heavy artifacts, use a reader layout with:

- outline pane
- body pane
- metadata pane

For metadata-rich assets, use:

- asset list
- metadata detail panel
- dependency/usage panel
- actions panel

## Validation

Show:

- latest validation report
- blocking vs non-blocking issues
- validator names
- consensus disagreements
- issue ownership hints

## Checkpoints

Show:

- checkpoint timeline
- checkpoint metadata
- version comparisons
- invalidation report preview
- rollback confirmations

## Providers

Show:

- registered providers
- health status
- active generation batches
- error classifications
- recovery suggestions

## Audit

Show:

- recent tool actions
- graph decisions
- approvals
- revisions
- rollback events

## Context Drawer

Use the right-side drawer for:

- raw JSON
- schema-level detail
- metadata
- keyboard help
- confirmation previews

This avoids cluttering the main workspace with low-signal detail.

## Command Palette

Required commands:

- switch project
- create project
- change workflow mode
- refresh current view
- open next review item
- open structure navigator
- open scene navigator
- open asset navigator
- approve current phase
- request revision
- inspect blockers
- open checkpoint list
- trigger health check

## UX Style Direction

The TUI should feel like a production control room, not a chat shell.

Visual priorities:

- compact tables
- strong status color semantics
- deliberate whitespace
- persistent hotkey hints
- readable long-form text views

Color semantics:

- green: safe, approved, healthy
- amber: attention, warning, pending review
- red: blocked, failing, destructive
- blue: active work, selected view, neutral action

## Recommended Keyboard Model

- `g n`: new project
- `g d`: dashboard
- `g r`: review
- `g t`: structure
- `g a`: artifacts
- `g s`: scenes
- `g v`: validation
- `g c`: checkpoints
- `g p`: providers
- `g u`: audit
- `j` / `k`: move selection
- `enter`: open selected item
- `[`, `]`: previous / next scene
- `a`: approve when allowed
- `r`: request revision
- `e`: escalate
- `/`: search
- `:` command palette
- `?`: hotkeys

## UX Anti-Patterns To Avoid

- modal overload
- auto-refresh that steals focus
- approval buttons shown when actions are blocked
- giant raw JSON walls as the default view
- ambiguous labels like “continue” without explicit effect
- hidden auto-approval behavior with no visible workflow context
