# Structure-Level Workflow

## Purpose

The TUI should support project-level and act-level structural operations as first-class
workflows.

This includes work such as:

- flow validation
- pacing improvement
- duration increase or reduction
- act-balance review
- setup/payoff strengthening
- structural consistency checks

## Why It Matters

Film creators do not always want to operate at only one granularity.

They need to move across levels:

- project
- act
- scene
- shot
- asset

If the TUI cannot support project-wide and act-wide steering, it will feel too tactical and
not strategic enough for real story shaping.

## Main Requirement

A user must be able to:

- inspect the whole project structure
- inspect act-by-act structure
- validate narrative flow
- request structural improvement at project or act scope
- request duration changes at project or act scope
- see downstream impact before accepting major structural changes

## Recommended Workspace

Add a structure-oriented workspace.

Recommended top-level areas:

- project structure summary
- act navigator
- active act detail
- structural issues panel
- structure actions panel

## Project Structure Summary

Show:

- target runtime
- estimated current runtime
- act count
- scene count
- pacing summary
- unresolved setup/payoff threads
- structural risk summary

## Act Navigator

Each act row should show:

- act id or label
- estimated duration
- scene count
- dramatic purpose
- structural health indicator
- issue count

## Active Act Detail

Show:

- act objective
- entry and exit state
- scene sequence summary
- pacing profile
- emotional progression
- major structural notes

## Structural Issues Panel

Examples:

- weak escalation
- slow middle
- rushed ending
- unclear turning point
- underdeveloped payoff
- runtime imbalance
- scene ordering weakness

## Structure Actions

Required actions:

- `validate flow`
- `request structural improvement`
- `increase duration`
- `reduce duration`
- `improve pacing`
- `compare structure versions`
- `jump to scenes in this act`

Later possible actions:

- `split act`
- `merge act`
- `re-sequence scenes`

## Scope Rule

Project-level and act-level changes are inherently wider than scene-level changes.

The TUI must make that explicit.

Examples:

- increasing project duration may require new scenes or expanded scenes across multiple acts
- improving act 2 pacing may require scene additions, cuts, or reordering
- changing flow at project scope may invalidate downstream shot planning and prompts

The backend must compute scope honestly, and the TUI must surface it.

## Recommended Backend Concepts

Add service concepts such as:

- `ProjectStructureSummary`
- `ActSummary`
- `ActDetail`
- `StructureValidationReport`
- `StructureImprovementRequest`
- `DurationChangeRequest`
- `StructureImpactPreview`

## Recommended Services

Likely responsibilities:

- `StructureService.get_project_structure(project_id)`
- `StructureService.list_acts(project_id)`
- `StructureService.get_act_detail(project_id, act_id)`
- `StructureService.validate_flow(project_id, scope)`
- `StructureService.request_structure_improvement(project_id, scope, notes)`
- `StructureService.request_duration_change(project_id, scope, delta_or_target, notes)`
- `CheckpointService.compare_structure_versions(project_id, from_ref, to_ref)`

Structure workflow rule:

- `Structure` owns strategic project-level and act-level change requests
- `Review` owns phase-level acceptance of resulting candidate baselines

## Example Operations

### Project-Level

- increase runtime from 8 minutes to 11 minutes
- improve narrative flow
- strengthen thematic payoff
- reduce redundancy in first half

### Act-Level

- make act 2 less repetitive
- extend act 3 resolution by 90 seconds
- sharpen act 1 inciting incident
- improve emotional escalation through act 2

## TUI Requirements

### Navigation

- open structure overview quickly
- jump from act to contained scenes
- jump from structural issue to affected act or scene set

### Improvement Requests

Support structured notes such as:

- preserve
- expand
- compress
- strengthen
- reorder
- clarify

### Comparison

Users should compare:

- approved structure vs candidate structure
- act version A vs act version B
- current structure vs target runtime intent

## Relationship To Other Workflows

Structure-level workflow sits above scene and asset workflows.

Recommended hierarchy:

- project or act changes define strategic direction
- scene changes refine local execution
- asset changes refine visual and metadata execution

The TUI should let the user move between these levels without losing context.

## V1 Recommendation

Implement:

- project structure summary
- act navigator
- structural issue panel
- flow validation view
- structure improvement request
- duration change request

Delay:

- direct drag-and-drop re-sequencing
- advanced timeline editing
- automated multi-act restructuring UI

## Acceptance Criteria

- a user can inspect project structure and act structure clearly
- a user can request project-level or act-level improvement
- a user can request duration changes at project or act scope
- the TUI explains the downstream impact of strategic structural changes
