# Shared Service Layer

## Main Decision

The TUI should not depend on MCP alone, and it should not bypass backend rules with private
logic.

The correct design is a shared application-service layer used by both:

- MCP tools
- TUI gateways

## Why This Is Needed

The current repo already hints at this shape:

- runtime behavior is centralized in `src/film_pipeline/app/runtime.py`
- graph dependencies are grouped in `src/film_pipeline/graph/services.py`
- MCP tools in `src/film_pipeline/mcp/tools/__init__.py` mix adapter logic and use-case logic

That is enough to build from, but not yet a clean service boundary.

## Problem With MCP-Only UI Coupling

If the TUI talks only to MCP, two issues appear:

1. every internal UI workflow becomes serialized through transport concerns
2. pressure grows to put product logic into MCP adapters instead of reusable services

That leads to fat tool handlers and thin domain structure.

## Problem With Direct Runtime Coupling

If the TUI talks straight to runtime helpers, different problems appear:

1. TUI behavior can drift from MCP behavior
2. testing surface fragments
3. future web or API surfaces reuse less code

## Target Layering

```text
TUI widgets / screens
        │
        ▼
TUI gateway interface
   ├─ MCP gateway
   └─ in-process gateway
        │
        ▼
application services
   ├─ project service
   ├─ orchestration service
   ├─ review service
   ├─ structure workflow service
   ├─ artifact query service
   ├─ scene workflow service
   ├─ asset workflow service
   ├─ validation query service
   ├─ checkpoint service
   ├─ provider ops service
   ├─ workflow policy service
   └─ audit service
        │
        ▼
runtime / graph / stores / providers / schemas
```

## Recommended Package Shape

Preferred location:

- `src/film_pipeline/app/services/`

Possible structure:

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
```

## Responsibilities

### MCP tool adapters

Should do:

- request parsing
- envelope handling
- auth or confirmation hooks if added later
- call one service method
- serialize result

Should not do:

- business-rule branching that exists nowhere else
- view-model-specific formatting beyond tool contract needs

### TUI gateways

Should do:

- expose typed methods to the UI
- map service or MCP responses into UI view models
- hide transport details from screens

Should not do:

- orchestration decisions
- approval rules
- checkpoint logic

### Application services

Should do:

- own use-case rules
- call runtime, graph, artifact store, checkpoint manager, and provider systems
- return typed domain results
- evaluate workflow mode and gate policy consistently
- support narrow scene-level operations without hiding wider impact

## Mutation Lifecycle Rule

All sub-phase mutations must follow one durable lifecycle.

The same pattern applies to:

- structure changes
- scene revisions
- asset enhancements

Lifecycle:

1. user submits a targeted request
2. service creates a durable request record
3. service computes impact preview and scope classification
4. service produces new candidate artifacts or candidate sub-artifacts
5. service updates candidate refs and issue state
6. service exposes the new candidate through the relevant workspace
7. phase-level approval still happens through `Review`

Important rule:

- local workspaces may request change
- only the review flow promotes candidate state to approved downstream baseline

## Scope Classification

Every targeted mutation should classify scope as one of:

- `local`
- `dependent`
- `broad`

Meaning:

- `local`: only the selected entity is expected to change
- `dependent`: selected entity plus known downstream dependents may change
- `broad`: strategic change likely affects many downstream entities and review context

This classification must be returned by services and shown in the TUI.

## Gateway Model

The TUI should code against a gateway interface such as:

- `list_projects()`
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
- `get_mutation_request_status(project_id, request_id)`
- `get_workflow_mode(project_id)`
- `set_workflow_mode(project_id, mode)`
- `approve_phase(project_id)`
- `request_revision(project_id, note)`
- `list_checkpoints(project_id)`
- `preview_rollback(...)`

Implementations:

- `MCPStudioGateway`
- `InProcessStudioGateway`

## When To Use Each Gateway

### MCP gateway

Default for:

- real operator use
- integration testing of the public surface
- demos

### In-process gateway

Useful for:

- local development speed
- UI tests
- debugging service behavior without transport noise

Both must call the same application services.

## Migration Plan

### Step 1

Identify tool handlers that contain real use-case logic and extract that logic into service
methods.

### Step 2

Make MCP tools thin adapters over those services.

### Step 3

Build the TUI against a gateway abstraction.

### Step 4

Implement MCP gateway first and in-process gateway second.

## Candidate First Services

Start with the highest-value operator workflows:

- project creation and selection
- project summary and orchestrator summary
- workflow mode inspection and update
- review package retrieval
- project- and act-level structure operations
- scene navigation and scene revision
- asset navigation and asset enhancement
- approve and revise
- checkpoint listing and rollback preview
- provider health and generation status

## Acceptance Criteria

- business rules exist in one place
- MCP and TUI produce behaviorally consistent results
- TUI can switch gateway implementation without screen rewrites
- adding a new UI surface does not require copying tool logic
