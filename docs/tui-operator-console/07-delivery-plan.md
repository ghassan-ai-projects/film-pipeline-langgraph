# Delivery Plan

## Strategy

Deliver the TUI in slices that provide real operator value early.

Do not wait for a perfect all-phase console before shipping.

## Phase 0: Architecture And Contract Alignment

Goal:

- validate TUI scope
- define shared application services
- confirm MCP tools needed for V1
- choose framework

Outputs:

- this doc set
- service-layer package plan
- dependency decision for `Textual`
- backlog of any MCP surface gaps

## Phase 1: Service Extraction

Goal:

- move operator-critical use-case logic below MCP and TUI

Add:

- `app/services/` package
- service models and errors
- thin MCP adapters for the first extracted workflows

First workflows:

- project summary
- orchestrator summary
- review package retrieval
- approve and revise
- checkpoint listing and rollback preview

## Phase 2: Read-Only Operator Shell

Goal:

- open the TUI
- list projects
- inspect dashboard state
- view artifacts, validations, checkpoints, providers, and audit data

Minimum screens:

- dashboard
- artifacts
- validation
- checkpoints
- providers
- audit

Why this first:

- de-risks transport and layout
- immediately useful for inspection and demos
- no mutation safety complexity yet

## Phase 3: Review And Approval Loop

Goal:

- make the TUI operational, not just inspectable

Add:

- review workspace
- approve phase
- request revision
- structured revision note editor
- confirmation flows

This is the first version that materially reduces operator friction.

## Phase 4: Operational Recovery

Goal:

- cover failure and recovery workflows

Add:

- provider incident workflows
- checkpoint diff explorer
- invalidation preview
- rollback confirmations
- spend-approval UX

## Phase 5: High-Leverage Productivity

Goal:

- improve throughput for multi-project operation

Add:

- operator inbox
- saved filters
- command palette improvements
- recent activity stream
- keyboard macros for common review loops

## Phase 6: Advanced Live Operation

Goal:

- reduce polling and improve responsiveness

Add if justified:

- runtime event feed
- push updates
- richer batch-generation monitor

## Recommended Initial Backlog

### Backend-adjacent

- extract operator-critical service methods from MCP tool handlers
- confirm current MCP tools return stable enough payloads for public TUI operation
- add bulk summary tool if project rail becomes too chatty
- add review-status summary if review queue needs a lightweight source

### TUI package

- add `Textual` dependency
- create `src/film_pipeline/tui/`
- implement gateway interface
- implement MCP gateway
- implement in-process gateway
- implement shell app and dashboard
- implement read-only screens
- implement review workspace
- implement mutation confirmations

### Quality

- unit tests for shared services
- unit tests for view-model mapping
- snapshot or structural tests for key widgets
- integration test for MCP client against local test server

## Suggested Milestones

### M1

Shared services extracted for the first operator-critical workflows.

### M2

Read-only shell works against mock mode.

### M3

Approval and revision loop works against mock mode.

### M4

Rollback and provider operations work against mock mode.

### M5

Real mode is safe enough for operator-assisted usage.

## Definition Of Done For TUI V1

- a user can install and run the TUI from docs alone
- operator-critical workflows come from shared services, not duplicated adapters
- project triage works
- current review package can be inspected cleanly
- approve and revise are reliable
- blockers and provider state are visible
- no action bypasses MCP or runtime rules
