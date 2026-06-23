# Navigation Map

## Purpose

Define how the user moves through the TUI.

## Primary Shell

Global shell elements:

- top header
- left project rail
- center page area
- right context drawer
- footer/status bar

## Primary Entry Point

Default landing page for existing-workflow operation:

- `Dashboard`

Reason:

- it gives the best summary of status, workflow mode, blockers, and next actions

Entry point for creating a new project:

- `Project Create`

## Page Relationships

### Dashboard

Acts as the hub.

Main links:

- to `Review` when a phase is awaiting decision
- to `Structure` when there are pacing/flow issues
- to `Scenes` when a scene-specific problem is identified
- to `Assets` when reference or metadata issues are identified
- to `Providers` when generation/provider health is degraded
- to `Checkpoints` when recovery is needed

### Review

Links to:

- `Scenes` for scene-targeted review
- `Assets` for reference and metadata drill-down
- `Validation` for deeper validator detail
- `Checkpoints` when comparing candidate vs approved history matters

### Structure

Links to:

- `Scenes` for act-contained scene inspection
- `Review` after structural revisions produce a new candidate package
- `Validation` for structure-related issues

### Scenes

Links to:

- `Review` for phase-level decision
- `Assets` for related references and shot metadata
- `Validation` for scene-specific issues
- `Structure` for parent act context

### Assets

Links to:

- `Scenes` for related scene usage
- `Review` for candidate vs approved review context
- `Validation` for asset-specific issues

### Validation

Links to:

- `Review`
- `Structure`
- `Scenes`
- `Assets`

depending on issue scope.

### Checkpoints

Links to:

- `Dashboard` after rollback
- `Review` for candidate history
- `Structure`, `Scenes`, or `Assets` depending on rollback target

### Providers

Links to:

- `Dashboard` for overall triage
- `Review` when generation or QC decisions are blocked
- `Assets` when provider output quality is the real issue

### Audit

Links to every page through referenced entities.

### Project Settings

Links back to:

- `Dashboard`

after changing workflow mode, profiles, or display-affecting project settings.

### Project Create

Links to:

- `Dashboard` after successful creation
- `Project Settings` when the user needs to inspect resolved defaults after creation

## Recommended Navigation Behavior

### Persistent project selection

Changing pages should not change the active project.

### Context-aware opening

If a dashboard issue targets scene `sc_014`, opening `Scenes` should land directly there.

If a validation issue targets `reference_id=ref_008`, opening `Assets` should land on that
asset.

### Return paths

After completing a focused action, the user should be able to:

- return to previous page
- return to page root
- return to dashboard

## Recommended Page Priority

Pages that should feel strongest in V1:

1. `Dashboard`
2. `Review`
3. `Structure`
4. `Scenes`
5. `Assets`

Operational pages can be simpler at first if needed:

- `Validation`
- `Checkpoints`
- `Providers`
- `Audit`
