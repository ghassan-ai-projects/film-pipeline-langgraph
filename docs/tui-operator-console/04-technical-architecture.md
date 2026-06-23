# Technical Architecture

## Core Architecture Decision

Build the TUI as a separate app package over a shared application-service layer.

MCP remains the public control boundary, but the TUI and MCP adapters should both call the
same backend services.

Recommended location:

- `src/film_pipeline/tui/`

Recommended startup command:

- `python -m film_pipeline.tui.app`

## Why A Separate TUI Layer

This preserves clear boundaries:

- `src/film_pipeline/mcp/` remains the product contract
- `src/film_pipeline/app/services/` becomes shared use-case logic
- `src/film_pipeline/app/runtime.py` remains runtime state + orchestration bridge
- `src/film_pipeline/tui/` becomes presentation and operator workflow only

## Current Repo Anchors

Primary anchors:

- `src/film_pipeline/mcp/server.py`
- `src/film_pipeline/mcp/tools/__init__.py`
- `src/film_pipeline/app/runtime.py`
- `src/film_pipeline/app/health.py`

These already give the system:

- a stdio MCP server
- a defined tool surface
- local runtime state and project lifecycle
- readiness and provider-health checks

They do not yet provide a clean shared service boundary. That should be added.

## Framework Recommendation

### Recommend `Textual`

Why:

- Python-native
- strong keyboard-first model
- layouts, tables, tabs, trees, logs, markdown, and modal support
- reactive refresh model
- easier to build a dense operator console than lower-level alternatives

### Alternatives

#### `prompt_toolkit`

Pros:

- lightweight
- excellent input handling

Cons:

- more custom work for layout, tables, focus management, and application structure

#### `urwid`

Pros:

- mature

Cons:

- lower momentum and less ergonomic for a modern, complex operator shell

### Decision

Choose `Textual` unless dependency policy blocks it.

## Proposed Internal Modules

```text
src/film_pipeline/app/services/
├── __init__.py
├── project_service.py
├── orchestration_service.py
├── review_service.py
├── structure_service.py
├── artifact_service.py
├── scene_service.py
├── asset_service.py
├── validation_service.py
├── checkpoint_service.py
├── provider_service.py
├── workflow_policy_service.py
├── audit_service.py
├── models.py
└── errors.py

src/film_pipeline/tui/
├── __init__.py
├── app.py
├── config.py
├── gateway.py
├── gateways/
│   ├── mcp_gateway.py
│   └── inprocess_gateway.py
├── events.py
├── commands.py
├── state.py
├── drafts.py
├── formatting.py
├── view_models/
│   ├── dashboard.py
│   ├── review.py
│   ├── structure.py
│   ├── scenes.py
│   ├── assets.py
│   └── validation.py
├── widgets/
│   ├── project_list.py
│   ├── phase_summary.py
│   ├── review_package.py
│   ├── structure_overview.py
│   ├── act_navigator.py
│   ├── scene_navigator.py
│   ├── artifact_viewer.py
│   ├── asset_metadata_panel.py
│   ├── validation_panel.py
│   ├── checkpoint_timeline.py
│   ├── provider_health.py
│   └── audit_log.py
└── screens/
    ├── project_create.py
    ├── dashboard.py
    ├── review.py
    ├── structure.py
    ├── scenes.py
    ├── assets.py
    ├── validation.py
    ├── checkpoints.py
    ├── providers.py
    ├── audit.py
    └── project_settings.py
```

## Service-Layer First, Transport Second

The TUI should be written against a gateway interface, not raw MCP calls.

That gateway should target shared application services.

## Transport Design

### Short-Term Recommendation

Start with a local stdio MCP gateway for real operator paths.

Why:

- it matches the current server mode
- no network dependency
- low setup cost
- easiest path to consistent local operation

Also add an in-process gateway later for development and UI testing.

### MCP Gateway Responsibilities

- start or attach to server process
- run `initialize`
- cache tool catalog
- call tools with typed helpers
- normalize errors into UI-safe messages

### In-Process Gateway Responsibilities

- call shared application services directly
- avoid transport overhead in tests and local prototyping
- preserve service-level behavior

## Typed Gateway Layer

Do not let widgets construct arbitrary tool payloads.

Introduce a thin gateway API:

- `list_projects()`
- `create_project(...)`
- `get_dashboard(project_id)`
- `get_review_workspace(project_id)`
- `get_project_structure(project_id)`
- `get_act_workspace(project_id, act_id)`
- `request_structure_improvement(project_id, scope, note)`
- `request_duration_change(project_id, scope, target_or_delta, note)`
- `list_scenes(project_id)`
- `get_scene_workspace(project_id, scene_id)`
- `request_scene_revision(project_id, scene_id, note)`
- `list_assets(project_id, family)`
- `get_asset_workspace(project_id, asset_id)`
- `request_asset_enhancement(project_id, asset_id, note)`
- `get_workflow_mode(project_id)`
- `set_workflow_mode(project_id, mode)`
- `approve_phase(project_id)`
- `request_revision(project_id, note)`
- `list_checkpoints(project_id)`
- `preview_rollback(...)`

This keeps UI code declarative and reduces transport coupling.

## State Model

Split state into two classes.

### 1. Durable backend state

Comes from application services, usually backed by MCP responses in operator mode:

- project status
- artifacts
- review packages
- validation reports
- checkpoints
- provider health
- audit events

### 2. Ephemeral local UI state

Lives only in the TUI:

- selected project
- active tab
- focused list index
- filter text
- expanded nodes
- unsent revision draft
- unsent structure-improvement draft
- unsent scene-revision draft
- unsent asset-enhancement draft
- background refresh status

## Draft Lifecycle

Drafts are local and ephemeral, but they need explicit rules.

Rules:

- keep one draft per entity scope: project, act, scene, asset, phase review
- drafts survive page switches inside the same project
- drafts are discarded only on explicit user action or successful submission
- background refresh must never overwrite a local draft buffer
- if backend state changes materially while a draft is open, show a stale-context warning instead of auto-merging silently

## Refresh Strategy

### Phase 1

Pull-based refresh only:

- full refresh on project switch
- partial refresh after each mutation
- timer refresh for top-level status

### Phase 2

Smarter invalidation:

- review tab refreshes only review + orchestrator data
- providers tab refreshes provider + generation data

### Phase 3

Optional event stream:

- server emits durable runtime events
- TUI subscribes and patches local view models

Do not require this for V1.

## Concurrency Model

The TUI should keep the screen responsive during long calls.

Requirements:

- background worker for MCP calls
- visible loading state per panel
- cancellable refresh jobs where possible
- serialize destructive actions per project

## Error Handling

Errors should be classified into:

- user input errors
- blocked action errors
- backend/runtime errors
- transport errors
- stale-data conflicts

UI requirement:

Every error message should say:

- what failed
- why it failed
- what the operator can do next

## Persistence

TUI-local persistence should be minimal.

Allowed:

- last selected project
- layout preferences
- theme preference
- command history

Not allowed:

- project truth
- approval state
- review package cache used as source of truth

## Security And Safety

### Main rules

- never log secrets from environment-backed providers
- redact credentials in error panels
- confirm expensive or destructive mutations
- show runtime mode clearly to avoid real/mock confusion

### High-risk actions

Require extra confirmation for:

- generation spend approval
- generation start
- rollback
- branch promotion
- final delivery export

## Page Ownership Rules

To avoid duplicate workflows:

- `Dashboard` owns triage and summary
- `Review` owns phase-level decisions
- `Structure` owns project-level and act-level change requests
- `Scenes` owns scene-targeted change requests
- `Assets` owns asset-targeted enhancement requests
- `Validation` owns issue-first inspection, not mutation ownership
- `Checkpoints` owns rollback/recovery

## Service Extraction Strategy

Extract business logic from `src/film_pipeline/mcp/tools/__init__.py` into application
services incrementally. Start with operator-critical paths, then move lower-priority tools.

The TUI should not wait for a perfect service layer. It should target the gateway interface
while the service extraction proceeds underneath.

## Observability In The TUI

The TUI should expose:

- latest audit events
- current blockers
- provider health
- action latency
- last refresh time
